from pathlib import Path
from rosbags.highlevel import AnyReader
from rosbags.typesys import Stores, get_typestore
from .cloud import decode


def frames(path, topic=None):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    with AnyReader([path], default_typestore=get_typestore(Stores.ROS2_HUMBLE)) as reader:
        connections = [c for c in reader.connections if c.msgtype=='sensor_msgs/msg/PointCloud2' and (topic is None or c.topic==topic)]
        names = sorted(set(c.topic for c in connections))
        if not names:
            raise ValueError('No PointCloud2 topic found')
        if len(names)>1:
            raise ValueError('Multiple PointCloud2 topics; specify --topic: '+', '.join(names))
        for connection, stamp, data in reader.messages(connections=connections):
            msg = reader.deserialize(data,connection.msgtype)
            header_stamp = msg.header.stamp.sec+msg.header.stamp.nanosec/1e9
            yield decode(msg), {'bag_timestamp':stamp/1e9,'header_timestamp':header_stamp,
                               'frame_id':msg.header.frame_id,'topic':connection.topic}
