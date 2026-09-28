"""Reproduce ten diagnostic checkpoints; these are not ground-truth metrics.

In this bag, appended synthetic returns form a trailing intensity=1 run.
That observation is used ONLY for review, never by the detector. Intensity=1
also occurs in real returns, so the selected points require visual review.
Checkpoints were selected by inspecting the cloud and the supplied ordering.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from rosbags.highlevel import AnyReader
from rosbags.typesys import Stores, get_typestore


# frame, approximate longitudinal location, scenario description
CHECKPOINTS = [
    (200, 28., '1: 2x2 central'),
    (365, 8.5, '2: 0.3x0.3 central'),
    (420, 12.4, '3: 0.3x0.3 on rail'),
    (470, 20.2, '4: 0.3x0.3 at edge'),
    (525, 15.7, '5: 0.3x0.3 outside (supplier)'),
    (575, 17., '6: 2x2 at edge, inside'),
    (625, 18.5, '7: 2x2 outside (supplier)'),
    (670, 28., '8: 2x2 above envelope'),
    (735, 17.7, '9: 2x0.2 low on rails'),
    (800, 11.8, '10: narrow hanging object'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bag', default='data/cloud_with_fake_obj')
    parser.add_argument('--runs', nargs='+', default=['outputs/fake-baseline', 'outputs/fake-mounted'])
    parser.add_argument('--output', default='outputs/fake-review')
    args = parser.parse_args()
    runs = {}
    for directory in args.runs:
        path = Path(directory)
        runs[str(path)] = {r['frame_index']: r for r in
                           map(json.loads, (path/'detections.jsonl').read_text().splitlines())}
        if any(r['bag_name'] != Path(args.bag).name for r in runs[str(path)].values()):
            raise ValueError('Detection results belong to another bag')
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    canvas = Image.new('RGB', (1400, 1900), 'white')
    draw = ImageDraw.Draw(canvas)
    report = []
    selected = {frame: (j, distance, title) for j, (frame, distance, title) in enumerate(CHECKPOINTS)}
    with AnyReader([Path(args.bag)], default_typestore=get_typestore(Stores.ROS2_HUMBLE)) as reader:
        connections = [c for c in reader.connections if c.topic == '/lidar_points']
        for i, (connection, stamp, data) in enumerate(reader.messages(connections=connections)):
            if i not in selected:
                continue
            j, distance, title = selected[i]
            msg = reader.deserialize(data, connection.msgtype)
            layout = [(f.name, f.offset, f.datatype, f.count) for f in msg.fields]
            if (msg.point_step != 16 or msg.height != 1 or msg.is_bigendian or
                    layout != [(n, k*4, 7, 1) for k,n in enumerate(('x','y','z','intensity'))]):
                raise ValueError('Review helper only supports this bag layout')
            raw = np.frombuffer(msg.data, dtype='<f4').reshape(-1,4)
            p = raw[:, [1,0,2]].copy()
            p[:,0] *= -1
            not_one = np.flatnonzero(raw[:,3] != 1)
            tail = p[not_one[-1]+1:] if len(not_one) else p
            reference = tail[np.abs(tail[:,0]-distance) < 3]
            if len(reference) < 3:
                raise ValueError('Missing diagnostic returns at frame '+str(i))
            row = dict(scenario=j+1, frame_index=i, description=title,
                       reference_min=reference.min(0).tolist(), reference_max=reference.max(0).tolist(),
                       reference_points=len(reference), runs={})
            ox, oy = (j%2)*700, (j//2)*380

            def xy(y,z):
                return int(ox+350+y*75), int(oy+345-(z+2)*48)

            section = p[np.abs(p[:,0]-distance)<3]
            for points, color in ((section, '#aab1b8'), (reference, '#cf3028')):
                visible = points[(np.abs(points[:,1])<4.4)&(points[:,2]>-2)&(points[:,2]<4)]
                for _,y,z in visible:
                    u,v = xy(y,z)
                    draw.point((u,v),fill=color)
            draw.text((ox+10,oy+5),title,fill='black')
            draw.text((ox+10,oy+22),f'frame {i}; X~{distance:g}m; red: diagnostic returns',fill='black')
            for k, (name, frames) in enumerate(runs.items()):
                result = frames[i]
                header_stamp = msg.header.stamp.sec+msg.header.stamp.nanosec/1e9
                if abs(result['header_timestamp']-header_stamp)>1e-6:
                    raise ValueError('Timestamp mismatch at checkpoint')
                matches = []
                for obj in result['objects']:
                    inside = np.all((reference >= np.array(obj['min'])-.02)&
                                    (reference <= np.array(obj['max'])+.02), axis=1)
                    if inside.sum() >= 5:
                        matches.append(dict(id=obj['id'], confirmed=obj['confirmed'],
                                            matching_points=int(inside.sum()), distance_m=obj['distance_m']))
                confirmed = any(o['confirmed'] for o in matches)
                row['runs'][name] = dict(confirmed=confirmed, matches=matches)
                draw.text((ox+10,oy+40+16*k),f'{Path(name).name}: '+('CONFIRMED' if confirmed else 'not confirmed'),fill='black')
            # Show the estimated running surface from the final run, not a true envelope.
            corridor = np.asarray(result['corridor'])
            if len(corridor):
                floor = np.interp(distance,corridor[:,0],corridor[:,2])
                draw.line([xy(-4,floor),xy(4,floor)],fill='#4169b1')
            draw.text((ox+10,oy+360),'Y: -4..4m; Z: -2..4m; blue: estimated rail height',fill='black')
            report.append(row)
    if len(report) != len(CHECKPOINTS):
        raise ValueError('Not all checkpoints were found')
    canvas.save(out/'checkpoints.png')
    (out/'checkpoints.json').write_text(json.dumps(dict(
        note='Diagnostic checkpoints only. Trailing intensity=1 is a dataset-specific heuristic, '
             'not verified ground truth. Matching is point containment, not precision/recall.',
        checkpoints=report),indent=2)+'\n')
    for row in report:
        print(row['scenario'],row['frame_index'], {k:v['confirmed'] for k,v in row['runs'].items()})


if __name__ == '__main__':
    main()
