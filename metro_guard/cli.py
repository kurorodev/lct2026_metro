import argparse
from collections import Counter
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import functools
import hashlib
import json
from pathlib import Path
import shutil
import time
import numpy as np
from . import __version__
from .bag import frames
from .config import Config
from .detector import Detector


def run_bag(args):
    config = Config.load(args.config)
    detector = Detector(config)
    out = Path(args.output)
    out.mkdir(parents=True,exist_ok=True)
    if any((out/f).exists() for f in ('detections.jsonl','frames.json','summary.json')) and not args.overwrite:
        raise ValueError('Output already contains results; use a new directory or --overwrite')
    if args.limit is not None and args.limit<1 or args.export_every<1 or args.preview_points<1:
        raise ValueError('Limits must be positive')
    elapsed, statuses, degraded, count = [], Counter(), 0, 0
    started = time.perf_counter()
    first_stamp, last_stamp = None, None
    preview_count = 0
    canonical_config = json.dumps(config.to_dict(),sort_keys=True)
    with (out/'detections.jsonl').open('w') as results, (out/'frames.json').open('w') as preview:
        preview.write('[')
        for i,(xyz,meta) in enumerate(frames(args.bag,args.topic)):
            stamp = meta['header_timestamp'] if meta['header_timestamp']>0 else meta['bag_timestamp']
            result,p = detector.process(xyz,stamp)
            result.update(meta)
            result['bag_name']=Path(args.bag).name
            result['frame_index'] = i
            results.write(json.dumps(result,allow_nan=False)+'\n')
            elapsed.append(result['processing_ms'])
            statuses[result['status']]+=1
            degraded+=int(result['degraded'])
            count+=1
            if first_stamp is None: first_stamp=meta['bag_timestamp']
            last_stamp=meta['bag_timestamp']
            if i%args.export_every==0:
                # Uniform deterministic sampling only affects visualization.
                selected = np.linspace(0,len(p)-1,min(len(p),args.preview_points)).astype(int) if len(p) else []
                item = dict(result,points=p[selected].round(3).tolist())
                if preview_count: preview.write(',\n')
                preview.write(json.dumps(item,allow_nan=False))
                preview_count+=1
            if i%50==0:
                print(f'{i:5d} {result["status"]:22s} {result["processing_ms"]:7.1f} ms | {len(result["objects"])} candidates',flush=True)
            if args.limit is not None and count>=args.limit: break
        preview.write(']\n')
    if not count:
        raise ValueError('Bag contains no point clouds')
    wall = time.perf_counter()-started
    summary = {'version':__version__,'bag':str(Path(args.bag).resolve()),'config':config.to_dict(),
               'config_sha256':hashlib.sha256(canonical_config.encode()).hexdigest(),
               'frames':count,'preview_frames':preview_count,'duration_s':last_stamp-first_stamp,
               'wall_s':wall,'offline_throughput_fps':count/wall,'status_counts':dict(statuses),
               'degraded_frames':degraded,
               'processing_ms':dict(zip(('p50','p95','p99','max'),np.percentile(elapsed,[50,95,99,100]).tolist())),
               'quality_metrics':None,'quality_note':'No ground-truth labels: precision, recall and detection distance are not evaluated.'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    shutil.copyfile(Path(__file__).parent/'web'/'index.html',out/'index.html')
    shutil.copyfile(Path(__file__).parent/'web'/'review.js',out/'review.js')
    print(json.dumps(summary,indent=2,ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description='Metro Guard — offline LiDAR obstacle baseline')
    sub = parser.add_subparsers(dest='command',required=True)
    run = sub.add_parser('run',help='Process every frame and export a review dashboard')
    run.add_argument('bag')
    run.add_argument('--config')
    run.add_argument('--topic')
    run.add_argument('--output',default='outputs/run')
    run.add_argument('--limit',type=int)
    run.add_argument('--export-every',type=int,default=5)
    run.add_argument('--preview-points',type=int,default=4000)
    run.add_argument('--overwrite',action='store_true')
    serve = sub.add_parser('serve',help='Serve an exported dashboard (localhost by default)')
    serve.add_argument('directory',nargs='?',default='outputs/run')
    serve.add_argument('--port',type=int,default=8080)
    serve.add_argument('--host',default='127.0.0.1')
    args = parser.parse_args()
    try:
        if args.command=='run':
            run_bag(args)
        else:
            directory=Path(args.directory).resolve()
            if not (directory/'index.html').is_file(): raise ValueError('No dashboard found in '+str(directory))
            server=ThreadingHTTPServer((args.host,args.port),functools.partial(SimpleHTTPRequestHandler,directory=str(directory)))
            print(f'http://{args.host}:{args.port}',flush=True)
            try: server.serve_forever()
            finally: server.server_close()
    except (ValueError,FileNotFoundError) as exc:
        parser.exit(2,str(exc)+'\n')
    except KeyboardInterrupt:
        pass


if __name__=='__main__':
    main()
