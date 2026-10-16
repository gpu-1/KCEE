import copy,unittest,tempfile
from pathlib import Path
from kcee.bracket_flow import domain_spec,make_case
from kcee.flow_domain import summary,report_markdown
from kcee.flow_sampling import PROBES
try:
 import test_bracket_flow as bracket_fixture
except ModuleNotFoundError:
 from tests import test_bracket_flow as bracket_fixture

class DomainStudyTests(unittest.TestCase):
 def studies(self):
  out=[]
  for index,name in enumerate(('base','expanded','far')):
   spec=domain_spec('medium',name)
   probes=[{'name':label,'requested_position_m':list(point),'sample_position_m':list(point),'available':True,'velocity_m_s':[.01,0.,0.],'speed_m_s':.01,'kinematic_pressure_m2_s2':10*index+j*.000001,'maximum_support_distance_m':.001,'support_cell_indices':[0,1,2,3],'support_positions_m':[list(point)]*4,'weights':[.25]*4} for j,(label,point) in enumerate(PROBES)]
   flow={'domain_name':name,'mesh_name':'medium','source':{'source_stl_sha256':'a'*64},'inputs':{k:v for k,v in spec.items() if k!='background_spacing_m'}|{'maximum_iterations':1500,'viscosity':.0001},'fixed_probes':probes,'field_position_basis':'triangulated_polyhedral_volume_centroids','cells':62000+index*20000,'checks':{'mesh':True},'residuals':{'p':1e-9},'relative_boundary_mass_imbalance':1e-10,'mesh':{},'bore_verification':{'all_pass':True},'cell_position_audit':{}}
   out.append({'run_id':name,'manifest_sha256':'b'*64,'flow':flow,'reused':index==0})
  return out
 def test_expansion_preserves_spacing_and_integer_grid_alignment(self):
  base=domain_spec('medium')
  for name,steps in [('expanded',4),('far',8)]:
   spec=domain_spec('medium',name)
   for k,h in enumerate(base['background_spacing_m']):
    self.assertAlmostEqual((spec['domain_max_m'][k]-spec['domain_min_m'][k])/spec['background_cells'][k],h)
    self.assertAlmostEqual((base['domain_min_m'][k]-spec['domain_min_m'][k])/h,steps)
  for mesh,name in [('fine','expanded'),('medium','unknown')]:
   with self.assertRaises(ValueError):domain_spec(mesh,name)
 def test_pressure_reference_removes_uniform_gauge_shift(self):
  result=summary(self.studies())
  for pair in result['successive_changes']:self.assertLess(pair['maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale'],1e-9)
  self.assertEqual(result['domain_convergence'],'not_established');self.assertIn('Pressure reference',report_markdown(result))
 def test_physical_pressure_difference_is_retained(self):
  studies=self.studies();studies[2]['flow']['fixed_probes'][1]['kinematic_pressure_m2_s2']+=.000005
  result=summary(studies);self.assertAlmostEqual(result['successive_changes'][1]['maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale'],.1,places=7)
 def test_mixed_spacing_physics_surface_and_unavailable_probes_rejected(self):
  for change in ('spacing','physics','surface','probe'):
   studies=self.studies();flow=studies[1]['flow']
   if change=='spacing':flow['inputs']['background_cells'][0]+=1
   if change=='physics':flow['inputs']['viscosity']=.001
   if change=='surface':flow['source']['source_stl_sha256']='c'*64
   if change=='probe':flow['fixed_probes'][0]['available']=False
   with self.assertRaises(ValueError):summary(studies)
 def test_generated_domain_cases_change_only_background_dictionary(self):
  raw=bracket_fixture.BracketFlowTests().surface()
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'base';b=Path(d)/'expanded';make_case(a,raw,'medium');make_case(b,raw,'medium','expanded')
   for p in a.rglob('*'):
    if p.is_file() and p.name!='blockMeshDict':self.assertEqual(p.read_bytes(),(b/p.relative_to(a)).read_bytes())
   text=(b/'system/blockMeshDict').read_text();self.assertIn('(40 28 30)',text);self.assertIn('-0.165',text);self.assertNotEqual((a/'system/blockMeshDict').read_text(),text)
