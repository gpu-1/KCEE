import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from kcee.demo import run
from kcee.picogk import GeometryError
class AdapterTests(unittest.TestCase):
    def test_unavailable_kernel_is_explicit_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(GeometryError):run(tmp,geometry_backend='picogk',picogk_executable='/does/not/exist')
            failure=json.loads(next(Path(tmp).glob('*/failure.json')).read_text())
            self.assertEqual(failure['status'],'failed');self.assertEqual(failure['stage'],'geometry')
            self.assertFalse(list(Path(tmp).glob('*/manifest.json')))
    def test_unknown_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):run(tmp,geometry_backend='unknown')
            self.assertFalse(list(Path(tmp).iterdir()))
