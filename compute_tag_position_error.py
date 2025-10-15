#!/usr/bin/python3

import rclpy
import os
import pandas as pd
from rclpy.node import Node
from geometry_msgs.msg import PointStamped
from tf2_ros import Buffer, TransformListener, TransformException, TransformStamped
import tf2_geometry_msgs
from ros_qorvo_uwb_localization.msg import QorvoUWBSystemState
from builtin_interfaces.msg import Time


class TagPositionLogger(Node):
    def __init__(self):
        super().__init__('tag_position_logger')

        # Use sim time if available
        use_sim_time_param = rclpy.parameter.Parameter('use_sim_time', rclpy.Parameter.Type.BOOL, True)
        self.set_parameters([use_sim_time_param])

        self.uwb_frame = "uwb_frame"

        # TF2 setup
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # DataFrames for tag_1 and tag_2
        self.df_tag_1 = pd.DataFrame(columns=['t', 'q', 'x_uwb', 'y_uwb', 'x_rtk', 'y_rtk'])
        self.df_tag_2 = pd.DataFrame(columns=['t', 'q', 'x_uwb', 'y_uwb', 'x_rtk', 'y_rtk'])

        # Subscribers
        self.sub_tag_1 = self.create_subscription(QorvoUWBSystemState, '/tag_1/system_state', self.tag_1_callback, 10)
        self.sub_tag_2 = self.create_subscription(QorvoUWBSystemState, '/tag_2/system_state', self.tag_2_callback, 10)

        # Publishers (transformed points)
        self.pub_tag_1_transformed = self.create_publisher(PointStamped, '/tag_1/transformed', 10)
        self.pub_tag_2_transformed = self.create_publisher(PointStamped, '/tag_2/transformed', 10)

        # Publishers (gt points)
        self.pub_tag_1_rtk = self.create_publisher(PointStamped, '/tag_1/rtk', 10)
        self.pub_tag_2_rtk = self.create_publisher(PointStamped, '/tag_2/rtk', 10)

        self.get_logger().info('TagPositionLogger node started.')

    # -------------------------------
    # Generic transform + log helper
    # -------------------------------
    def transform_and_log(self, msg: QorvoUWBSystemState, tag_frame: str, tag_name: str):
        if msg.quality_factor == 0:
            return

        try:
            # transform_tag = self.tf_buffer.lookup_transform(
            #     source_frame=msg.tag_position.header.frame_id,
            #     target_frame=tag_frame,
            #     time=msg.tag_position.header.stamp,
            # )

            # transformed_tag = tf2_geometry_msgs.do_transform_point(msg.tag_position, transform_tag)

            # transform_tag_in_map_frame: TransformStamped = self.tf_buffer.lookup_transform(
            #     source_frame=tag_frame,
            #     target_frame=self.uwb_frame,
            #     time=rclpy.time.Time()
            # )

            tag_rtk_position = PointStamped()
            tag_rtk_position.header.stamp = msg.tag_position.header.stamp
            tag_rtk_position.header.frame_id = tag_frame

            transform_tag_rtk_to_uwb: TransformStamped = self.tf_buffer.lookup_transform(
                source_frame=tag_rtk_position.header.frame_id,
                target_frame=self.uwb_frame,
                time=rclpy.time.Time(),
            )

            transformed_tag_rtk = tf2_geometry_msgs.do_transform_point(tag_rtk_position, transform_tag_rtk_to_uwb)

            # Publish transformed point
            # self.publish_transformed_point(transformed_tag, tag_frame, tag_name)

            if tag_name == 'tag_1':
                self.pub_tag_1_rtk.publish(transformed_tag_rtk)
            else:
                self.pub_tag_2_rtk.publish(transformed_tag_rtk)

            # Extract time (as float seconds)
            stamp = msg.tag_position.header.stamp
            timestamp = stamp.sec + stamp.nanosec * 1e-9

            # Log to correct dataframe
            entry = {'t': timestamp,
                     'q': msg.quality_factor,
                    #  'x_err': transformed_tag.point.x, 'y_err': transformed_tag.point.y,
                     'x_uwb': msg.tag_position.point.x, 'y_uwb': msg.tag_position.point.y,
                     'x_rtk': transformed_tag_rtk.point.x, 'y_rtk': transformed_tag_rtk.point.y,
                    #  'x_rtk': transform_tag_in_map_frame.transform.translation.x, 'y_rtk': transform_tag_in_map_frame.transform.translation.y,
            }

            if tag_name == 'tag_1':
                self.df_tag_1.loc[len(self.df_tag_1)] = entry
            else:
                self.df_tag_2.loc[len(self.df_tag_2)] = entry

            self.get_logger().info(f"{tag_name} {transformed_tag_rtk.point.x:.3f}, {transformed_tag_rtk.point.y:.3f}")

        except TransformException as ex:
            self.get_logger().warn(
                f'Could not transform {msg.header.frame_id} → {tag_frame}: {ex}'
            )

    # -------------------------------
    # Callbacks for each tag
    # -------------------------------
    def tag_1_callback(self, msg: QorvoUWBSystemState):
        self.transform_and_log(msg, 'qorvo_tag_1', 'tag_1')

    def tag_2_callback(self, msg: QorvoUWBSystemState):
        self.transform_and_log(msg, 'qorvo_tag_2', 'tag_2')

    # -------------------------------
    # Publish transformed PointStamped
    # -------------------------------
    # def publish_transformed_point(self, transformed: PointStamped, frame: str, tag_name: str):
    #     pub_msg = PointStamped()
    #     pub_msg.header.stamp = self.get_clock().now().to_msg()
    #     pub_msg.header.frame_id = frame
    #     pub_msg.point.x = transformed.point.x
    #     pub_msg.point.y = transformed.point.y
    #     pub_msg.point.z = transformed.point.z

    #     if tag_name == 'tag_1':
    #         self.pub_tag_1_transformed.publish(pub_msg)
    #     else:
    #         self.pub_tag_2_transformed.publish(pub_msg)

    # -------------------------------
    # On shutdown → save CSVs
    # -------------------------------
    def destroy_node(self):
        print('Saving CSV files before shutdown...')
        try:
            self.df_tag_1.to_csv(os.path.expanduser('~/ds/uwb_logs/tag_1_positions.csv'), index=False)
            self.df_tag_2.to_csv(os.path.expanduser('~/ds/uwb_logs/tag_2_positions.csv'),index=False)
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
