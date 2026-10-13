import json,tempfile,unittest
from pathlib import Path
from kcee.failures import list_failures

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
