import unittest
from kcee.thermal import solve,benchmark,LEFT,RIGHT
class ThermalTests(unittest.TestCase):
 def test_manufactured_solution_refines_and_balances(self):
  result=benchmark();self.assertTrue(all(result['checks'].values()))
  self.assertLess(result['mesh_study'][-1]['maximum_temperature_error_C'],.003)
  for mesh in result['mesh_study']:
   self.assertEqual(mesh['profile'][0]['temperature_C'],LEFT);self.assertEqual(mesh['profile'][-1]['temperature_C'],RIGHT)
   self.assertAlmostEqual(mesh['outward_left_heat_W']+mesh['outward_right_heat_W'],mesh['generated_heat_W'],places=9)
  self.assertGreater(result['mesh_study'][0]['maximum_temperature_error_C'],result['mesh_study'][-1]['maximum_temperature_error_C']*60)
 def test_invalid_mesh(self):
  for value in (0,3,1001,10.5):
   with self.assertRaises(ValueError):solve(value)
