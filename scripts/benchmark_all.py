"""Process all bags with identical parameters; preserve per-frame evidence."""
import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',default='data/for_hackathon')
    parser.add_argument('--output',default='outputs/benchmark')
    parser.add_argument('--config',default='config/default.json')
    parser.add_argument('--overwrite',action='store_true')
    args=parser.parse_args()
    root=Path(args.output)
    root.mkdir(parents=True,exist_ok=True)
    summaries=[]
    bags=sorted(Path(args.data).glob('*/metadata.yaml'))
    if not bags: parser.error('No bag metadata.yaml files found')
    for meta in bags:
        out=root/meta.parent.name
        command=[sys.executable,'-m','metro_guard.cli','run',str(meta.parent),'--config',args.config,
                 '--output',str(out),'--export-every','5','--preview-points','3000']
        if args.overwrite: command.append('--overwrite')
        subprocess.run(command,check=True)
        summaries.append(json.loads((out/'summary.json').read_text()))
    report={'platform':platform.platform(),'machine':platform.machine(),'python':platform.python_version(),'runs':summaries}
    (root/'benchmark.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__': main()
