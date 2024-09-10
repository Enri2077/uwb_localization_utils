from collections import defaultdict
from pathlib import Path
from os import path
from rosbags.highlevel import AnyReader
import pandas as pd


def bag_to_csv(bag_path: str) -> None:
    topic_field_data = defaultdict(list)

    with AnyReader([Path(bag_path)]) as reader:
        connections = [x for x in reader.connections if x.topic == "/UWB/Pos"]
        for connection, timestamp, rawdata in reader.messages(connections=connections):
            msg = reader.deserialize(rawdata, connection.msgtype)
            topic_field_data['t'].append(timestamp/1E9)
            topic_field_data['x'].append(msg.position.x)
            topic_field_data['y'].append(msg.position.y)
            topic_field_data['z'].append(msg.position.z)

        df = pd.DataFrame(topic_field_data)
        df.to_csv(path.join(bag_path, f"position.csv"))


def main():
    bag_to_csv(path.expanduser('~/uwb_logs/laser_tracker/uwb_laser_tracker_bags/rosbag2_2024_07_26-12_14_22'))


if __name__ == '__main__':
    main()
