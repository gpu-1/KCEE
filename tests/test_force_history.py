import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from kcee.force_history import functions,postprocess_control,parse,summarize,PROFILE,mesh_comparison
from kcee.bracket_flow import make_case,validate_profile
class ForceHistoryTests(unittest.TestCase):
 def test_fixed_three_mesh_recipe(self):
  with tempfile.TemporaryDirectory() as tmp,patch('kcee.bracket_flow.prepare_surface',return_value=(b'solid bracket\nendsolid bracket\n',{})):
   for mesh in ('coarse','medium','fine'):
    root=Path(tmp)/mesh;make_case(root,b'fixture',mesh,'far',5,PROFILE)
    control=(root/'system/controlDict').read_text();snappy=(root/'system/snappyHexMeshDict').read_text()
    self.assertIn('endTime 3000',control);self.assertIn('solverLoads',control);self.assertIn('level (4 4)',snappy);self.assertIn('levels ((1e15 5))',snappy);self.assertIn('addLayers true',snappy)
    self.assertNotIn(b'solverLoads',postprocess_control(control.encode()))
   with self.assertRaises(ValueError):validate_profile(PROFILE,'fine','outer',5)
 def test_parser_rejects_missing_duplicate_and_nonfinite_samples(self):
  good=b'1 (3 0 0) (1 0 0) (2 0 0)\n2 (3 0 0) (1 0 0) (2 0 0)\n'
  self.assertEqual(len(parse(good,2)),2)
  for bad in (good.splitlines()[0],good.replace(b'\n2 ',b'\n1 '),good.replace(b'(3 0 0)',b'(nan 0 0)',1)):
   with self.assertRaises(ValueError):parse(bad,2)
 def test_separate_component_drift_cannot_hide_in_constant_total(self):
  forces=[{'pressure':[1+i*.001,0,0],'viscous':[2-i*.001,0,0],'total':[3,0,0]} for i in range(400)]
  moment=[{'pressure':[0,0,0],'viscous':[0,0,0],'total':[0,0,0]} for i in range(400)]
  r=summarize(forces,moment);self.assertTrue(r['checks']['total_force_N']);self.assertFalse(r['checks']['pressure_force_N']);self.assertFalse(r['checks']['viscous_force_N']);self.assertEqual(r['iterative_settling'],'not_established')
 def test_constant_and_near_zero_histories_settle(self):
  v=[{'pressure':[1e-30,0,0],'viscous':[0,0,0],'total':[1e-30,0,0]}]*400
  r=summarize(v,v);self.assertEqual(r['iterative_settling'],'criteria_met');self.assertTrue(all(r['checks'].values()))
 def test_three_mesh_changes_do_not_infer_gci(self):
  keys=('pressure_force_N','viscous_force_N','total_force_N','pressure_moment_N_m','viscous_moment_N_m','total_moment_N_m')
  rows=[{'run_id':str(i),'loads':{k:[v,0,0] for k in keys},'force_history':{'iterative_settling':'criteria_met'}} for i,v in enumerate((4,3,2.5))]
  r=mesh_comparison(rows);self.assertTrue(r['iterative_settling']);self.assertEqual(r['mesh_convergence'],'not_established');self.assertEqual(r['adjacent_mesh_changes'][1]['changes']['total_force_N']['signed_change'],[-.5,0,0])
 def test_history_runtime_must_match_the_source_solver(self):
  import json
  from test_native_forces import runtime_record
  from kcee.force_history import evaluate,SCOPES
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);meta=runtime_record();meta['overlay']['scope']=SCOPES[1]
   record={'force_history_runtime':meta,'binaries_sha256':{'simpleFoam':'b'*64},'package':meta['package'],'solver_overlay_scope':'dictionary::digest only; fixed force-history simpleFoam invocation'}
   (root/'runtime.json').write_text(json.dumps(record))
   with self.assertRaisesRegex(ValueError,'fingerprint'):evaluate(root)
