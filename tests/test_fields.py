import tempfile,unittest,zipfile
from pathlib import Path
from kcee.fields import displacement_surface

class FieldsTest(unittest.TestCase):
    def archive(self,path,missing=False):
        nodes=[(0,0,0),(1,0,0),(0,1,0),(0,0,1),(.5,0,0),(.5,.5,0),(0,.5,0),(0,0,.5),(.5,0,.5),(0,.5,.5)]
        inp='*NODE\n'+''.join(f'{i},'+','.join(map(str,p))+'\n' for i,p in enumerate(nodes,1))+'*ELEMENT,TYPE=C3D10\n1,1,2,3,4,5,6,7,8,9,10\n'
        frd=' -4  DISP        4    1\n'+''.join(f' -1{i:10d}{0.:12.5E}{0.:12.5E}{-i/10:12.5E}\n' for i in range(1,10 if missing else 11))+' -3\n -4  STRESS      6    1\n'+''.join(f' -1{i:10d}{10.:12.5E}{0.:12.5E}{0.:12.5E}{0.:12.5E}{0.:12.5E}{0.:12.5E}\n' for i in range(1,11))+' -3\n'
        with zipfile.ZipFile(path,'w') as z:z.writestr('mesh-1.5/bracket.inp',inp);z.writestr('mesh-1.5/bracket.frd',frd)
    def test_surface_preserves_midsides_and_displacements(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.zip';self.archive(p);f=displacement_surface(p)
            self.assertEqual(len(f['triangles']),16);self.assertEqual(len(f['positions']),10);self.assertEqual(f['maximum_displacement_mm'],1.);self.assertEqual(f['maximum_surface_von_mises_MPa'],10.);self.assertEqual(f['von_mises_MPa'],[10.]*10)
    def test_missing_displacement_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.zip';self.archive(p,True)
            with self.assertRaises(ValueError):displacement_surface(p)
