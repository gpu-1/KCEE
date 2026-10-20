import copy,math,unittest
from kcee.regional_forces import region,partition,compare,csv_text,KEYS,CENTRES,NAMES
class RegionalTests(unittest.TestCase):
 def fixture(self):
  c=[list(CENTRES[0]),[.003,.01,.003],[.05,.025,.003],[.003,.025,.035]]
  mesh=[(i,i,[1.,0.,0.]) for i in range(4)];t=[[2.,0.,0.,-1.,0.,-1.] for _ in c];p=[1.,2.,3.,4.]
  expected=dict(zip(KEYS,([10.,0.,0.],[8.,0.,0.],[18.,0.,0.],[0.,.15675,-.21],[0.,.0855,-.15],[0.,.24225,-.36])))
  return mesh,c,t,p,expected
 def test_partition_matches_hand_integrated_forces_and_moments(self):
  mesh,c,t,p,e=self.fixture();d=partition(mesh,c,t,p,1,e,1)
  self.assertEqual([r['faces'] for r in d['regions']],[1,0,0,0,1,1,1]);self.assertTrue(all(d['checks'].values()))
  self.assertEqual(d['regions'][0]['loads']['pressure_force_N'],[1.,0.,0.]);self.assertEqual(d['regions'][0]['pressure_offset_1Pa_force_N'],[1.,0.,0.])
 def test_pressure_offset_matches_area_diagnostic(self):
  mesh,c,t,p,e=self.fixture();a=partition(mesh,c,t,p,1,e,1)
  shifted=copy.deepcopy(e);shifted['pressure_force_N']=[14.,0.,0.];shifted['total_force_N']=[22.,0.,0.];shifted['pressure_moment_N_m']=[0.,.1995,-.285];shifted['total_moment_N_m']=[0.,.285,-.435]
  b=partition(mesh,c,t,[v+1 for v in p],1,shifted,1)
  for x,y in zip(a['regions'],b['regions']):
   for i in range(3):self.assertAlmostEqual(y['loads']['pressure_force_N'][i]-x['loads']['pressure_force_N'][i],x['pressure_offset_1Pa_force_N'][i])
 def test_rejects_nonfinite_misaligned_or_nonclosing_evidence(self):
  mesh,c,t,p,e=self.fixture()
  for args in [(mesh,c[:-1],t,p,1,e,1),(mesh,c,t,[math.nan]*4,1,e,1),(mesh,c,t,p,2,e,1),(mesh,c,t,p,1,{**e,'total_force_N':[1,0,0]},1)]:
   with self.assertRaises(ValueError):partition(*args)
 def test_region_boundaries_and_empty_regions(self):
  for i,c in enumerate(CENTRES):self.assertEqual(region(c),i)
  self.assertEqual(region([.008,.01,.008]),4);self.assertEqual(region([.05,.01,.008]),5);self.assertEqual(region([.003,.01,.04]),6)
  with self.assertRaises(ValueError):region([0,0,math.inf])
 def test_signed_changes_close_and_csv_carries_provenance(self):
  mesh,c,t,p,e=self.fixture();a=partition(mesh,c,t,p,1,e,1);cases=[dict(a,run_id='a',mesh='coarse',profile='v1',domain='far',manifest_sha256='hash'),dict(a,run_id='b',mesh='fine',profile='v2',domain='far',manifest_sha256='hash2')]
  d=compare(cases);self.assertTrue(all(v==[0,0,0] for row in d[0]['regions'] for v in row['signed_changes'].values()))
  text=csv_text({'report_run_id':'report','report_manifest_sha256':'reporthash','cases':cases});self.assertEqual(len(text.splitlines()),43);self.assertIn('reporthash',text);self.assertIn('pressure_offset_1Pa_force_N',text)
