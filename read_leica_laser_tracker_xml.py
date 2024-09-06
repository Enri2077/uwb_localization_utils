#!/usr/bin/python3
import os.path
from xml.etree import ElementTree
from datetime import datetime
import pandas as pd

in_file_path = os.path.expanduser("~/uwb_logs/laser_tracker/laser_tracker_data/cornaredo.xml")
out_file_path = os.path.expanduser("~/uwb_logs/laser_tracker/laser_tracker_data/cornaredo_from_xml.csv")


tree = ElementTree.parse(in_file_path)
root = tree.getroot()
points = root.findall(".//{http://www.landxml.org/schema/LandXML-1.2}CgPoint")

df = pd.DataFrame(columns=["t", "name", "x", "y", "z"])
rows = list()

for i, p in enumerate(points):
    df.loc[i] = [datetime.strptime(p.attrib['timeStamp'], "%Y-%m-%dT%H:%M:%S.%f").timestamp(), p.attrib['name']] + list(map(float, p.text.split(' ')))

df = df.sort_values("t", ascending=True)
df.to_csv(out_file_path)
