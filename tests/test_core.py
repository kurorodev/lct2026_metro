import json
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
import numpy as np
from metro_guard.cloud import canonical, decode
from metro_guard.config import Config
from metro_guard.detector import Detector, clusters


def tunnel(obstacle=False, bend=False):
    rng=np.random.default_rng(2026)
    n=16000
    x=rng.uniform(2,90,n)
    center=0.0003*x*x if bend else np.zeros(n)
    floor=np.column_stack([x,center+rng.uniform(-2.5,2.5,n),np.full(n,-1.6)])
    walls=np.column_stack([x,center+rng.choice([-2.5,2.5],n),rng.uniform(-1.6,2.2,n)])
    points=[floor,walls]
    if obstacle:
        obj=rng.uniform([24.8,-.35,-1.25],[25.2,.35,.2],(300,3))
        if bend: obj[:,1]+=0.0003*obj[:,0]**2
        points.append(obj)
    return np.vstack(points).astype(np.float32)


class CloudTests(unittest.TestCase):
    def test_padded_rows_big_endian(self):
        fields=[NS(name=n,offset=i*4,datatype=7,count=1) for i,n in enumerate('xyz')]
        payload=b''.join(struct.pack('>fff',*p)+b'xxxx' for p in [(1,2,3),(4,5,6)])
        msg=NS(width=1,height=2,point_step=12,row_step=16,data=payload,fields=fields,is_bigendian=True)
        np.testing.assert_array_equal(decode(msg),[[1,2,3],[4,5,6]])
        msg.data=payload[:-1]
        with self.assertRaises(ValueError): decode(msg)

    def test_real_layout_unaligned_timestamp(self):
        fields=[NS(name=n,offset=o,datatype=t,count=1) for n,o,t in [('x',0,7),('y',4,7),('z',8,7),('intensity',12,7),('ring',16,4),('timestamp',18,8)]]
        msg=NS(width=1,height=1,point_step=26,row_step=26,data=struct.pack('<ffffHd',1,2,3,5,128,946687300.),fields=fields,is_bigendian=False)
        np.testing.assert_array_equal(decode(msg),[[1,2,3]])

    def test_axes(self):
        np.testing.assert_array_equal(canonical(np.array([[2.,-10.,3.]])),[[10.,2.,3.]])


class DetectionTests(unittest.TestCase):
    def setUp(self): self.config=Config(forward_axis='x')

    def test_empty_is_unknown(self):
        result,_=Detector(self.config).process(np.zeros((100,3)),1.)
        self.assertEqual(result['status'],'unknown')
        self.assertIsNone(result['distance_m'])

    def test_straight_empty_tunnel(self):
        result,_=Detector(self.config).process(tunnel(),1.)
        self.assertEqual(result['status'],'no_obstacle_observed')

    def test_bent_empty_tunnel(self):
        result,_=Detector(self.config).process(tunnel(bend=True),1.)
        self.assertFalse(result['objects'])

    def test_rails_and_low_sidewalk_are_background(self):
        rng=np.random.default_rng(11)
        n=12000
        x=rng.uniform(2,85,n)
        rails=np.column_stack([x,rng.choice([-.76,.76],n)+rng.normal(0,.02,n),np.full(n,-1.28)])
        pavement=np.column_stack([x,rng.uniform(1.2,1.4,n),np.full(n,-1.12)])
        result,_=Detector(self.config).process(np.vstack([tunnel(),rails,pavement]),1.)
        self.assertFalse(result['objects'])

    def test_ceiling_is_not_obstacle(self):
        rng=np.random.default_rng(2)
        roof=np.column_stack([rng.uniform(2,85,15000),rng.uniform(-2.5,2.5,15000),np.full(15000,1.4)])
        base=tunnel()
        base=base[base[:,2]<=1.4]
        result,_=Detector(self.config).process(np.vstack([base,roof]),1.)
        self.assertFalse(result['objects'])

    def test_temporal_confirmation_and_distance(self):
        detector=Detector(self.config)
        for i in range(3):
            result,_=detector.process(tunnel(obstacle=True),1+i*.1)
            self.assertEqual(result['obstacle_detected'],i==2)
        self.assertAlmostEqual(result['distance_m'],24.8,delta=.1)
        result,_=detector.process(tunnel(),1.3)
        self.assertFalse(result['obstacle_detected'])

    def test_boundary_points_remain_visible_but_uncertain(self):
        rng=np.random.default_rng(19)
        edge=rng.uniform([24.8,1.38,-.4],[25.2,1.44,.1],(250,3))
        detector=Detector(Config(forward_axis='x',boundary_margin=.12))
        for stamp in (1.,1.1,1.2):
            result,_=detector.process(np.vstack([tunnel(),edge]),stamp)
        self.assertTrue(result['objects'])
        self.assertTrue(result['objects'][0]['temporally_confirmed'])
        self.assertTrue(result['objects'][0]['boundary_uncertain'])
        self.assertFalse(result['obstacle_detected'])
        self.assertIn('clearance_boundary_uncertainty',result['reasons'])

    def test_asymmetric_walls_do_not_shift_rail_center(self):
        rng=np.random.default_rng(121)
        n=18000
        x=rng.uniform(2,80,n)
        floor=np.column_stack([x,rng.uniform(-1.6,2.0,n),np.full(n,-1.6)])
        walls=np.column_stack([x,rng.choice([-1.6,2.0],n),rng.uniform(-1.6,2.2,n)])
        rails=np.column_stack([x,rng.choice([-.76,.76],n)+rng.normal(0,.01,n),np.full(n,-1.28)])
        result,_=Detector(Config(forward_axis='x',geometry_model='rail_guided')).process(np.vstack([floor,walls,rails]),1.)
        centers=np.asarray(result['corridor'])[:,1]
        self.assertLess(float(np.max(np.abs(centers))),.15)
        self.assertFalse(result['objects'])

    def test_gap_resets_confirmation(self):
        detector=Detector(self.config)
        for t in [1.,1.1,1.2]: detector.process(tunnel(True),t)
        for t in [2.,0.5]:
            result,_=detector.process(tunnel(True),t)
            self.assertFalse(result['obstacle_detected'])
            self.assertIn('timestamp_discontinuity',result['reasons'])

    def test_nonfinite_and_behind_points(self):
        bad=np.array([[np.nan,0,1],[0,np.inf,1],[-10,0,1],[0,0,0]],dtype=np.float32)
        result,_=Detector(self.config).process(bad,1.)
        self.assertEqual(result['roi_points'],0)
        self.assertEqual(result['status'],'unknown')

    def test_voxels_keep_separate_objects(self):
        p=np.array([[0,0,0],[.1,0,0],[5,0,0],[5.1,0,0]])
        self.assertEqual(sorted(map(len,clusters(p,.35))),[2,2])

    def test_invalid_config(self):
        for c in [Config(max_range=-1),Config(confirm_frames=0),Config(half_width=float('nan')),Config(bin_size=0),
                  Config(lidar_height=1.075),Config(geometry_model='rail_guided',lidar_height=-1),
                  Config(geometry_model='rail_guided',lidar_height=float('nan'))]:
            with self.assertRaises(ValueError): c.validate()

    def test_mounted_lidar_low_obstacle_on_graded_rails(self):
        rng = np.random.default_rng(42)
        x = rng.uniform(2, 80, 18000)
        z = -1.075 - .006*x
        rails = np.column_stack([x, rng.choice([-.76,.76], len(x)) + rng.normal(0,.008,len(x)), z])
        bed = np.column_stack([x, rng.uniform(-2.5,2.5,len(x)), z-.25])
        walls = np.column_stack([x, rng.choice([-2.5,2.5],len(x)), z+rng.uniform(0,3.8,len(x))])
        background = np.vstack([rails,bed,walls])
        config = Config(forward_axis='x',geometry_model='rail_guided',lidar_height=1.075,min_height=.1)
        empty, _ = Detector(config).process(background,1.)
        self.assertFalse(empty['objects'])
        nodes = np.asarray(empty['corridor'])
        self.assertLess(np.max(np.abs(nodes[:,2]-(-1.075-.006*nodes[:,0]))), .1)
        obj = rng.uniform([24.9,-.95,0],[25.1,.95,.2],(600,3))
        obj[:,2] += -1.075-.006*obj[:,0]
        detector = Detector(config)
        for stamp in (1.,1.1,1.2):
            result,_ = detector.process(np.vstack([background,obj]),stamp)
        self.assertTrue(result['obstacle_detected'])
        self.assertAlmostEqual(result['distance_m'],24.9,delta=.1)

    def test_mount_anchor_is_not_observed_corridor(self):
        config = Config(geometry_model='rail_guided',lidar_height=1.075)
        result,_ = Detector(config).process(np.zeros((0,3)),1.)
        self.assertEqual(result['status'],'unknown')
        self.assertFalse(result['corridor'])


if __name__=='__main__': unittest.main()
