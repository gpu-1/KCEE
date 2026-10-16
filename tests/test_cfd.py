import unittest,math,tempfile,json
from pathlib import Path
from unittest.mock import patch,MagicMock
from kcee.cfd import solve,benchmark,INPUTS
from kcee.cfd_run import run_cfd
from kcee.provenance import verify_directory,IntegrityError
class CFDTests(unittest.TestCase):
 def test_exact_flow_conservation_and_second_order_refinement(self):
  r=benchmark();self.assertTrue(all(r['checks'].values()));self.assertAlmostEqual(r['mesh_study'][-1]['analytical_flow_per_span_m2_s'],1/120000,places=15)
  for m in r['mesh_study']:
   self.assertAlmostEqual(m['relative_profile_error'],1/m['cells']**2,places=10);self.assertAlmostEqual(m['relative_flow_error'],2/m['cells']**2,places=10);self.assertAlmostEqual(m['wall_shear_lower_Pa'],.0005,places=12);self.assertLess(m['relative_momentum_balance_error'],1e-9)
  for order in r['observed_orders']:self.assertAlmostEqual(order,2,places=7)
 def test_scaling_and_invalid_inputs(self):
  a=solve(32);b=solve(32,dict(INPUTS,pressure_gradient_Pa_m=.2));self.assertAlmostEqual(b['flow_per_span_m2_s'],2*a['flow_per_span_m2_s']);
  for n in [True,0,3,513,8.5]:
   with self.assertRaises(ValueError):solve(n)
  with self.assertRaises(ValueError):solve(16,dict(INPUTS,dynamic_viscosity_Pa_s=0))
 def test_worker_reproduction_and_artifact_hashes(self):
  response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps(benchmark()).encode()
  with tempfile.TemporaryDirectory() as tmp,patch('kcee.cfd_run.urlopen',return_value=response):
   dest=run_cfd(tmp);manifest,digest=verify_directory(dest);self.assertEqual(manifest['kind'],'cfd_benchmark');self.assertTrue((dest/'velocity.csv').read_text().startswith('y_m,velocity_m_s,'));self.assertEqual(len((dest/'velocity.csv').read_text().splitlines()),129);self.assertIn('not engineering validation',(dest/'result.json').read_text())
 def test_changed_worker_results_are_rejected_before_saving(self):
  data=benchmark();data['mesh_study'][-1]['mean_velocity_m_s']=99;response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps(data).encode()
  with tempfile.TemporaryDirectory() as tmp,patch('kcee.cfd_run.urlopen',return_value=response):
   with self.assertRaises(ValueError):run_cfd(tmp)
   self.assertEqual(list(Path(tmp).iterdir()),[])

 def test_changed_profile_file_fails_provenance(self):
  response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps(benchmark()).encode()
  with tempfile.TemporaryDirectory() as tmp,patch('kcee.cfd_run.urlopen',return_value=response):
   dest=run_cfd(tmp);(dest/'velocity.csv').write_text('changed')
   with self.assertRaises(IntegrityError):verify_directory(dest)
 def test_configurable_cases_scaling_and_laminar_envelope(self):
  base=benchmark();fine=base['mesh_study'][-1]
  for inputs,ratio in [({'pressure_gradient_Pa_m':.2},2),({'gap_m':.02},8),({'dynamic_viscosity_Pa_s':.002},.5),({'density_kg_m3':500},1),({'display_length_m':.5},1)]:
   result=benchmark(inputs);self.assertTrue(all(result['checks'].values()));self.assertAlmostEqual(result['mesh_study'][-1]['flow_per_span_m2_s']/fine['flow_per_span_m2_s'],ratio,places=9)
  self.assertEqual(base['inputs'],INPUTS)
  for bad in [{'gap_m':True},{'gap_m':float('nan')},{'gap_m':1},{'cells':32},{'density_kg_m3':None},{'pressure_gradient_Pa_m':10,'gap_m':.05},[],{'gap_m':float('inf')}]:
   with self.assertRaises(ValueError):benchmark(bad)
 def test_custom_worker_artifacts_preserve_inputs_and_envelope(self):
  inputs=dict(INPUTS,gap_m=.02,pressure_gradient_Pa_m=.2,display_length_m=.4)
  response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps(benchmark(inputs)).encode()
  with tempfile.TemporaryDirectory() as tmp,patch('kcee.cfd_run.urlopen',return_value=response):
   dest=run_cfd(tmp,inputs);verify_directory(dest);self.assertEqual(json.loads((dest/'requirements.json').read_text()),inputs);self.assertIn('400.0',(dest/'bracket.stl').read_text());self.assertIn('20.0',(dest/'bracket.stl').read_text())
 def test_cfd_assistant_evidence_is_bounded_and_uses_saved_case(self):
  from kcee.study_assistant import study_evidence
  from kcee.geometry_queue import encoded
  inputs=dict(INPUTS,pressure_gradient_Pa_m=.2);flow=benchmark(inputs);rid='1dbeef00-0000-4000-8000-000000000000';status=flow['validation_status']
  record={'id':rid,'validation_status':status,'manifest_sha256':'a'*64,'manifest':{'run_id':rid,'kind':'cfd_benchmark','artifacts':{k:'b'*64 for k in ['result.json','cfd.json','velocity.csv']}}}
  evidence,digest=study_evidence(record,{'kind':'cfd_benchmark','validation_status':status,'cfd':flow},{},{'items':[]})
  import hashlib
  self.assertEqual(digest,hashlib.sha256(encoded(evidence)).hexdigest());self.assertEqual(evidence['assumptions']['inputs'],inputs);self.assertEqual(evidence['selected_study_result']['cells'],128);self.assertNotIn('profile',evidence['mesh_results'][0]);self.assertLess(len(encoded(evidence)),20000)
