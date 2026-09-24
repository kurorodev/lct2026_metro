"""Evaluate independently reviewed frame labels; never turn filenames into truth."""
import argparse
import json
from pathlib import Path
import numpy as np


def evaluate(predictions, annotations):
    pred={row['frame_index']:row for row in predictions}
    if len(pred)!=len(predictions): raise ValueError('Duplicate prediction frame')
    seen=set()
    tp=fp=tn=fn=unknown=0
    errors=[]
    for row in annotations:
        if row.get('obstacle_present') is None: continue
        index=row['frame_index']
        if index in seen: raise ValueError('Duplicate label frame')
        seen.add(index)
        if index not in pred: raise ValueError('Missing prediction for labeled frame '+str(index))
        if not isinstance(row['obstacle_present'],bool): raise ValueError('obstacle_present must be boolean or null')
        p=pred[index]
        if 'bag_timestamp' in row and ('bag_timestamp' not in p or abs(row['bag_timestamp']-p['bag_timestamp'])>1e-6):
            raise ValueError('Label timestamp does not match prediction; possibly a different bag')
        if 'bag_name' in row and 'bag_name' in p and row['bag_name']!=p['bag_name']:
            raise ValueError('Label bag name does not match prediction')
        truth=row['obstacle_present']
        detected=p['obstacle_detected']
        unknown+=int(p['status']=='unknown')
        tp+=int(truth and detected)
        fp+=int(not truth and detected)
        tn+=int(not truth and not detected)
        fn+=int(truth and not detected)
        if truth and detected and row.get('nearest_distance_m') is not None:
            errors.append(abs(p['distance_m']-row['nearest_distance_m']))
    if not seen: raise ValueError('No reviewed labels; metrics cannot be computed')
    return {'labeled_frames':len(seen),'tp':tp,'fp':fp,'tn':tn,'fn':fn,
            'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None,
            'false_positive_frame_rate':fp/(fp+tn) if fp+tn else None,
            'unknown_frames':unknown,'distance_mae_m':float(np.mean(errors)) if errors else None,
            'distance_pairs':len(errors),
            'notes':['Frame-level, not object-level metrics.',
                     'Unknown/candidate count as no confirmed detection; positive truth therefore counts as a miss.',
                     'Distance error is conditional on positive detection, without object matching.']}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('predictions')
    parser.add_argument('labels')
    parser.add_argument('--output')
    args=parser.parse_args()
    def read(path): return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    result=evaluate(read(args.predictions),read(args.labels))
    text=json.dumps(result,indent=2)+'\n'
    if args.output: Path(args.output).write_text(text)
    print(text)


if __name__=='__main__': main()
