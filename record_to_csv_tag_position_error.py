#!/usr/bin/python3

import os
import pandas as pd

import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Time
from message_filters import Subscriber, ApproximateTimeSynchronizer

import tf2_geometry_msgs
from tf2_ros import Buffer, TransformListener, TransformException, TransformStamped
from tf_transformations import euler_from_quaternion

from geometry_msgs.msg import PointStamped, PoseStamped
from nav_msgs.msg import Odometry
from ros_qorvo_uwb_localization.msg import QorvoUWBSystemState


class TagPositionLogger(Node):
    def __init__(self):
        super().__init__('tag_position_logger')

        # use sim time if available
        use_sim_time_param = rclpy.parameter.Parameter('use_sim_time', rclpy.Parameter.Type.BOOL, True)
        self.set_parameters([use_sim_time_param])

        self.uwb_frame = "uwb_frame"

        # TF2 setup
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # DataFrames
        self.df_tag_1 = pd.DataFrame()
        self.df_tag_2 = pd.DataFrame()
        self.df_gnss = pd.DataFrame()
        self.df_ekf_uwb = pd.DataFrame()
        self.df_ekf_rtk = pd.DataFrame()

        # tag subscribers
        self.sub_tag_1 = self.create_subscription(QorvoUWBSystemState, '/tag_1/system_state', self.tag_1_callback, 10)
        self.sub_tag_2 = self.create_subscription(QorvoUWBSystemState, '/tag_2/system_state', self.tag_2_callback, 10)

        # publishers (transformed points)
        self.pub_tag_1_transformed = self.create_publisher(PointStamped, '/tag_1/transformed', 10)
        self.pub_tag_2_transformed = self.create_publisher(PointStamped, '/tag_2/transformed', 10)

        # publishers (gt points)
        self.pub_tag_1_rtk = self.create_publisher(PointStamped, '/tag_1/rtk', 10)
        self.pub_tag_2_rtk = self.create_publisher(PointStamped, '/tag_2/rtk', 10)

        # GNSS subscriptions
        from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy
        qos_profile_reliable_volatile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )
        self.sub_gnss1 = Subscriber(self, Odometry, '/gnss_1/navsat_odometry', qos_profile=qos_profile_reliable_volatile)
        self.sub_gnss2 = Subscriber(self, Odometry, '/gnss_2/navsat_odometry', qos_profile=qos_profile_reliable_volatile)

        # GNSS synchronizer (messages received within 0.1s are considered simultaneous)
        self.ts = ApproximateTimeSynchronizer([self.sub_gnss1, self.sub_gnss2], queue_size=10, slop=0.1)
        self.ts.registerCallback(self.gnss_callback)

        # publisher for mean GNSS position
        self.pub_gnss_mean = self.create_publisher(PointStamped, '/gnss_mean/point', qos_profile=qos_profile_reliable_volatile)

        # ekf subscribers
        self.sub_ekf_uwb = self.create_subscription(Odometry, '/recompute/ekf_uwb', self.ekf_uwb_callback, 10)
        self.sub_ekf_rtk = self.create_subscription(Odometry, '/recompute/ekf_rtk', self.ekf_rtk_callback, 10)

        self.get_logger().info('TagPositionLogger node started.')

    def tag_1_callback(self, msg: QorvoUWBSystemState):
        self.tag_transform_and_log(msg, 'qorvo_tag_1', 'tag_1')

    def tag_2_callback(self, msg: QorvoUWBSystemState):
        self.tag_transform_and_log(msg, 'qorvo_tag_2', 'tag_2')

    def tag_transform_and_log(self, msg: QorvoUWBSystemState, tag_frame: str, tag_name: str):
        if msg.quality_factor == 0:
            return

        try:

            tag_rtk_position = PointStamped()
            tag_rtk_position.header.stamp = msg.tag_position.header.stamp
            tag_rtk_position.header.frame_id = tag_frame

            transform_tag_rtk_to_uwb: TransformStamped = self.tf_buffer.lookup_transform(
                source_frame=tag_rtk_position.header.frame_id,
                target_frame=self.uwb_frame,
                time=rclpy.time.Time(),
            )

            tag_gt = tf2_geometry_msgs.do_transform_point(tag_rtk_position, transform_tag_rtk_to_uwb)  # ground truth: tag frame from rtk localization of the robot

            if tag_name == 'tag_1':
                self.pub_tag_1_rtk.publish(tag_gt)
            else:
                self.pub_tag_2_rtk.publish(tag_gt)

            stamp = msg.tag_position.header.stamp
            timestamp = stamp.sec + stamp.nanosec * 1e-9

            entry = {
                't': timestamp,
                'q': msg.quality_factor,
                'x_uwb': msg.tag_position.point.x, 'y_uwb': msg.tag_position.point.y,
                'x_rtk': tag_gt.point.x, 'y_rtk': tag_gt.point.y,
            }

            if tag_name == 'tag_1':
                self.df_tag_1 = pd.concat([self.df_tag_1, pd.DataFrame([entry])], ignore_index=True)
            else:
                self.df_tag_2 = pd.concat([self.df_tag_2, pd.DataFrame([entry])], ignore_index=True)

            self.get_logger().info(f"{tag_name} {tag_gt.point.x:.3f}, {tag_gt.point.y:.3f}")

        except TransformException as ex:
            self.get_logger().warn(f"Could not transform: {ex}")

    def gnss_callback(self, odom1: Odometry, odom2: Odometry):
        try:
            pos1 = odom1.pose.pose.position
            pos2 = odom2.pose.pose.position

            # Average position
            gnss_position = PointStamped()
            gnss_position.header.frame_id = odom1.header.frame_id
            gnss_position.point.x = (pos1.x + pos2.x) / 2.0
            gnss_position.point.y = (pos1.y + pos2.y) / 2.0
            gnss_position.point.z = (pos1.z + pos2.z) / 2.0

            # Average timestamp
            t1 = odom1.header.stamp
            t2 = odom2.header.stamp
            avg_sec = (t1.sec + t2.sec) / 2.0
            avg_nanosec = (t1.nanosec + t2.nanosec) / 2.0
            # Normalize nanoseconds > 1e9
            total_ns = avg_sec * 1e9 + avg_nanosec
            gnss_position.header.stamp.sec = int(total_ns // 1e9)
            gnss_position.header.stamp.nanosec = int(total_ns % 1e9)

            # Publish the averaged point
            self.pub_gnss_mean.publish(gnss_position)

            transform_to_uwb_frame: TransformStamped = self.tf_buffer.lookup_transform(
                source_frame=gnss_position.header.frame_id,
                target_frame=self.uwb_frame,
                time=rclpy.time.Time(),
            )

            gnss_position_in_uwb_frame = tf2_geometry_msgs.do_transform_point(gnss_position, transform_to_uwb_frame)

            timestamp = gnss_position.header.stamp.sec + gnss_position.header.stamp.nanosec * 1e-9

            entry = {
                't': timestamp,
                'x': gnss_position_in_uwb_frame.point.x, 'y': gnss_position_in_uwb_frame.point.y,
            }
            self.df_gnss = pd.concat([self.df_gnss, pd.DataFrame([entry])], ignore_index=True)

        except TransformException as ex:
            self.get_logger().warn(f"Could not transform: {ex}")

    def ekf_uwb_callback(self, ekf_uwb: Odometry):
        try:

            ekf_uwb_pose_stamped = PoseStamped()
            ekf_uwb_pose_stamped.header = ekf_uwb.header
            ekf_uwb_pose_stamped.pose = ekf_uwb.pose.pose

            transform_to_uwb_frame: TransformStamped = self.tf_buffer.lookup_transform(
                source_frame=ekf_uwb_pose_stamped.header.frame_id,
                target_frame=self.uwb_frame,
                time=rclpy.time.Time(),
            )

            ekf_uwb_in_uwb_frame = tf2_geometry_msgs.do_transform_pose_stamped(ekf_uwb_pose_stamped, transform_to_uwb_frame)

            timestamp = ekf_uwb.header.stamp.sec + ekf_uwb.header.stamp.nanosec * 1e-9
            q = [ekf_uwb_in_uwb_frame.pose.orientation.x, ekf_uwb_in_uwb_frame.pose.orientation.y, ekf_uwb_in_uwb_frame.pose.orientation.z, ekf_uwb_in_uwb_frame.pose.orientation.w]

            entry = {
                't': timestamp,
                'x': ekf_uwb_in_uwb_frame.pose.position.x, 'y': ekf_uwb_in_uwb_frame.pose.position.y, 'yaw': euler_from_quaternion(q)[2],
            }
            self.df_ekf_uwb = pd.concat([self.df_ekf_uwb, pd.DataFrame([entry])], ignore_index=True)

        except TransformException as ex:
            self.get_logger().warn(f"Could not transform: {ex}")

    def ekf_rtk_callback(self, ekf_rtk: Odometry):
        try:

            ekf_rtk_pose_stamped = PoseStamped()
            ekf_rtk_pose_stamped.header = ekf_rtk.header
            ekf_rtk_pose_stamped.pose = ekf_rtk.pose.pose

            transform_to_uwb_frame: TransformStamped = self.tf_buffer.lookup_transform(
                source_frame=ekf_rtk_pose_stamped.header.frame_id,
                target_frame=self.uwb_frame,
                time=rclpy.time.Time(),
            )

            ekf_rtk_in_uwb_frame = tf2_geometry_msgs.do_transform_pose_stamped(ekf_rtk_pose_stamped, transform_to_uwb_frame)

            timestamp = ekf_rtk.header.stamp.sec + ekf_rtk.header.stamp.nanosec * 1e-9
            q = [ekf_rtk_in_uwb_frame.pose.orientation.x, ekf_rtk_in_uwb_frame.pose.orientation.y, ekf_rtk_in_uwb_frame.pose.orientation.z, ekf_rtk_in_uwb_frame.pose.orientation.w]

            entry = {
                't': timestamp,
                'x': ekf_rtk_in_uwb_frame.pose.position.x, 'y': ekf_rtk_in_uwb_frame.pose.position.y, 'yaw': euler_from_quaternion(q)[2],
            }
            self.df_ekf_rtk = pd.concat([self.df_ekf_rtk, pd.DataFrame([entry])], ignore_index=True)

        except TransformException as ex:
            self.get_logger().warn(f"Could not transform: {ex}")

    def destroy_node(self):
        print('Saving CSV files before shutdown...')
        try:
            self.df_tag_1.to_csv(os.path.expanduser('~/ds/uwb_logs/tag_1_positions.csv'), index=False)
            self.df_tag_2.to_csv(os.path.expanduser('~/ds/uwb_logs/tag_2_positions.csv'), index=False)
            self.df_gnss.to_csv(os.path.expanduser('~/ds/uwb_logs/rtk_positions.csv'), index=False)
            self.df_ekf_uwb.to_csv(os.path.expanduser('~/ds/uwb_logs/ekf_uwb_positions.csv'), index=False)
            self.df_ekf_rtk.to_csv(os.path.expanduser('~/ds/uwb_logs/ekf_rtk_positions.csv'), index=False)
            print('CSV files saved successfully in ~/ds/uwb_logs/.')
        except Exception as e:
            print(f'Error saving CSVs: {e}')

# -------------------------------
# Main
# -------------------------------
def main(args=None):
    rclpy.init(args=args)
    node = TagPositionLogger()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Keyboard interrupt received. Exiting...')
    finally:
        node.destroy_node()



if __name__ == '__main__':
    main()
