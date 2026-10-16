import copy,io,json,unittest,zipfile,base64,hashlib,tempfile
from pathlib import Path
from unittest.mock import patch
from kcee.flow_sampling import LEGACY,COMPACT,DEFAULT,sampling_spec,flow_version,common_sampling
try:
 import test_flow_domain as domain_fixtures
 import test_flow_combined as combined_fixtures
 import test_flow_refinement as mesh_fixtures
 import test_bracket_flow as bracket_fixtures
except ModuleNotFoundError:
 from tests import test_flow_domain as domain_fixtures,test_flow_combined as combined_fixtures,test_flow_refinement as mesh_fixtures,test_bracket_flow as bracket_fixtures

def compact(studies):
 for source in studies:
  flow=source['flow'];flow['inputs']['probe_sampling']=COMPACT;flow['sampling']=sampling_spec(COMPACT)
  for p in flow['fixed_probes']:
   if p['available']:p['method']='compact wall-visible positive tetrahedral interpolation'
 return studies

class SamplingVersionTests(unittest.TestCase):
 def test_default_and_legacy_inference_are_explicit_and_strict(self):
  self.assertEqual(DEFAULT,COMPACT);self.assertEqual(flow_version({}),LEGACY)
  for bad in ('unknown',None,False):
   with self.assertRaises(ValueError):sampling_spec(bad)
  flow=compact(domain_fixtures.DomainStudyTests().studies())[0]['flow'];self.assertEqual(flow_version(flow),COMPACT)
  for change in ('descriptor','probe','missing_input'):
   f=copy.deepcopy(flow)
   if change=='descriptor':f['sampling']['candidate_limit']=999
   if change=='probe':f['fixed_probes'][0]['method']='wall-visible positive tetrahedral interpolation'
   if change=='missing_input':del f['inputs']['probe_sampling']
   with self.assertRaises(ValueError):flow_version(f)
 def test_all_comparison_families_reject_mixed_sampling(self):
  from kcee.flow_domain import summary
  from kcee.flow_combined import mesh_summary
  from kcee.flow_refinement import comparison_summary
  for studies,fn in [(domain_fixtures.DomainStudyTests().studies(),summary),(combined_fixtures.CombinedFlowTests().sources()[0],mesh_summary),(mesh_fixtures.FlowRefinementTests().studies(),comparison_summary)]:
   compact(studies[:1])
   with self.assertRaisesRegex(ValueError,'mix CFD sampling'):fn(studies)
 def test_compact_schemas_and_upstream_gauge_policy(self):
  from kcee.flow_domain import summary
  from kcee.flow_refinement import comparison_summary
  self.assertEqual(summary(compact(domain_fixtures.DomainStudyTests().studies()))['schema'],'kcee.bracket-flow-domain.v2')
  sources=compact(mesh_fixtures.FlowRefinementTests().studies())
  for i,s in enumerate(sources):
   for p in s['flow']['fixed_probes']:p['kinematic_pressure_m2_s2']+=i*100
  data=comparison_summary(sources);self.assertEqual(data['schema'],'kcee.bracket-flow-refinement.v4');self.assertEqual(data['pressure_reference'],'fixed_upstream_probe')
  for pair in data['successive_changes']:self.assertLess(pair['maximum_pressure_change_normalized_by_inlet_dynamic_scale'],1e-8)
 def test_archive_version_cannot_be_silently_relabelled(self):
  from kcee.bracket_flow_run import verified_archive
  flow=compact(domain_fixtures.DomainStudyTests().studies())[0]['flow'];buffer=io.BytesIO();runtime={'package':'1912.200626-3+b1','binaries_sha256':{n:'a'*64 for n in ('snappyHexMesh','simpleFoam','checkMesh','surfaceCheck')}}
  with zipfile.ZipFile(buffer,'w') as z:z.writestr('runtime.json',json.dumps(runtime))
  raw=buffer.getvalue();payload={'archive_base64':base64.b64encode(raw).decode(),'archive_sha256':hashlib.sha256(raw).hexdigest(),'result':flow}
  with self.assertRaisesRegex(ValueError,'Archive sampling version'):verified_archive(payload,b'fixture')
 def test_fresh_worker_archive_declares_compact_version_even_on_failure(self):
  from kcee.bracket_flow import run_payload
  raw=bracket_fixtures.BracketFlowTests().surface()
  with patch('kcee.bracket_flow.command',side_effect=ValueError('fixture')),patch('kcee.bracket_flow.subprocess.check_output',return_value='1912.200626-3+b1'),patch('shutil.which',return_value=__file__):data=run_payload(raw)
  with zipfile.ZipFile(io.BytesIO(base64.b64decode(data['archive_base64']))) as z:self.assertEqual(json.loads(z.read('sampling.json')),sampling_spec(COMPACT))
 def test_resampling_repackages_only_sampling_metadata_and_preserves_old_object(self):
  from kcee.flow_resampling import resample_archive
  old={'inputs':{},'field':[],'cells':0};buffer=io.BytesIO()
  members={'constant/polyMesh/'+n:b'original-'+n.encode() for n in ('points','faces','owner','neighbour','boundary')};members['1500/U']=b'unchanged velocity';members['1500/p']=b'unchanged pressure'
  with zipfile.ZipFile(buffer,'w') as z:
   for name,raw in members.items():z.writestr(name,raw)
  original=buffer.getvalue()
  def replay(payload,*args):return (old,original) if 'fixture' in payload else (payload['result'],base64.b64decode(payload['archive_base64']))
  def apply(flow,*args):flow['inputs']['probe_sampling']=COMPACT;flow['sampling']=sampling_spec(COMPACT)
  with patch('kcee.flow_resampling.verified_archive',side_effect=replay) as verify,patch('kcee.flow_resampling.cell_positions',return_value=[]),patch('kcee.flow_resampling.apply_sampling',side_effect=apply):flow,data=resample_archive({'fixture':True},b'stl','coarse')
  self.assertEqual(verify.call_count,2);self.assertEqual(old['inputs'],{});self.assertEqual(flow['inputs']['probe_sampling'],COMPACT)
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   for name,raw in members.items():self.assertEqual(z.read(name),raw)
   self.assertEqual(json.loads(z.read('sampling.json')),sampling_spec(COMPACT))
 def test_compact_combined_requires_compact_domain_schema_and_exact_metadata(self):
  from kcee.flow_combined import combined_summary
  sources,domain=combined_fixtures.CombinedFlowTests().sources();compact(sources);d=domain['data'];d['sampling']=sampling_spec(COMPACT);d['schema']='kcee.bracket-flow-domain.v2';d['common_inputs']['probe_sampling']=COMPACT
  result=combined_summary(sources,domain);self.assertEqual(result['schema'],'kcee.bracket-flow-combined.v2');self.assertEqual(result['sampling']['version'],COMPACT)
  d['sampling']=sampling_spec(LEGACY)
  with self.assertRaisesRegex(ValueError,'sampling versions differ'):combined_summary(sources,domain)
 def test_reuse_skips_legacy_sources_and_rechecks_compact_archive(self):
  from kcee.flow_sources import reusable
  studies=domain_fixtures.DomainStudyTests().studies();old=studies[0]['flow'];new=compact(copy.deepcopy(studies))[0]['flow']
  for f in (old,new):f['inputs']['bore_refinement']={'level':4}
  class Registry:
   def list(self,*args):return [{'id':'legacy','kind':'bracket_flow','parent_id':'parent'},{'id':'current','kind':'bracket_flow','parent_id':'parent'}]
   def verify(self,*args):pass
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'parent').mkdir();(root/'parent/bracket.stl').write_bytes(b'stl')
   for name,f in [('legacy',old),('current',new)]:
    p=root/name;p.mkdir();(p/'cfd.json').write_text(json.dumps(f));(p/'cfd-artifacts.zip').write_bytes(b'archive')
   with patch('kcee.flow_sources.verify_directory',return_value=({'source_parent_manifest_sha256':'a'*64},'b'*64)),patch('kcee.flow_sources.verified_archive') as verify:result=reusable(root,'parent',{'manifest_sha256':'a'*64},Registry(),'medium')
   self.assertEqual(result['run_id'],'current');self.assertTrue(result['reused']);self.assertEqual(verify.call_count,1)
