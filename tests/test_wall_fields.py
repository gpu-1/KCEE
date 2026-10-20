import copy,math,unittest
from kcee.wall_fields import face_fields
class WallFieldTests(unittest.TestCase):
 def fixture(self):
  expected={'pressure_force_N':[0,-6,0],'viscous_force_N':[-.4,.8,-1],'total_force_N':[-.4,-5.2,-1],'pressure_moment_N_m':[1.2,0,-.6],'viscous_moment_N_m':[-.16,.02,.08],'total_moment_N_m':[1.04,.02,-.52]}
  return [(7,0,[0,-1,0])],[[.1,0,.2]],[[.1,.2,.3,-.4,.5,.3]],[3],2,expected,1
 def test_physical_pressure_and_full_normal_viscous_traction(self):
  d=face_fields(*self.fixture());r=d['faces'][0];self.assertEqual(r['pressure_Pa'],6);self.assertEqual(r['viscous_traction_Pa'],[-.4,.8,-1]);self.assertEqual(r['total_traction_Pa'],[-.4,-5.2,-1]);self.assertTrue(all(d['checks'].values()))
  self.assertLess(max(d['relative_closure_errors'].values()),1e-14)
 def test_traction_uses_full_parent_face_area_not_render_triangle_area(self):
  m,c,t,p,rho,e,n=self.fixture();m=[(7,0,[0,-2,0])];e={k:[2*x for x in v] for k,v in e.items()};d=face_fields(m,c,t,p,rho,e,n);self.assertEqual(d['faces'][0]['area_m2'],2);self.assertEqual(d['faces'][0]['viscous_traction_Pa'],[-.4,.8,-1]);self.assertEqual(d['faces'][0]['pressure_force_N'],[0,-12,0])
 def test_changed_tensor_or_pressure_cannot_pass_global_native_closure(self):
  m,c,t,p,rho,e,n=self.fixture()
  for args in [(m,c,t,[4],rho,e,n),(m,c,[[.1,.2,.3,-.3,.5,.3]],p,rho,e,n)]:
   with self.assertRaisesRegex(ValueError,'reproduce native'):face_fields(*args)
 def test_rejects_zero_area_duplicates_and_nonfinite_fields(self):
  m,c,t,p,rho,e,n=self.fixture()
  for args in [([(7,0,[0,0,0])],c,t,p,rho,e,n),(m+m,c+c,t+t,p,rho,e,n),(m,c,t,[math.inf],rho,e,n)]:
   with self.assertRaises(ValueError):face_fields(*args)
