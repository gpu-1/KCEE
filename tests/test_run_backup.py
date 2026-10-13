import hashlib,tempfile,unittest,zipfile
from pathlib import Path
from kcee.demo import run
from kcee.provenance import IntegrityError,verify_directory
from kcee.run_backup import export_run,restore_run

class BackupTests(unittest.TestCase):
    def test_round_trip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=run(root/'runs');_,digest=verify_directory(source);bundle=root/'backup.zip';receipt=export_run(source,bundle,digest);target=root/source.name
            restore_run(bundle,target,receipt['bundle_sha256'],digest)
            self.assertTrue(all(p.read_bytes()==(target/p.name).read_bytes() for p in source.iterdir()))
            with self.assertRaises(IntegrityError):restore_run(bundle,target,receipt['bundle_sha256'],digest)
            with self.assertRaises(FileExistsError):export_run(source,bundle,digest)
    def test_wrong_hash_and_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bundle=root/'bad.zip'
            with zipfile.ZipFile(bundle,'w') as z:z.writestr('../escape','bad')
            digest=hashlib.sha256(bundle.read_bytes()).hexdigest()
            for expected in ('0'*64,digest):
                with self.assertRaises(IntegrityError):restore_run(bundle,root/'target',expected,'0'*64)
            self.assertFalse((root/'target').exists())
    def test_wrong_manifest_leaves_no_destination(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=run(root/'runs');_,digest=verify_directory(source);bundle=root/'backup.zip';receipt=export_run(source,bundle,digest);target=root/source.name
            with self.assertRaises(IntegrityError):restore_run(bundle,target,receipt['bundle_sha256'],'0'*64)
            self.assertFalse(target.exists())

    def test_changed_run_during_export_is_rejected(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=run(root/'runs');manifest,digest=verify_directory(source);bundle=root/'backup.zip'
            def verified_then_changed(*args,**kwargs):
                (source/'report.md').write_text('changed after verification')
                return manifest,digest
            with patch('kcee.run_backup.verify_directory',side_effect=verified_then_changed):
                with self.assertRaisesRegex(IntegrityError,'changed'):export_run(source,bundle,digest)
            self.assertFalse(bundle.exists())

    def test_modified_artifact_in_bundle_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=run(root/'runs');_,digest=verify_directory(source);bundle=root/'backup.zip';export_run(source,bundle,digest)
            with zipfile.ZipFile(bundle) as z:files={name:z.read(name) for name in z.namelist()}
            files['report.md']=b'altered'
            with zipfile.ZipFile(bundle,'w') as z:
                for name,data in files.items():z.writestr(name,data)
            target=root/source.name
            with self.assertRaisesRegex(IntegrityError,'Artifact hash mismatch'):restore_run(bundle,target,hashlib.sha256(bundle.read_bytes()).hexdigest(),digest)
            self.assertFalse(target.exists())
