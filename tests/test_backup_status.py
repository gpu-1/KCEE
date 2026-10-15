import json, tempfile, unittest
from pathlib import Path
from kcee.backup_status import recorded_status

class BackupStatusTests(unittest.TestCase):
    def test_empty_and_malformed_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(recorded_status(tmp)['backup'])
            (Path(tmp)/'x.zip.receipt.json').write_text('{')
            result=recorded_status(tmp)
            self.assertIsNone(result['backup']);self.assertEqual(len(result['warnings']),1)

    def test_receipt_presence_and_restore_are_independent_without_exposing_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);counts={'local_documents':3,'document_page_notes':1}
            receipt={'bundle':'/private/source/x.zip','bundle_sha256':'a'*64,'counts':counts,'review_notes':{'integrity':'verified'}}
            (root/'x.zip.receipt.json').write_text(json.dumps(receipt))
            (root/'x-restore-verification.json').write_text(json.dumps({'root':'/private/destination','verification':{'integrity':'verified','counts':counts}}))
            result=recorded_status(root);self.assertFalse(result['backup']['bundle_present']);self.assertTrue(result['backup']['review_notes_verified']);self.assertTrue(result['restore']['native_setup_required']);self.assertNotIn('/private',json.dumps(result))
            (root/'x.zip').write_bytes(b'unchecked');self.assertTrue(recorded_status(root)['backup']['bundle_present'])

    def test_rejects_symlinks_failed_restore_and_invalid_fingerprints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'external').write_text('{}');(root/'x.zip.receipt.json').symlink_to(root/'external')
            (root/'x-restore-verification.json').write_text(json.dumps({'verification':{'integrity':'failed','counts':{}}}))
            result=recorded_status(root);self.assertEqual(len(result['warnings']),2)

    def test_restore_link_identifies_exact_backup_and_stopped_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'x.zip.receipt.json').write_text(json.dumps({'bundle':'x.zip','bundle_sha256':'a'*64,'counts':{}}));(root/'r-restore-verification.json').write_text(json.dumps({'tested_bundle_sha256':'a'*64,'isolated_restore_stopped':True,'verification':{'integrity':'verified','counts':{}}}));r=recorded_status(root);self.assertEqual(r['restore_link']['status'],'matches');self.assertTrue(r['restore']['isolated_restore_stopped'])
