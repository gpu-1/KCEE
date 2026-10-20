import math,unittest
from kcee.regional_wall import triangulate
class RegionalWallTests(unittest.TestCase):
 def fixture(self):return ([[0,0,0],[.01,0,0],[.01,.01,0],[0,.01,0]],[[0,1,2,3]],[(0,0,[0,0,.0001])],[[.033,.015,.00175]],[1,0,0,0,0,0,0])
 def test_polygon_triangles_inherit_native_face_region_and_source_identity(self):
  d=triangulate(*self.fixture());self.assertEqual(d['positions_mm'][2],[10,10,0]);self.assertEqual(d['triangles'],[[0,1,2],[0,2,3]]);self.assertEqual(d['triangle_regions'],[0,0]);self.assertEqual(d['triangle_source_faces'],[0,0]);self.assertEqual(d['wall_faces'],1)
 def test_display_counts_must_equal_integrated_face_counts(self):
  p,f,w,c,_=self.fixture()
  with self.assertRaisesRegex(ValueError,'integrated regions'):triangulate(p,f,w,c,[0,0,0,0,1,0,0])
 def test_bad_mesh_addressing_and_nonfinite_positions_are_rejected(self):
  p,f,w,c,n=self.fixture()
  for args in [(p,[[0,1,9]],w,c,n),(p,[[0,1,1]],w,c,n),([[math.nan,0,0],*p[1:]],f,w,c,n),(p,f,w+w,c+c,[2,0,0,0,0,0,0])]:
   with self.assertRaises(ValueError):triangulate(*args)
 def test_multiple_triangles_count_parent_face_once(self):
  p,f,w,c,n=self.fixture();d=triangulate(p,[*f,[0,1,2]],[*w,(1,0,[0,0,1])],[*c,[.003,.02,.035]],[1,0,0,0,0,0,1]);self.assertEqual(d['region_face_counts'],[1,0,0,0,0,0,1]);self.assertEqual(d['triangle_regions'],[0,0,6])
