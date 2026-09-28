import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from metro_guard.cli import run_bag
from metro_guard.output import staged_output


class ExportTests(unittest.TestCase):
    def args(self, path, overwrite=False):
        return SimpleNamespace(output=str(path), config=None, limit=None, export_every=1,
                               preview_points=100, overwrite=overwrite, bag='test', topic=None)

    def frames(self, fail=False):
        yield np.zeros((0,3)), dict(header_timestamp=1.,bag_timestamp=1.,frame_id='lidar',topic='/lidar_points')
        if fail:
            raise ValueError('Truncated input bag')

    def test_failed_export_is_not_published(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root)/'run'
            with patch('metro_guard.cli.frames', return_value=self.frames(fail=True)):
                with self.assertRaisesRegex(ValueError, 'Truncated'):
                    run_bag(self.args(out))
            self.assertFalse((out/'summary.json').exists())
            self.assertFalse((out/'frames.json').exists())
            self.assertFalse(list(out.glob('.pending-*')))

    def test_failed_overwrite_preserves_previous_run(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root)/'run'
            with patch('metro_guard.cli.frames', return_value=self.frames()):
                run_bag(self.args(out))
            before = {p.name:p.read_bytes() for p in out.iterdir()}
            with patch('metro_guard.cli.frames', return_value=self.frames(fail=True)):
                with self.assertRaises(ValueError):
                    run_bag(self.args(out, overwrite=True))
            self.assertEqual(before, {p.name:p.read_bytes() for p in out.iterdir()})
            summary = json.loads((out/'summary.json').read_text())
            self.assertEqual(summary['frames'], 1)
            self.assertEqual(len(json.loads((out/'frames.json').read_text())), 1)
            with self.assertRaisesRegex(ValueError, 'already contains'):
                run_bag(self.args(out))

    def test_concurrent_writer_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            # Abort the outer writer after testing exclusion.
            with self.assertRaisesRegex(ValueError, 'abort'):
                with staged_output(root):
                    with self.assertRaisesRegex(ValueError, 'Another process'):
                        with staged_output(root):
                            pass
                    raise ValueError('abort')


if __name__ == '__main__':
    unittest.main()
