import tempfile,unittest
from pathlib import Path
from kcee.flow_centres import volume_centres
class VolumeCentreTests(unittest.TestCase):
 def mesh(self,root,points,faces,owners,neighbours=()):
  for name,values in [('points',['('+ ' '.join(map(str,p))+')' for p in points]),('faces',[str(len(f))+'('+ ' '.join(map(str,f))+')' for f in faces]),('owner',list(map(str,owners))),('neighbour',list(map(str,neighbours)))]:
   (root/name).write_text('FoamFile {}\n'+str(len(values))+'\n('+' '.join(values)+')')
 def test_skew_pyramid_volume_moments_and_translation(self):
  for shift in (0.,1000000.):
   with tempfile.TemporaryDirectory() as d:
    root=Path(d);self.mesh(root,[(x+shift,y+shift,z+shift) for x,y,z in [(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0),(0,0,2)]],[(0,3,2,1),(0,1,4),(1,2,4),(2,3,4),(3,0,4)],[0]*5)
    centres,means,audit=volume_centres(root,1)
    self.assertAlmostEqual(audit['total_fluid_volume_m3'],8/3);self.assertAlmostEqual(centres[0][2],shift+.5);self.assertAlmostEqual(means[0][2],shift+.4);self.assertAlmostEqual(audit['maximum_vertex_mean_to_volume_centroid_m'],.1)
 def test_internal_face_orientation_for_both_adjacent_cells(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.mesh(root,[(0,0,0),(1,0,0),(0,1,0),(0,0,1),(0,0,-1)],[(0,2,1),(0,1,3),(1,2,3),(2,0,3),(0,4,1),(1,4,2),(2,4,0)],[0,0,0,0,1,1,1],[1])
   centres,means,audit=volume_centres(root,2)
   for a,b in zip(centres,[(.25,.25,.25),(.25,.25,-.25)]):
    for x,y in zip(a,b):self.assertAlmostEqual(x,y)
   self.assertAlmostEqual(audit['total_fluid_volume_m3'],1/3)
 def test_reversed_cell_faces_are_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.mesh(root,[(0,0,0),(1,0,0),(0,1,0),(0,0,1)],[(0,1,2),(3,1,0),(3,2,1),(3,0,2)],[0]*4)
   with self.assertRaisesRegex(ValueError,'Nonpositive'):volume_centres(root,1)
