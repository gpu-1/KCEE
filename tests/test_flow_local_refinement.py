import copy,io,json,tempfile,unittest,zipfile,base64,hashlib
from pathlib import Path
from kcee.bracket_flow import make_case,LOCAL_PROFILE,LOCAL_REGIONS,domain_spec
from kcee.flow_local_refinement import summary,save
from kcee.flow_sampling import COMPACT,sampling_spec
try:
 import test_flow_combined as combined_fixtures
 import test_bracket_flow as bracket_fixtures
except ModuleNotFoundError:
 from tests import test_flow_combined as combined_fixtures,test_bracket_flow as bracket_fixtures

class LocalRefinementTests(unittest.TestCase):
 def sources(self):
  sources=combined_fixtures.CombinedFlowTests().sources()[0][1:];targeted=copy.deepcopy(sources)
  for source in sources+targeted:
   f=source['flow'];f['inputs']['probe_sampling']=COMPACT;f['sampling']=sampling_spec(COMPACT)
   for p in f['fixed_probes']:p['method']='compact wall-visible positive tetrahedral interpolation'
  for source in targeted:
   f=source['flow'];source['run_id']+='-targeted';f['cells']+=30000;f['inputs']['local_refinement_profile']=LOCAL_PROFILE;data={'regions':copy.deepcopy(LOCAL_REGIONS),'nominal_cell_m':max(domain_spec(f['mesh_name'],'far')['background_spacing_m'])/8};f['mesh']['targeted_refinement']=data;f['inputs']['targeted_refinement']=data
  return sources+targeted
 def test_matched_pairs_preserve_zero_and_gauge_invariance(self):
  sources=self.sources();d=summary(sources);self.assertTrue(all(d['checks'].values()));self.assertEqual(d['mesh_independence'],'not_established')
  for i,s in enumerate(sources):
   for p in s['flow']['fixed_probes']:p['kinematic_pressure_m2_s2']+=i*100
  for pair in summary(sources)['local_refinement_changes']:self.assertLess(pair['maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale'],1e-8)
 def test_recipe_sampling_source_domain_and_unavailable_probe_rejected(self):
  for case in ('region','sampling','source','domain','probe','bore'):
   sources=self.sources();f=sources[2]['flow']
   if case=='region':f['inputs']['targeted_refinement']['regions'][0]['min_m'][0]+=.001
   if case=='sampling':del f['inputs']['probe_sampling']
   if case=='source':f['source']['source_stl_sha256']='different'
   if case=='domain':f['inputs']['domain_min_m'][0]-=.01
   if case=='probe':f['fixed_probes'][0]['available']=False
   if case=='bore':f['inputs']['bore_refinement']['level']=5
   with self.subTest(case=case),self.assertRaises(ValueError):summary(sources)
 def test_targeted_dict_changes_only_local_mesh_recipe(self):
  raw=bracket_fixtures.BracketFlowTests().surface()
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'a';b=Path(d)/'b';make_case(a,raw,'medium','far');make_case(b,raw,'medium','far',4,LOCAL_PROFILE)
   for p in a.rglob('*'):
    if p.is_file() and p.name!='snappyHexMeshDict':self.assertEqual(p.read_bytes(),(b/p.relative_to(a)).read_bytes())
   text=(b/'system/snappyHexMeshDict').read_text();self.assertIn('targetWake {mode inside;levels ((1e15 3));}',text);self.assertIn('targetBelow {mode inside;levels ((1e15 3));}',text);self.assertIn('wake {mode inside;levels ((1e15 2));}',text);self.assertIn('bore1 {mode inside;levels ((1e15 4));}',text)
   for mesh,domain,bore,profile in [('coarse','far',4,LOCAL_PROFILE),('medium','base',4,LOCAL_PROFILE),('fine','far',5,LOCAL_PROFILE),('fine','far',4,'unknown')]:
    with self.assertRaises(ValueError):make_case(b,raw,mesh,domain,bore,profile)
 def test_report_inventory_and_csv_pressure_are_bound(self):
  from kcee.provenance import verify_directory,IntegrityError
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'parent';p.mkdir()
   for n in ('requirements.json','geometry.json','geometry-request.json'):(p/n).write_text('{}')
   (p/'bracket.stl').write_bytes(b'fixture');dest=save(root,'parent',{'manifest_sha256':'a'*64},self.sources());manifest,_=verify_directory(dest);self.assertEqual(manifest['kind'],'bracket_flow_local');self.assertEqual(len((dest/'verification.csv').read_text().splitlines()),37)
   (dest/'cfd.json').write_text('{}')
   with self.assertRaises(IntegrityError):verify_directory(dest)
 def test_targeted_archive_cannot_be_relabelled_baseline(self):
  from kcee.bracket_flow_run import verified_archive
  raw=bracket_fixtures.BracketFlowTests().surface();buffer=io.BytesIO();f=self.sources()[0]['flow']
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);make_case(p,raw,'medium','far',4,LOCAL_PROFILE)
   with zipfile.ZipFile(buffer,'w') as z:
    z.writestr('sampling.json',json.dumps(sampling_spec(COMPACT)));z.writestr('runtime.json',json.dumps({'package':'1912.200626-3+b1','binaries_sha256':{n:'a'*64 for n in ('snappyHexMesh','simpleFoam','checkMesh','surfaceCheck')}}))
    for file in p.rglob('*'):
     if file.is_file():z.write(file,file.relative_to(p).as_posix())
  data=buffer.getvalue()
  with self.assertRaisesRegex(ValueError,'case/source surface differs'):verified_archive({'result':f,'archive_base64':base64.b64encode(data).decode(),'archive_sha256':hashlib.sha256(data).hexdigest()},raw,'medium','far')

 def test_reuse_keeps_baseline_and_targeted_profiles_separate(self):
  from unittest.mock import patch
  from kcee.flow_sources import reusable
  baseline=self.sources()[0]['flow'];targeted=self.sources()[2]['flow']
  class Registry:
   def list(self,*args):return [{'id':n,'kind':'bracket_flow','parent_id':'parent'} for n in ('targeted','baseline')]
   def verify(self,*args):pass
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'parent').mkdir();(root/'parent/bracket.stl').write_bytes(b'stl')
   for name,flow in [('targeted',targeted),('baseline',baseline)]:
    p=root/name;p.mkdir();(p/'cfd.json').write_text(json.dumps(flow));(p/'cfd-artifacts.zip').write_bytes(b'archive')
   with patch('kcee.flow_sources.verify_directory',return_value=({'source_parent_manifest_sha256':'a'*64},'b'*64)),patch('kcee.flow_sources.verified_archive') as replay:
    a=reusable(root,'parent',{'manifest_sha256':'a'*64},Registry(),'medium','far')
    b=reusable(root,'parent',{'manifest_sha256':'a'*64},Registry(),'medium','far',local_profile=LOCAL_PROFILE)
   self.assertEqual(a['run_id'],'baseline');self.assertEqual(b['run_id'],'targeted');self.assertEqual(replay.call_count,2)
