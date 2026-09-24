"""Exercise live ros2 bag play against the real detector; run inside Docker."""
import argparse
import json
import subprocess
import time
import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import PointCloud2
from visualization_msgs.msg import MarkerArray
from rclpy.qos import qos_profile_sensor_data


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('bag')
    parser.add_argument('--topic',default='/lidar_points')
    parser.add_argument('--visualize',action='store_true')
    parser.add_argument('--queue-depth',type=int,default=2)
    parser.add_argument('--read-ahead',type=int,default=2)
    parser.add_argument('--expected-frames',type=int)
    args=parser.parse_args()
    worker=subprocess.Popen(['python3','-m','metro_guard.ros_node','--ros-args','-p','input_topic:='+args.topic,'-p','queue_depth:='+str(args.queue_depth)])
    player=None
    rclpy.init()
    node=Node('metro_guard_real_bag_test')
    results=[]
    subscription=node.create_subscription(String,'/metro_guard/result',lambda m:results.append(json.loads(m.data)),100)
    if args.visualize:
        cloud_subscription=node.create_subscription(PointCloud2,'/metro_guard/cloud',lambda m:None,qos_profile_sensor_data,raw=True)
        marker_subscription=node.create_subscription(MarkerArray,'/metro_guard/markers',lambda m:None,10)
    def spin(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end: rclpy.spin_once(node,timeout_sec=.05)
    try:
        deadline=time.monotonic()+15
        while not node.get_subscriptions_info_by_topic(args.topic) and time.monotonic()<deadline: spin(.1)
        assert node.get_subscriptions_info_by_topic(args.topic),'Input subscriber missing'
        player=subprocess.Popen(['ros2','bag','play',args.bag,'--clock','--delay','1',
                                 '--read-ahead-queue-size',str(args.read_ahead)],stdout=subprocess.DEVNULL)
        deadline=time.monotonic()+180
        while player.poll() is None and time.monotonic()<deadline:
            assert worker.poll() is None,'Detector crashed'
            spin(.1)
        assert player.poll()==0,'Bag playback failed or timed out'
        spin(.5)
        frames=[r for r in results if 'input_points' in r]
        assert len(frames)>10,'Too few detection results'
        if args.expected_frames is not None:
            assert len(frames)==args.expected_frames,f'Expected {args.expected_frames} results, got {len(frames)}'
        assert not any('invalid_cloud_or_processing_error' in r.get('reasons',[]) for r in results)
        print(json.dumps({'real_bag_ros_smoke':'passed','bag':args.bag,'results':len(frames),
                          'input_points_range':[min(r['input_points'] for r in frames),max(r['input_points'] for r in frames)],
                          'dropped_in_worker':max(r['dropped_frames'] for r in frames),
                          'received_by_subscription':max(r['received_frames'] for r in frames),
                          'callback_to_result_ms_p95':float(np.percentile([r['callback_to_result_ms'] for r in frames],95)),
                          'visualization_enabled':args.visualize,
                          'queue_depth':args.queue_depth,
                          'read_ahead_queue_size':args.read_ahead,
                          'visualization_ms_p95':float(np.percentile([r['previous_visualization_ms'] for r in frames],95)),
                          'stage_ms':{k:{'mean':float(np.mean([r['timings_ms'][k] for r in frames])),
                                         'p95':float(np.percentile([r['timings_ms'][k] for r in frames],95)),
                                         'max':float(np.max([r['timings_ms'][k] for r in frames]))}
                                      for k in frames[-1]['timings_ms']},
                          'source_duration_s':frames[-1]['timestamp']-frames[0]['timestamp'],
                          'receipt_duration_s':frames[-1]['callback_monotonic']-frames[0]['callback_monotonic'],
                          'quality_evaluated':False},indent=2))
    finally:
        for process in (player,worker):
            if process is not None and process.poll() is None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill();process.wait()
        node.destroy_node()
        rclpy.shutdown()


if __name__=='__main__': main()
