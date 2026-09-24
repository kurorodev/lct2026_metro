"""ROS 2 Humble adapter. Core and offline runner have no ROS dependency."""
import json
from array import array
from collections import deque
import threading
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import Header, String
from geometry_msgs.msg import Point
from visualization_msgs.msg import Marker, MarkerArray
from rosbags.typesys import Stores, get_typestore
from .cloud import decode
from .config import Config
from .detector import Detector


class GuardNode(Node):
    def __init__(self):
        super().__init__('metro_guard')
        self.declare_parameter('input_topic','/lidar_points')
        self.declare_parameter('config_path','')
        self.declare_parameter('stale_timeout_s',1.0)
        self.stale_timeout=float(self.get_parameter('stale_timeout_s').value)
        if not np.isfinite(self.stale_timeout) or self.stale_timeout<=0:
            raise ValueError('stale_timeout_s must be positive and finite')
        self.declare_parameter('queue_depth',2)
        self.declare_parameter('visualization_hz',5.0)
        self.visualization_hz=float(self.get_parameter('visualization_hz').value)
        if not np.isfinite(self.visualization_hz) or not 0<self.visualization_hz<=30:
            raise ValueError('visualization_hz must be in (0, 30]')
        self.next_visualization=0.
        self.previous_visualization_ms=0.
        self.previous_publish_ms=0.
        self.previous_iteration_ms=0.
        self.queue_depth=self.get_parameter('queue_depth').value
        if not isinstance(self.queue_depth,int) or not 1<=self.queue_depth<=10:
            raise ValueError('queue_depth must be an integer from 1 to 10')
        self.detector=Detector(Config.load(self.get_parameter('config_path').value or None))
        self.typestore=get_typestore(Stores.ROS2_HUMBLE)
        self.result_pub=self.create_publisher(String,'/metro_guard/result',10)
        self.marker_pub=self.create_publisher(MarkerArray,'/metro_guard/markers',10)
        self.cloud_pub=self.create_publisher(PointCloud2,'/metro_guard/cloud',qos_profile_sensor_data)
        self.lock=threading.Lock()
        self.pending=deque()
        self.stopped=threading.Event()
        self.received=time.monotonic()
        self.dropped=0
        self.received_count=0
        self.subscription=self.create_subscription(PointCloud2,self.get_parameter('input_topic').value,self.receive,qos_profile_sensor_data,raw=True)
        self.watchdog=self.create_timer(0.25,self.check_stale)
        self.worker=threading.Thread(target=self.work,daemon=True)
        self.worker.start()
        self.get_logger().info('Metro Guard started; output frame: metro_guard_lidar (forward / left / up)')

    def receive(self,msg):
        arrived=time.monotonic()
        with self.lock:
            if len(self.pending)>=self.queue_depth:
                self.pending.popleft()
                self.dropped+=1
            interval=(arrived-self.received)*1000 if self.received_count else 0.
            self.pending.append((msg,arrived,interval))
            self.received_count+=1
            self.received=time.monotonic()

    def unknown(self,reason):
        payload={'status':'unknown','obstacle_detected':False,'distance_m':None,'degraded':True,
                 'reasons':[reason],'dropped_frames':self.dropped}
        payload['received_frames']=self.received_count
        self.result_pub.publish(String(data=json.dumps(payload)))
        clear=Marker()
        clear.action=Marker.DELETEALL
        self.marker_pub.publish(MarkerArray(markers=[clear]))

    def check_stale(self):
        if time.monotonic()-self.received>self.stale_timeout:
            self.unknown('stale_input')

    def work(self):
        while not self.stopped.wait(0.002):
            with self.lock:
                item=self.pending.popleft() if self.pending else None
            if item is None: continue
            raw,received,arrival_interval=item
            iteration_start=time.monotonic()
            try:
                # Avoid constructing a Python ROS uint8 sequence for 24 MB clouds
                # in the executor. CDR decoding here exposes a NumPy buffer view.
                msg=self.typestore.deserialize_cdr(raw,'sensor_msgs/msg/PointCloud2')
                cdr_end=time.monotonic()
                xyz=decode(msg)
                xyz_end=time.monotonic()
                stamp=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9
                if stamp<=0:
                    self.unknown('invalid_header_timestamp')
                    continue
                result,points=self.detector.process(xyz,stamp)
                result['dropped_frames']=self.dropped
                result['received_frames']=self.received_count
                result['previous_visualization_ms']=self.previous_visualization_ms
                result['timings_ms']={'queue':(iteration_start-received)*1000,
                    'cdr':(cdr_end-iteration_start)*1000,'xyz':(xyz_end-cdr_end)*1000,
                    'core':result['processing_ms'],'previous_publish':self.previous_publish_ms,
                    'previous_iteration':self.previous_iteration_ms,'arrival_interval':arrival_interval}
                result['callback_monotonic']=received
                result['callback_to_result_ms']=(time.monotonic()-received)*1000
                if time.monotonic()-received>self.stale_timeout:
                    self.unknown('processing_deadline_exceeded')
                    continue
                publish_start=time.monotonic()
                self.result_pub.publish(String(data=json.dumps(result,allow_nan=False)))
                self.previous_publish_ms=(time.monotonic()-publish_start)*1000
                now=time.monotonic()
                if now>=self.next_visualization and (self.cloud_pub.get_subscription_count() or self.marker_pub.get_subscription_count()):
                    self.visualize(msg,result,points)
                    self.previous_visualization_ms=(time.monotonic()-now)*1000
                    self.next_visualization=now+1/self.visualization_hz
                self.previous_iteration_ms=(time.monotonic()-iteration_start)*1000
            except Exception as exc:
                self.get_logger().error(str(exc))
                self.detector.tracks=[]
                self.unknown('invalid_cloud_or_processing_error')

    def visualize(self,msg,result,points):
        header=Header(frame_id='metro_guard_lidar')
        header.stamp.sec=int(msg.header.stamp.sec)
        header.stamp.nanosec=int(msg.header.stamp.nanosec)
        # Visualization is bounded; every original point is processed by the detector.
        stride=max(1,int(np.ceil(len(points)/20000)))
        data=np.ascontiguousarray(points[::stride],dtype='<f4')
        cloud=PointCloud2(header=header,height=1,width=len(data),is_bigendian=False,
                          point_step=12,row_step=12*len(data),is_dense=True)
        cloud.fields=[PointField(name=name,offset=4*i,datatype=PointField.FLOAT32,count=1) for i,name in enumerate(('x','y','z'))]
        cloud.data=array('B',data.tobytes())
        self.cloud_pub.publish(cloud)
        clear=Marker()
        clear.action=Marker.DELETEALL
        markers=[clear]
        for obj in result['objects']:
            marker=Marker(header=header,ns='objects',id=obj['id'],type=Marker.CUBE,action=Marker.ADD)
            marker.pose.position.x,marker.pose.position.y,marker.pose.position.z=map(float,obj['center'])
            marker.pose.orientation.w=1.
            size=np.maximum(np.array(obj['max'])-obj['min'],0.08)
            marker.scale.x,marker.scale.y,marker.scale.z=map(float,size)
            marker.color.r=1.
            marker.color.g=0.2 if obj['confirmed'] else 0.7
            marker.color.b=0.2
            marker.color.a=0.55
            markers.append(marker)
        for side in (-1,1):
            line=Marker(header=header,ns='corridor',id=side+1,type=Marker.LINE_LIST,action=Marker.ADD)
            line.pose.orientation.w=1.
            line.scale.x=0.04
            line.color.r,line.color.g,line.color.b,line.color.a=0.4,0.6,1.,1.
            for a,b in zip(result['corridor'],result['corridor'][1:]):
                if b[0]-a[0]>self.detector.config.bin_size*2: continue
                for p in (a,b):
                    line.points.append(Point(x=float(p[0]),y=float(p[1]+side*self.detector.config.half_width),z=float(p[2])))
            markers.append(line)
        self.marker_pub.publish(MarkerArray(markers=markers))

    def close(self):
        self.stopped.set()
        self.worker.join(timeout=10)


def main():
    rclpy.init()
    node=GuardNode()
    try: rclpy.spin(node)
    except (KeyboardInterrupt,ExternalShutdownException): pass
    finally:
        node.close()
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()


if __name__=='__main__': main()
