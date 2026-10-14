import unittest
from pathlib import Path
from scripts.stop_kcee import worker_command_matches

class WorkerShutdownIdentityTests(unittest.TestCase):
    def test_only_exact_project_worker_arguments_match(self):
        root=Path('/project with spaces/KCEE')
        command='/usr/bin/python3 -m kcee.geometry_worker --queue '+str(root/'.local/geometry/queue')+' --key '+str(root/'.local/geometry/key')+' --executable '+str(root/'host/macos/picogk/generate.sh')
        self.assertTrue(worker_command_matches(command+'\n',root))
        for bad in (command.replace('kcee.geometry_worker','other.worker'),command+' --other',command.replace('/project with spaces/','/other/'),'-m kcee.geometry_worker'):
            with self.subTest(command=bad):self.assertFalse(worker_command_matches(bad,root))
