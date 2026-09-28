"""Small deterministic ROS 2 bag for deployment checks without private data."""
import argparse
from pathlib import Path

import numpy as np
from rosbags.rosbag2 import Writer
from rosbags.typesys import Stores, get_typestore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output')
    args = parser.parse_args()
    store = get_typestore(Stores.ROS2_HUMBLE)
    Time = store.types['builtin_interfaces/msg/Time']
    Header = store.types['std_msgs/msg/Header']
    Field = store.types['sensor_msgs/msg/PointField']
    Cloud = store.types['sensor_msgs/msg/PointCloud2']
    rng = np.random.default_rng(42)
    x = rng.uniform(2, 60, 12000)
    rails = np.column_stack([x, rng.choice([-.76,.76],len(x)), np.full(len(x),-1.075)])
    floor = np.column_stack([x, rng.uniform(-2.5,2.5,len(x)), np.full(len(x),-1.4)])
    walls = np.column_stack([x, rng.choice([-2.5,2.5],len(x)), rng.uniform(-1.4,2.2,len(x))])
    obj = rng.uniform([24.8,-.4,-.8], [25.2,.4,.5], (400,3))
    xyz = np.vstack([rails,floor,walls,obj])
    raw = np.ascontiguousarray(np.column_stack([xyz[:,1],-xyz[:,0],xyz[:,2]]), dtype='<f4')
    with Writer(Path(args.output)) as writer:
        connection = writer.add_connection('/lidar_points','sensor_msgs/msg/PointCloud2',typestore=store)
        for i in range(8):
            msg = Cloud(Header(Time(100,i*100000000),'smoke_lidar'), 1, len(raw),
                        [Field(name,k*4,7,1) for k,name in enumerate('xyz')],
                        False, 12, len(raw)*12, raw.view(np.uint8).ravel(), True)
            writer.write(connection, 100000000000+i*100000000, store.serialize_cdr(msg,msg.__msgtype__))
    print('Created 8-frame synthetic bag:',args.output)


if __name__ == '__main__':
    main()
