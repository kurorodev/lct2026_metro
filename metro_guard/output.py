"""Stage bag exports and serialize writers to the same output directory."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import tempfile


ARTIFACTS = ('detections.jsonl', 'frames.json', 'index.html', 'review.js', 'summary.json')


@contextmanager
def staged_output(directory, overwrite=False):
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    # Keep the lock inode: unlinking it would let a third writer bypass a waiter.
    with (out/'.metro_guard.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another process is writing to '+str(out)) from None
        if not overwrite and any((out/name).exists() for name in ARTIFACTS):
            raise ValueError('Output already contains results; use a new directory or --overwrite')
        with tempfile.TemporaryDirectory(prefix='.pending-', dir=out) as temporary:
            stage = Path(temporary)
            yield stage
            if not all((stage/name).is_file() for name in ARTIFACTS):
                raise ValueError('Incomplete export; results were not published')
            # Readers must not consider a partially published run ready. A failed
            # publication leaves this marker until a successful --overwrite run.
            marker = out/'.publishing'
            marker.touch()
            for name in ARTIFACTS:  # summary.json is always published last
                os.replace(stage/name, out/name)
            marker.unlink()
