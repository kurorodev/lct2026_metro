"""Read-only audit of ROS2 SQLite bags; run with the analysis environment."""
import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from rosbags.typesys import Stores, get_typestore


def array_from_msg(msg):
    types = {1: 'i1', 2: 'u1', 3: 'i2', 4: 'u2', 5: 'i4', 6: 'u4', 7: 'f4', 8: 'f8'}
    endian = '>' if msg.is_bigendian else '<'
    dtype = np.dtype({'names': [f.name for f in msg.fields],
                      'formats': [endian + types[f.datatype] for f in msg.fields],
                      'offsets': [f.offset for f in msg.fields], 'itemsize': msg.point_step})
    return np.ndarray((msg.height, msg.width), dtype=dtype, buffer=msg.data,
                      strides=(msg.row_step, msg.point_step)).reshape(-1)


def preview(xyz, path, title):
    im = Image.new('RGB', (1500, 900), '#101725')
    draw = ImageDraw.Draw(im)
    views = [(0, 1, (-10, 100), (-12, 12), 'XY'),
             (0, 2, (-10, 100), (-5, 8), 'XZ'),
             (1, 2, (-8, 8), (-5, 8), 'YZ (all ranges)')]
    for j, (a, b, xr, yr, label) in enumerate(views):
        left, top, w, h = 60, 50 + 280*j, 1380, 235
        draw.rectangle((left, top, left+w, top+h), outline='#445269')
        mask = ((xyz[:, a] > xr[0]) & (xyz[:, a] < xr[1]) &
                (xyz[:, b] > yr[0]) & (xyz[:, b] < yr[1]))
        p = xyz[mask]
        u = (left + (p[:, a]-xr[0])/(xr[1]-xr[0])*w).astype(int)
        v = (top+h - (p[:, b]-yr[0])/(yr[1]-yr[0])*h).astype(int)
        pixels = im.load()
        for x, y in zip(u, v):
            pixels[int(x), int(y)] = (67, 204, 196)
        draw.text((left, top-18), f'{label}: {xr} / {yr} m', fill='white')
    draw.text((60, 8), title, fill='white')
    im.save(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='data/for_hackathon')
    parser.add_argument('--output', default='analysis')
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    store = get_typestore(Stores.ROS2_HUMBLE)
    report = []
    for path in sorted(Path(args.data).glob('*/*.db3')):
        con = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
        topics = con.execute('select id,name,type from topics').fetchall()
        rows = con.execute('select id,timestamp,length(data) from messages order by timestamp,id').fetchall()
        ts = np.array([r[1] for r in rows], dtype=np.int64)
        delta = np.diff(ts)/1e6
        bag = {'name': path.parent.name, 'bytes': path.stat().st_size, 'topics': topics,
               'count': len(rows), 'duration_s': float((ts[-1]-ts[0])/1e9),
               'frequency_hz': float((len(ts)-1)/((ts[-1]-ts[0])/1e9)),
               'interval_ms_quantiles': np.percentile(delta, [0, 50, 95, 99, 100]).tolist(),
               'nonpositive_intervals': int((delta <= 0).sum()), 'samples': []}
        for idx in np.unique(np.linspace(0, len(rows)-1, 9).astype(int)):
            raw = con.execute('select data from messages where id=?', (rows[idx][0],)).fetchone()[0]
            msg = store.deserialize_cdr(raw, 'sensor_msgs/msg/PointCloud2')
            arr = array_from_msg(msg)
            xyz = np.column_stack([arr[n] for n in ('x','y','z')])
            finite = np.isfinite(xyz).all(axis=1)
            zero = (xyz == 0).all(axis=1)
            valid = xyz[finite & ~zero]
            ranges = np.linalg.norm(valid, axis=1)
            stamp = msg.header.stamp.sec*10**9+msg.header.stamp.nanosec
            sample = {'index': int(idx), 'frame_id': msg.header.frame_id,
                      'point_count': len(arr), 'point_step': msg.point_step,
                      'fields': [[f.name, f.offset, f.datatype, f.count] for f in msg.fields],
                      'finite_fraction': float(finite.mean()), 'zero_fraction': float(zero.mean()),
                      'bag_minus_header_s': (int(ts[idx])-stamp)/1e9,
                      'xyz_quantiles': np.percentile(valid, [0,1,50,99,100], axis=0).tolist(),
                      'range_quantiles': np.percentile(ranges, [50,90,95,99,100]).tolist(),
                      'range_counts': {str(d):int((ranges >= d).sum()) for d in [50,100,150,200,250,300]},
                      'ring_minmax': [int(arr['ring'].min()),int(arr['ring'].max())],
                      'point_time_minmax': [float(arr['timestamp'].min()),float(arr['timestamp'].max())]}
            bag['samples'].append(sample)
            if idx == len(rows)//2 or idx == np.linspace(0,len(rows)-1,9).astype(int)[4]:
                preview(valid, out/(path.parent.name+'.png'),path.parent.name)
                np.savez_compressed(out/(path.parent.name+'_sample.npz'), xyz=valid[::3])
        con.close()
        report.append(bag)
        print(bag['name'], bag['count'], round(bag['duration_s'],2), 's', flush=True)
    (out/'dataset_audit.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
