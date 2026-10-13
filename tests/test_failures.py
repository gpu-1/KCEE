import json,tempfile,unittest,zipfile
from pathlib import Path
from kcee.failures import list_failures,failure_reason

class FailureTests(unittest.TestCase):
    def test_valid_failure_and_unsafe_records(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);run='12345678-1234-1234-1234-123456789abc';directory=root/run;directory.mkdir()
            path=directory/'failure.json';record={'run_id':run,'status':'failed','stage':'bracket_structural'};path.write_text(json.dumps(record))
            self.assertEqual(list_failures(root)[0]['run_id'],run)
            (directory/'failed-solver-artifacts.zip').symlink_to(path)
            self.assertFalse(list_failures(root)[0]['has_solver_archive'])
            record['run_id']='wrong';path.write_text(json.dumps(record));self.assertEqual(list_failures(root),[])
            path.write_text('malformed');self.assertEqual(list_failures(root),[])
            path.write_text('[]');self.assertEqual(list_failures(root),[])

    def test_bounded_diagnostic_reason(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'diagnostics.zip'
            with zipfile.ZipFile(path,'w') as z:z.writestr('job.log','Traceback\nException: Invalid boundary mesh (overlapping facets)\n')
            self.assertIn('overlapping',failure_reason(path))
            with zipfile.ZipFile(path,'w') as z:z.writestr('job.log','x'*(128*1024+1))
            self.assertIn('preview limit',failure_reason(path))
            path.write_bytes(b'invalid');self.assertIn('unreadable',failure_reason(path))
