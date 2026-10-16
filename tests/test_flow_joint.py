import copy,csv,json,math,tempfile,unittest
from pathlib import Path
from kcee.flow_reference import summary,save
from kcee.bracket_flow import domain_spec,make_case,LOCAL_PROFILE
try:import test_flow_reference as fixtures
except ModuleNotFoundError:from tests import test_flow_reference as fixtures
class JointStudyTests(unittest.TestCase):
 def sources(self):
  sources=fixtures.ReferenceStudyTests().sources();fine=copy.deepcopy(sources[3]);fine['run_id']='fine-outer';f=fine['flow'];f['domain_name']='outer';spec=domain_spec('fine','outer')
  for k in ('domain_min_m','domain_max_m','background_cells'):f['inputs'][k]=spec[k]
  for key,level in [('bore_refinement',4),('targeted_refinement',3)]:
   f['inputs'][key]['nominal_cell_m']=max(spec['background_spacing_m'])/2**level;f['mesh'][key]=copy.deepcopy(f['inputs'][key])
  return sources+[fine]
 def test_joint_bounds_and_grid_confounds_are_explicit(self):
  d=summary(self.sources());self.assertEqual(d['schema'],'kcee.bracket-flow-reference.v2');self.assertEqual(len(d['comparisons']),5);self.assertTrue(all(d['checks'].values()));self.assertFalse(d['fine_grid_audit']['spacing_and_alignment_preserved']);self.assertAlmostEqual(max(abs(v) for v in d['fine_grid_audit']['relative_spacing_changes']),.005128205128205332);self.assertEqual(d['mesh_independence'],'not_established')
 def test_signed_interaction_closure_and_gauge_invariance(self):
  sources=self.sources()
  for j,p in enumerate(sources[-1]['flow']['fixed_probes']):p['kinematic_pressure_m2_s2']+=j*1e-6;p['velocity_m_s'][0]+=j*1e-5
  d=summary(sources);i=d['interaction'];self.assertAlmostEqual(i['probes'][1]['upstream_referenced_change_m2_s2'],1e-6);self.assertAlmostEqual(i['probes'][1]['velocity_vector_change_m_s'],1e-5)
  for p in i['probes']:self.assertAlmostEqual(p['upstream_referenced_change_m2_s2'],p['local_anchor_change_m2_s2']+p['anchor_upstream_change_m2_s2'],places=14)
  for k,s in enumerate(sources):
   for p in s['flow']['fixed_probes']:p['kinematic_pressure_m2_s2']+=k
  for a,b in zip(i['probes'],summary(sources)['interaction']['probes']):self.assertAlmostEqual(a['upstream_referenced_change_m2_s2'],b['upstream_referenced_change_m2_s2'],places=13)
 def test_fine_recipe_mismatches_rejected(self):
  for mutation in ('bounds','source','recipe','cells','basis','physics'):
   sources=self.sources();f=sources[-1]['flow']
   if mutation=='bounds':f['inputs']['domain_min_m'][0]-=.01
   if mutation=='source':f['source']['source_stl_sha256']='other'
   if mutation=='recipe':f['inputs']['bore_refinement']['nominal_cell_m']=1
   if mutation=='cells':f['inputs']['background_cells'][0]+=1
   if mutation=='basis':f['field_position_basis']='other'
   if mutation=='physics':f['inputs']['kinematic_viscosity_m2_s']=1
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):summary(sources)
 def test_fine_case_cap_and_physical_domain(self):
  # Obtain the same synthetic fixture without importing a TestCase into discovery.
  try:import test_bracket_flow as bf
  except ModuleNotFoundError:from tests import test_bracket_flow as bf
  raw=bf.BracketFlowTests().surface()
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);make_case(p,raw,'fine','outer',4,LOCAL_PROFILE);text=(p/'system/snappyHexMeshDict').read_text();self.assertIn('maxGlobalCells 350000',text);self.assertIn('maxLocalCells 350000',text)
  self.assertEqual(domain_spec('fine','outer')['domain_min_m'],domain_spec('medium','outer')['domain_min_m'])
 def test_joint_export_contains_direct_pairs_and_bound_interaction(self):
  from kcee.provenance import verify_directory
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'parent';p.mkdir()
   for n in ('requirements.json','geometry.json','geometry-request.json'):(p/n).write_text('{}')
   (p/'bracket.stl').write_bytes(b'fixture');sources=self.sources();fine=root/sources[5]['run_id'];fine.mkdir();import zipfile
   with zipfile.ZipFile(fine/'cfd-artifacts.zip','w') as archive:archive.writestr('snappyHexMesh.log','No refinement limit reached')
   dest=save(root,'parent',{'manifest_sha256':'a'*64},sources);verify_directory(dest)
   with (dest/'verification.csv').open() as stream:rows=list(csv.DictReader(stream))
   self.assertEqual(len(rows),65);self.assertEqual(len(json.loads((dest/'cfd.json').read_text())['interaction']['source_run_ids']),4);self.assertIn('Fine grid audit',(dest/'report.md').read_text())

 def test_larger_response_allowance_is_limited_to_fine_outer(self):
  from unittest.mock import patch,MagicMock
  from kcee.bracket_flow_run import run_bracket_flow
  from kcee.flow_sampling import COMPACT
  for mesh,domain,limit in [('fine','outer',128),('fine','far',96),('medium','outer',96)]:
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);p=root/'parent';p.mkdir()
    for n in ('requirements.json','geometry.json'):(p/n).write_text('{}')
    (p/'geometry-request.json').write_text(json.dumps({'geometry_mm':{'length':60,'width':30,'height':40,'thickness':3.5},'mounting_holes':True}));(p/'bracket.stl').write_bytes(b'fixture')
    response=MagicMock();response.__enter__.return_value=response;response.read.return_value=b'{}'
    with patch('kcee.bracket_flow_run.urlopen',return_value=response),patch('kcee.bracket_flow_run.verified_archive',return_value=({},b'')),patch('kcee.bracket_flow_run.flow_version',return_value=COMPACT),patch('kcee.bracket_flow_run.save_completed',return_value=p):run_bracket_flow(root,'parent',{},mesh,domain,4,COMPACT,LOCAL_PROFILE)
    response.read.assert_called_once_with(limit*1024*1024+1)
 def test_cap_limited_mesh_is_flagged_in_saved_report(self):
  import zipfile
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'parent';p.mkdir()
   for n in ('requirements.json','geometry.json','geometry-request.json'):(p/n).write_text('{}')
   (p/'bracket.stl').write_bytes(b'fixture');sources=self.sources();fine=root/sources[5]['run_id'];fine.mkdir()
   with zipfile.ZipFile(fine/'cfd-artifacts.zip','w') as archive:archive.writestr('snappyHexMesh.log','No cells marked for refinement since reached limit 350000.')
   dest=save(root,'parent',{'manifest_sha256':'a'*64},sources);d=json.loads((dest/'cfd.json').read_text());self.assertFalse(d['checks']['fine_mesh_refinement_not_cap_limited']);self.assertTrue(d['fine_mesh_capacity_audit']['refinement_limit_reached']);self.assertTrue(any('cap-limited' in x for x in d['limits']))
