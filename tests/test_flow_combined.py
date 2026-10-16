import copy,unittest
from kcee.bracket_flow import domain_spec
from kcee.flow_combined import mesh_summary,combined_summary
from kcee.flow_domain import summary as domain_summary
try:
 import test_flow_domain as fixtures
except ModuleNotFoundError:
 from tests import test_flow_domain as fixtures

class CombinedFlowTests(unittest.TestCase):
 def sources(self):
  domains=fixtures.DomainStudyTests().studies();domains_data=domain_summary(domains)
  far=domains[-1];far['flow']['inputs']['bore_refinement']={'level':4,'nominal_cell_m':.0007}
  # Domain evidence must carry the same local refinement recipe as the far mesh.
  domains_data['common_inputs']['bore_refinement']={'level':4,'nominal_cell_m':.0007}
  out=[]
  for i,name in enumerate(('coarse','medium','fine')):
   source=copy.deepcopy(far);source['run_id']=name;source['flow']['mesh_name']=name;source['flow']['inputs'].update({k:v for k,v in domain_spec(name,'far').items() if k!='background_spacing_m'});source['flow']['cells']=50000+i*50000;source['flow']['mesh']={'near_surface_nominal_cell_m':max(domain_spec(name,'far')['background_spacing_m'])/8};source['flow']['inputs']['bore_refinement']['nominal_cell_m']=max(domain_spec(name,'far')['background_spacing_m'])/16
   out.append(source)
  out[1]['run_id']=far['run_id'];return out,{'run_id':'domain-report','manifest_sha256':'c'*64,'data':domains_data}
 def test_far_bounds_are_identical_while_resolution_changes(self):
  specs=[domain_spec(n,'far') for n in ('coarse','medium','fine')]
  self.assertTrue(all(s['domain_min_m']==specs[0]['domain_min_m'] and s['domain_max_m']==specs[0]['domain_max_m'] for s in specs))
  self.assertGreater(max(specs[0]['background_spacing_m']),max(specs[1]['background_spacing_m']));self.assertGreater(max(specs[1]['background_spacing_m']),max(specs[2]['background_spacing_m']))
 def test_combined_evidence_requires_shared_medium_far_source(self):
  studies,domain=self.sources();result=combined_summary(studies,domain);self.assertEqual(result['joint_independence'],'not_established');self.assertTrue(all(result['checks'].values()))
  domain['data']['studies'][-1]['run_id']='other'
  with self.assertRaisesRegex(ValueError,'exact verified'):combined_summary(studies,domain)
 def test_pressure_gauge_shift_does_not_create_mesh_difference(self):
  studies,domain=self.sources()
  for i,s in enumerate(studies):
   for p in s['flow']['fixed_probes']:p['kinematic_pressure_m2_s2']+=100*i
  result=mesh_summary(studies)
  for pair in result['successive_changes']:self.assertLess(pair['maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale'],1e-8)
 def test_mixed_domain_and_physics_rejected(self):
  for field in ('domain','physics','spacing'):
   studies,_=self.sources()
   if field=='domain':studies[1]['flow']['domain_name']='base'
   if field=='physics':studies[1]['flow']['inputs']['viscosity']=2.
   if field=='spacing':studies[1]['flow']['inputs']['background_cells'][0]+=1
   with self.assertRaises(ValueError):mesh_summary(studies)

 def test_pressure_reference_and_fixed_bounds_are_enforced(self):
  studies,domain=self.sources();domain['data']['pressure_reference']['probe']='wake'
  with self.assertRaisesRegex(ValueError,'pressure reference'):combined_summary(studies,domain)
  studies,_=self.sources()
  for s in studies:s['flow']['inputs']['domain_min_m'][0]-=.01
  with self.assertRaisesRegex(ValueError,'bounds'):mesh_summary(studies)
