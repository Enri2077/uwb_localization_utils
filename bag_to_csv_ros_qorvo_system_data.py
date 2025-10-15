#!/usr/bin/env python3

from collections import defaultdict
from pathlib import Path
from os import path
from rosbags.highlevel import AnyReader
import pandas as pd
from ros_qorvo_uwb_localization.msg import QorvoUWBSystemState, AnchorState
from rclpy.time import Time
from builtin_interfaces.msg import Time as BuiltinInterfacesTime


def bag_to_csv(topic_prefix: str, bag_path: str) -> None:

    with AnyReader([Path(bag_path)]) as reader:
        ranges_df = pd.DataFrame()
        ranges_df_row = dict()
        connections = [x for x in reader.connections if x.topic == f"{topic_prefix}/system_state"]
        for connection, timestamp, rawdata in reader.messages(connections=connections):
            msg: QorvoUWBSystemState = reader.deserialize(rawdata, connection.msgtype)
            ranges_df_row['msg_timestamp'] = timestamp * 1E-9
            ranges_df_row['ros_timestamp'] = msg.header.stamp.sec + msg.header.stamp.nanosec * 1E-9
            ranges_df_row['x_uwb'] = msg.tag_position.point.x
            ranges_df_row['y_uwb'] = msg.tag_position.point.y
            ranges_df_row['z_uwb'] = msg.tag_position.point.z
            ranges_df_row['uwb_frame'] = msg.tag_position.header.frame_id

            anchor_state: AnchorState
            for anchor_state in msg.anchors:
                ranges_df_row[anchor_state.id] = anchor_state.range

            ranges_df = pd.concat([ranges_df, pd.DataFrame([ranges_df_row])], ignore_index=True)

        ranges_df.to_csv(path.join(bag_path, f"{topic_prefix.replace('/', '')}_system_state.csv"))


def main():
    bag_to_csv(topic_prefix="/tag_1", bag_path=path.expanduser('~/ds/uwb_logs/2025-10-09/0/d_rosbag2_2025-10-09__14-42-47_no_sensors/'))


if __name__ == '__main__':
    main()
