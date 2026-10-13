import unittest
from kcee.fea import deck,table,SolverError
class FeaTests(unittest.TestCase):
    def test_consistent_load_and_constraints(self):
        text,coordinates,tip,fixed,loads=deck(8,2,1)
        self.assertAlmostEqual(sum(loads.values()),-10)
        self.assertTrue(all(coordinates[node][0]==0 for node in fixed))
        self.assertTrue(all(coordinates[node][0]==60 for node in tip))
        self.assertIn('TYPE=C3D20',text)
        self.assertEqual(len(coordinates),165)
    def test_missing_solver_output_is_error(self):
        with self.assertRaises(SolverError):table('job failed','displacements')
