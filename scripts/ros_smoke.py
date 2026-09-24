"""Run INSIDE the ROS image; validate node, actual CDR input, outputs and watchdog."""
import json
import subprocess
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header, String
from sensor_msgs.msg import PointCloud2
from visualization_msgs.msg import MarkerArray


def main():
    child=subprocess.Popen(['python3','-m','metro_guard.ros_node','--ros-args','-p','input_topic:=/smoke/points'])
    rclpy.init()
    node=Node('metro_guard_smoke')
    results=[]
    clouds=[]
    markers=[]
    sub=node.create_subscription(String,'/metro_guard/result',lambda m:results.append(json.loads(m.data)),10)
    cloud_sub=node.create_subscription(PointCloud2,'/metro_guard/cloud',lambda m:clouds.append(m.width),qos_profile_sensor_data)
    marker_sub=node.create_subscription(MarkerArray,'/metro_guard/markers',lambda m:markers.append(len(m.markers)),10)
    pub=node.create_publisher(PointCloud2,'/smoke/points',qos_profile_sensor_data)
    def spin(seconds):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            rclpy.spin_once(node,timeout_sec=0.03)
    try:
        deadline=time.monotonic()+15
        while pub.get_subscription_count()==0 and time.monotonic()<deadline: spin(.1)
        assert pub.get_subscription_count()>0,'Detector subscriber not discovered'
        rng=np.random.default_rng(7)
        n=12000
        x=rng.uniform(2,80,n)
        road=np.column_stack([x,rng.uniform(-2.5,2.5,n),np.full(n,-1.6)])
        walls=np.column_stack([x,rng.choice([-2.5,2.5],n),rng.uniform(-1.6,2.2,n)])
        obstacle=rng.uniform([24.8,-.35,-1.2],[25.2,.35,.2],(300,3))
        xyz=np.vstack([road,walls,obstacle])
        raw=np.column_stack([xyz[:,1],-xyz[:,0],xyz[:,2]]).astype(np.float32)
        for i in range(8):
            header=Header(frame_id='test_lidar')
            header.stamp.sec=100
            header.stamp.nanosec=i*100000000
            pub.publish(point_cloud2.create_cloud_xyz32(header,raw))
            spin(.15)
        detected=[r for r in results if r.get('obstacle_detected')]
        assert detected,'No confirmed obstacle from ROS node: '+str(results[-2:])
        assert abs(detected[-1]['distance_m']-24.8)<.2
        assert clouds and max(markers)>1,'Visualization topics absent'
        spin(1.5)
        assert results[-1]['status']=='unknown' and 'stale_input' in results[-1]['reasons']
        print(json.dumps({'ros_smoke':'passed','results':len(results),'clouds':len(clouds),'marker_messages':len(markers)},indent=2))
    finally:
        child.terminate()
        try: child.wait(timeout=10)
        except subprocess.TimeoutExpired: child.kill(); child.wait()
        node.destroy_node()
        rclpy.shutdown()


if __name__=='__main__': main()
