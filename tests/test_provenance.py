import json
import tempfile
import unittest
from pathlib import Path
from kcee.demo import run
from kcee.provenance import IntegrityError, verify_directory

class ProvenanceTests(unittest.TestCase):
    def test_tamper_and_independent_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=run(tmp); original,digest=verify_directory(dest)
            (dest/'report.md').write_text('altered')
            with self.assertRaises(IntegrityError): verify_directory(dest,original,digest)
            import hashlib
            changed=json.loads((dest/'manifest.json').read_text())
            changed['artifacts']['report.md']=hashlib.sha256(b'altered').hexdigest()
            (dest/'manifest.json').write_text(json.dumps(changed))
            with self.assertRaises(IntegrityError): verify_directory(dest,original,digest)
    def test_missing_extra_and_symlink(self):
        for variant in ('missing','extra','symlink'):
            with tempfile.TemporaryDirectory() as tmp:
                dest=run(tmp)
                if variant=='extra': (dest/'unexpected.txt').write_text('x')
                else:
                    (dest/'report.md').unlink()
                    if variant=='symlink': (dest/'report.md').symlink_to(dest/'result.json')
                with self.assertRaises(IntegrityError): verify_directory(dest)
    def test_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=run(tmp); manifest=json.loads((dest/'manifest.json').read_text());manifest['run_id']='bad'
            (dest/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(IntegrityError): verify_directory(dest)
