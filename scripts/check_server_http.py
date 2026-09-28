"""Exercise the deployed static viewer over HTTP, using no browser packages."""
import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    base = sys.argv[1].rstrip('/')
    if '--not-ready' in sys.argv:
        with urlopen(base+'/healthz',timeout=10) as response:
            assert response.status == 200
        for path in ('/readyz','/','/frames.json'):
            try:
                urlopen(base+path,timeout=10)
            except HTTPError as exc:
                assert exc.code == 503, (path,exc.code)
            else:
                raise AssertionError('Incomplete publication exposed: '+path)
        print('Incomplete publication correctly returns HTTP 503.')
        return
    for path in ('/healthz','/readyz','/','/review.js'):
        with urlopen(base+path, timeout=10) as response:
            assert response.status == 200, path
            assert response.read(), path
    with urlopen(base+'/summary.json',timeout=10) as response:
        summary = json.load(response)
    with urlopen(base+'/frames.json',timeout=10) as response:
        frames = json.load(response)
    assert summary['frames'] == 8
    assert len(frames) == 8
    assert frames[-1]['obstacle_detected'], 'Synthetic obstacle not confirmed'
    for path in ('/.env','/.metro_guard.lock','/frames.full.json','/missing','/../etc/passwd'):
        try:
            urlopen(base+path,timeout=10)
        except HTTPError as exc:
            assert exc.code in (400,403,404), (path,exc.code)
        else:
            raise AssertionError('Unexpected file exposure: '+path)
    try:
        urlopen(Request(base+'/frames.json',data=b'no writes',method='POST'),timeout=10)
    except HTTPError as exc:
        assert exc.code in (403,405), exc.code
    else:
        raise AssertionError('Write request unexpectedly accepted')
    print('HTTP checks passed: readiness, data, obstacle confirmation, restricted file access.')


if __name__ == '__main__':
    main()
