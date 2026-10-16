import copy,csv,json,math,tempfile,unittest
from pathlib import Path
from kcee.flow_reference import summary,save,PAIRS
from kcee.bracket_flow import domain_spec,make_case,LOCAL_PROFILE
try:import test_flow_local_refinement as fixtures
except ModuleNotFoundError:from tests import test_flow_local_refinement as fixtures
class ReferenceStudyTests(unittest.TestCase):
 def sources(self):
  sources=fixtures.LocalRefinementTests().sources();outer=copy.deepcopy(sources[2]);outer['run_id']='outer';f=outer['flow'];f['domain_name']='outer'
  for k in ('domain_min_m','domain_max_m','background_cells'):f['inputs'][k]=domain_spec('medium','outer')[k]
  sources.append(outer);return sources
 def test_gauge_invariance_and_signed_decomposition(self):
  sources=self.sources()
  for i,s in enumerate(sources):
   for j,p in enumerate(s['flow']['fixed_probes']):p['kinematic_pressure_m2_s2']+=(i+1)*j*1e-6
  before=summary(sources)
  for i,s in enumerate(sources):
   for p in s['flow']['fixed_probes']:p['kinematic_pressure_m2_s2']+=i*3
  after=summary(sources);self.assertTrue(all(after['checks'].values()));self.assertEqual(after['local_maximum_excludes'],['upstream'])
  for a,b in zip(before['comparisons'],after['comparisons']):
   for p,q in zip(a['probes'],b['probes']):
    self.assertAlmostEqual(p['upstream_referenced_change_m2_s2'],q['upstream_referenced_change_m2_s2'],places=13)
    self.assertAlmostEqual(q['upstream_referenced_change_m2_s2'],q['local_anchor_change_m2_s2']+q['anchor_upstream_change_m2_s2'],places=13)
   for p,q in zip(a['local_pressure_pairs'],b['local_pressure_pairs']):self.assertAlmostEqual(p['change_m2_s2'],q['change_m2_s2'],places=13)
 def test_local_pairs_resist_common_local_pressure_shift(self):
  sources=self.sources()
  for p in sources[4]['flow']['fixed_probes']:
   if p['name']!='upstream':p['kinematic_pressure_m2_s2']+=1e-5
  pair=summary(sources)['comparisons'][-1]
  self.assertAlmostEqual(pair['maximum_upstream_referenced_change_normalized'],.2)
  self.assertAlmostEqual(pair['maximum_local_anchor_change_normalized'],0)
  self.assertAlmostEqual(pair['maximum_local_pair_change_normalized'],0)
  self.assertAlmostEqual(pair['anchor_upstream_change_normalized'],.2)
 def test_mismatched_outer_recipe_or_probes_rejected(self):
  for mutation in ('source','profile','domain','spacing','sampling','probe','basis','refinement'):
   sources=self.sources();f=sources[-1]['flow']
   if mutation=='source':f['source']['source_stl_sha256']='other'
   if mutation=='profile':f['inputs']['local_refinement_profile']='baseline'
   if mutation=='domain':f['domain_name']='far'
   if mutation=='spacing':f['inputs']['background_cells'][0]+=1
   if mutation=='sampling':del f['sampling']
   if mutation=='probe':f['fixed_probes'][0]['available']=False
   if mutation=='basis':f['field_position_basis']='other'
   if mutation=='refinement':f['mesh']['targeted_refinement']['regions'][0]['level']=2
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):summary(sources)
 def test_outer_keeps_spacing_alignment_and_nonmesh_dicts(self):
  a=domain_spec('medium','far');b=domain_spec('medium','outer')
  self.assertEqual(a['background_spacing_m'],b['background_spacing_m'])
  for lo,outer,h in zip(a['domain_min_m'],b['domain_min_m'],a['background_spacing_m']):self.assertAlmostEqual((lo-outer)/h,4)
  with self.assertRaises(ValueError):domain_spec('fine','outer')
  raw=fixtures.bracket_fixtures.BracketFlowTests().surface()
  with tempfile.TemporaryDirectory() as tmp:
   x=Path(tmp)/'a';y=Path(tmp)/'b';make_case(x,raw,'medium','far',4,LOCAL_PROFILE);make_case(y,raw,'medium','outer',4,LOCAL_PROFILE)
   for file in x.rglob('*'):
    if file.is_file() and file.name!='blockMeshDict':self.assertEqual(file.read_bytes(),(y/file.relative_to(x)).read_bytes())
 def test_saved_inventory_and_csv_decomposition(self):
  from kcee.provenance import verify_directory,IntegrityError
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'parent';p.mkdir()
   for name in ('requirements.json','geometry.json','geometry-request.json'):(p/name).write_text('{}')
   (p/'bracket.stl').write_bytes(b'fixture');dest=save(root,'parent',{'manifest_sha256':'a'*64},self.sources());m,_=verify_directory(dest);self.assertEqual(m['kind'],'bracket_flow_reference')
   with (dest/'verification.csv').open() as stream:rows=list(csv.DictReader(stream))
   self.assertEqual(len(rows),39)
   for row in rows:
    if row['kind']=='probe':self.assertAlmostEqual(float(row['upstream_referenced_change_m2_s2']),float(row['local_anchor_change_m2_s2'])+float(row['anchor_upstream_change_m2_s2']),places=14)
   (dest/'cfd.json').write_text('{}')
   with self.assertRaises(IntegrityError):verify_directory(dest)
