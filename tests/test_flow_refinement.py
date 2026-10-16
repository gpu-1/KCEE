import unittest,copy
from unittest.mock import patch
from kcee.flow_bores import open_rays,OFFSETS,bore_checks
from kcee.flow_refinement import comparison_summary,report_markdown
class FlowRefinementTests(unittest.TestCase):
 def test_axial_rays_detect_blocked_and_open_paths_in_both_plate_directions(self):
  for axis in (0,2):
   transverse=[k for k in range(3) if k!=axis]
   def p(x,y):
    v=[0.,0.,0.];v[axis]=.00175;v[transverse[0]]=x;v[transverse[1]]=y;return tuple(v)
   wall=[[p(-.01,-.01),p(.01,-.01),p(.01,.01)],[p(-.01,-.01),p(.01,.01),p(-.01,.01)]]
   self.assertFalse(any(open_rays(wall,axis,(0,0))));self.assertTrue(all(open_rays([],axis,(0,0))));self.assertEqual(len(OFFSETS),85)
 def test_bore_gate_detects_closure_and_widening_not_just_open_center(self):
  source=[True]*69+[False]*16
  for mesh in [[False]*85,[True]*85]:
   with patch('kcee.flow_bores.source_triangles',return_value=[]),patch('kcee.flow_bores.wall_triangles',return_value=[]),patch('kcee.flow_bores.open_rays',side_effect=[v for _ in range(4) for v in (source,mesh)]):r=bore_checks(b'',None)
   self.assertFalse(r['all_pass']);self.assertTrue(all(not h['passes_sampling_gate'] for h in r['rows']))
 def studies(self):
  out=[]
  for i,name in enumerate(('coarse','medium','fine')):
   row={'x_m':.08,'y_m':.015,'z_m':.02,'u_m_s':.01+i*.001,'v_m_s':0.,'w_m_s':0.,'p_kinematic_m2_s2':i*.00001}
   flow={'mesh_name':name,'source':{'source_stl_sha256':'a'*64},'inputs':{'background_cells':[24+i,14,16],'inlet_velocity_m_s':.01},'field':[row],'cells':100+i,'mesh':{'near_surface_nominal_cell_m':.002-i*.0002},'checks':{'mesh_quality':True},'residuals':{'p':1e-9},'relative_boundary_mass_imbalance':1e-9,'bore_verification':{'all_pass':True,'rows':[],'method':'fixture'}}
   out.append({'run_id':name,'manifest_sha256':'b'*64,'flow':flow})
  return out
 def test_comparison_retains_physical_and_actual_probe_locations_and_scales(self):
  result=comparison_summary(self.studies());self.assertEqual(result['mesh_independence'],'not_established');self.assertTrue(all(result['checks'].values()));self.assertEqual(len(result['studies'][0]['probes']),8)
  wake=next(p for p in result['studies'][0]['probes'] if p['name']=='wake');self.assertEqual(wake['distance_m'],0);self.assertEqual(wake['requested_position_m'],wake['sample_position_m'])
  self.assertAlmostEqual(result['successive_changes'][0]['maximum_velocity_change_normalized_by_inlet'],.1);self.assertAlmostEqual(result['successive_changes'][0]['maximum_pressure_change_normalized_by_inlet_dynamic_scale'],.2)
  report=report_markdown(result);self.assertIn('Sample position',report);self.assertIn('not established',report);self.assertIn('b'*64,report)
 def test_mixed_source_domains_and_mesh_order_are_rejected(self):
  a=self.studies();a[1]['flow']['source']['source_stl_sha256']='c'*64
  with self.assertRaises(ValueError):comparison_summary(a)
  a=self.studies();a[1]['flow']['inputs']['inlet_velocity_m_s']=.02
  with self.assertRaises(ValueError):comparison_summary(a)
  with self.assertRaises(ValueError):comparison_summary(list(reversed(self.studies())))
