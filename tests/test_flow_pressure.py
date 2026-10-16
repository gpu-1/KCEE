import copy,tempfile,unittest
from pathlib import Path
from kcee.bracket_flow import make_case
from kcee.flow_pressure import summary
try:import test_flow_combined as fixtures
except ModuleNotFoundError:from tests import test_flow_combined as fixtures
class BorePressureTests(unittest.TestCase):
 def sources(self):
  all_sources,_=fixtures.CombinedFlowTests().sources();sources=all_sources[1:];refined=copy.deepcopy(sources)
  for s in sources:s['flow']['mesh']['bore_refinement']={'nominal_cell_m':.0007};s['flow']['inputs']['bore_refinement']['nominal_cell_m']=.0007
  for s in refined:
   s['run_id']+='-refined';s['flow']['cells']+=10000;s['flow']['inputs']['bore_refinement']['level']=5;s['flow']['inputs']['bore_refinement']['nominal_cell_m']=.00035
  sources+=refined;audits={}
  for s in sources:
   s['archive_sha256']='a'*64;audits[s['run_id']]={'source_archive_sha256':'a'*64,'total_cells':s['flow']['cells'],'native_centres_exported':10,'stencil_audit':{'compact_probes':copy.deepcopy(s['flow']['fixed_probes'])}}
  return sources,audits
 def test_matched_pairs_and_zero_gauge_invariance(self):
  sources,audits=self.sources();a=summary(sources,audits)
  self.assertEqual(len(a['background_mesh_changes']),2);self.assertEqual(len(a['local_bore_changes']),2)
  for i,s in enumerate(sources):
   for p in s['flow']['fixed_probes']+audits[s['run_id']]['stencil_audit']['compact_probes']:p['kinematic_pressure_m2_s2']+=i*100
  b=summary(sources,audits)
  for pair in b['local_bore_changes']:self.assertLess(pair['maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale'],1e-8)
  self.assertEqual(a['mesh_independence'],'not_established')
 def test_mixed_recipe_missing_probe_and_wrong_audit_rejected(self):
  for kind in ('source','audit','probes','level'):
   sources,audits=self.sources()
   if kind=='source':sources[2]['flow']['source']['source_stl_sha256']='different'
   if kind=='audit':audits[sources[2]['run_id']]['source_archive_sha256']='different'
   if kind=='probes':sources[2]['flow']['fixed_probes'][0]['available']=False
   if kind=='level':sources[2]['flow']['inputs']['bore_refinement']['level']=4
   with self.assertRaises(ValueError):summary(sources,audits)
 def test_bore_level_strict_and_only_local_recipe_changes(self):
  import struct
  verts=[(0.,0.,0.),(60.,0.,0.),(0.,30.,0.),(0.,0.,40.)];raw=b' '*80+struct.pack('<I',4)
  for inds in [(0,2,1),(0,1,3),(1,2,3),(2,0,3)]:raw+=struct.pack('<12fH',0,0,0,*[v for i in inds for v in verts[i]],0)
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp)/'a';b=Path(tmp)/'b';make_case(a,raw,'medium','far');make_case(b,raw,'medium','far',5)
   for p in a.rglob('*'):
    if p.is_file() and p.name!='snappyHexMeshDict':self.assertEqual(p.read_bytes(),(b/p.relative_to(a)).read_bytes())
   text=(b/'system/snappyHexMeshDict').read_text();self.assertEqual(text.count('levels ((1e15 5))'),4);self.assertIn('maxGlobalCells 250000',text)
   for value in (True,3,6,4.0):
    with self.assertRaises(ValueError):make_case(b,raw,'medium','far',value)
 def test_saved_report_inventory_is_verified_and_tampering_detected(self):
  import json
  from kcee.flow_pressure import save
  from kcee.provenance import verify_directory,IntegrityError
  sources,audits=self.sources()
  for a in audits.values():a['coverage_fraction']=.001
  for s in sources:s['flow']['inputs']['bore_refinement']['nominal_cell_m']=.0003
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);parent=root/'parent';parent.mkdir()
   for name in ('requirements.json','geometry.json','geometry-request.json'):(parent/name).write_text('{}')
   (parent/'bracket.stl').write_bytes(b'fixture')
   dest=save(root,'parent',{'manifest_sha256':'f'*64},sources,audits);manifest,_=verify_directory(dest);self.assertEqual(manifest['kind'],'bracket_flow_pressure')
   self.assertEqual(len((dest/'verification.csv').read_text().splitlines()),37)
   (dest/'cfd.json').write_text('{}')
   with self.assertRaises(IntegrityError):verify_directory(dest)
 def test_compact_stencil_is_linear_exact_and_no_wider_than_saved_method(self):
  import random
  from kcee.flow_sampling import interpolate
  random.seed(8);field=[]
  for _ in range(40):
   x,y,z=[random.uniform(-1,1) for k in range(3)];field.append(dict(x_m=x,y_m=y,z_m=z,u_m_s=x+2*y,v_m_s=3*z,w_m_s=0,p_kinematic_m2_s2=2*x-y+z))
  point=(.2,.1,-.1);old=interpolate(field,point);compact=interpolate(field,point,compact=True)
  self.assertLessEqual(compact['maximum_support_distance_m'],old['maximum_support_distance_m']);self.assertAlmostEqual(compact['kinematic_pressure_m2_s2'],.2);self.assertAlmostEqual(sum(compact['weights']),1);self.assertGreaterEqual(min(compact['weights']),0)
