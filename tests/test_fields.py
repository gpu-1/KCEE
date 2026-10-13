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

    def transformed(self,transform):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        path=Path(directory.name)/'a.zip';self.archive(path)
        with zipfile.ZipFile(path) as z:files={name:z.read(name).decode() for name in z.namelist()}
        transform(files)
        with zipfile.ZipFile(path,'w') as z:
            for name,data in files.items():z.writestr(name,data)
        return path

    def test_hydrostatic_stress_has_zero_von_mises(self):
        def change(files):
            name='mesh-1.5/bracket.frd';s=files[name];start=s.index(' -4  STRESS')
            files[name]=s[:start]+' -4  STRESS      6    1\n'+''.join(f' -1{i:10d}'+''.join(f'{v:12.5E}' for v in (10,10,10,0,0,0))+'\n' for i in range(1,11))+' -3\n'
        self.assertEqual(displacement_surface(self.transformed(change))['maximum_surface_von_mises_MPa'],0)

    def test_pure_shear_von_mises(self):
        def change(files):
            name='mesh-1.5/bracket.frd';s=files[name];start=s.index(' -4  STRESS')
            files[name]=s[:start]+' -4  STRESS      6    1\n'+''.join(f' -1{i:10d}'+''.join(f'{v:12.5E}' for v in (0,0,0,10,0,0))+'\n' for i in range(1,11))+' -3\n'
        self.assertAlmostEqual(displacement_surface(self.transformed(change))['maximum_surface_von_mises_MPa'],10*3**.5)

    def test_incomplete_stress_rejected(self):
        def change(files):
            name='mesh-1.5/bracket.frd';s=files[name];start=s.index(' -4  STRESS');files[name]=s[:start]+s[start:].replace(next(line+'\n' for line in s[start:].splitlines() if line.startswith(' -1')),'',1)
        with self.assertRaisesRegex(ValueError,'stress'):displacement_surface(self.transformed(change))

    def test_unknown_connectivity_rejected(self):
        def change(files):files['mesh-1.5/bracket.inp']=files['mesh-1.5/bracket.inp'].replace('1,1,2,3,4,5,6,7,8,9,10','1,1,2,3,4,5,6,7,8,9,99')
        with self.assertRaisesRegex(ValueError,'connectivity'):displacement_surface(self.transformed(change))

    def test_duplicate_volume_elements_rejected(self):
        def change(files):files['mesh-1.5/bracket.inp']+='2,1,2,3,4,5,6,7,8,9,10\n3,1,2,3,4,5,6,7,8,9,10\n'
        with self.assertRaisesRegex(ValueError,'Non-manifold'):displacement_surface(self.transformed(change))
