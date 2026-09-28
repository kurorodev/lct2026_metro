"""Deployment preflight using only Python's standard library on the host."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3


def initialize():
    env = ROOT/'.env'
    if not env.exists():
        text = (ROOT/'.env.example').read_text()
        text = text.replace('APP_UID=1000', 'APP_UID='+str(os.getuid()))
        text = text.replace('APP_GID=1000', 'APP_GID='+str(os.getgid()))
        with env.open('x') as stream:
            stream.write(text)
        env.chmod(0o600)
        print('Created .env with current UID/GID. Existing .env is never overwritten.')
    for name in ('data', 'outputs'):
        (ROOT/name).mkdir(exist_ok=True)
    print('Review .env, then transfer/extract one bag into DATA_DIR.')


def check(mode):
    if not (ROOT/'.env').is_file():
        raise ValueError('Run scripts/server.sh init first, then review .env')
    result = subprocess.run(['docker','compose','--profile','batch','config','--format','json'],
                            cwd=ROOT, text=True, capture_output=True, check=True)
    services = json.loads(result.stdout)['services']
    service = services['processor' if mode == 'process' else 'web']
    mounts = {v['target']:Path(v['source']) for v in service['volumes']}
    for target, source in mounts.items():
        if not source.exists():
            raise ValueError(f'Missing mount {source} -> {target}')
    if mode == 'process':
        command = service['command']
        bag = mounts['/data']/Path(command[1]).relative_to('/data')
        if not (bag/'metadata.yaml').is_file():
            raise ValueError('Missing ROS 2 bag metadata: '+str(bag/'metadata.yaml'))
        output = mounts['/output']
        if not os.access(output, os.W_OK):
            raise ValueError('Output directory is not writable: '+str(output))
        container_uid, container_gid = map(int, service['user'].split(':'))
        stat = output.stat()
        permission = (stat.st_mode >> (6 if stat.st_uid == container_uid else
                                      3 if stat.st_gid == container_gid else 0)) & 7
        if container_uid and permission & 3 != 3:
            raise ValueError('Output directory needs write/execute permission for APP_UID:APP_GID')
        free = shutil.disk_usage(output).free
        if free < GIB:
            raise ValueError('Keep at least 1 GiB free for results and temporary output')
        config = mounts['/config/detector.json']
        json.loads(config.read_text())
        run = output/Path(command[command.index('--output')+1]).relative_to('/output')
        if (run/'summary.json').exists():
            raise ValueError('RUN_NAME already exists. Choose a new RUN_NAME in .env: '+str(run))
        print(f'Bag: {bag}\nOutput: {run}\nFree output space: {free/GIB:.1f} GiB')
    else:
        run = mounts['/srv/results']
        if (run/'.publishing').exists():
            raise ValueError('Result publication is incomplete: '+str(run))
        for name in ('index.html','review.js','summary.json','frames.json'):
            if not (run/name).is_file() or (run/name).is_symlink():
                raise ValueError('Missing regular export file: '+str(run/name))
        summary = json.loads((run/'summary.json').read_text())
        if summary.get('frames', 0) < 1:
            raise ValueError('Export contains no processed frames')
        if (run/'frames.json').stat().st_size > 64*1024**2:
            raise ValueError('Browser preview exceeds 64 MiB; re-export with larger EXPORT_EVERY '
                             'or smaller PREVIEW_POINTS to a new RUN_NAME')
        print(f'Ready export: {run}\nFrames processed: {summary["frames"]}')
    print('Preflight passed. Data and outputs are bind mounts, outside container storage.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', nargs='?', choices=('process','web'), default='process')
    parser.add_argument('--init', action='store_true')
    args = parser.parse_args()
    try:
        initialize() if args.init else check(args.mode)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, str(exc)+'\n')


if __name__ == '__main__':
    main()
