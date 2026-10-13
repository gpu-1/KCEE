import math,struct,tempfile,unittest
from pathlib import Path
from kcee.geometry_measure import hole_sections

class GeometryMeasurementTests(unittest.TestCase):
    def test_square_sections_have_known_radial_envelope(self):
        triangles=[]
        for axis,center in [(2,(33,15)),(2,(48,15)),(0,(15,16)),(0,(15,30))]:
            transverse=[j for j in range(3) if j!=axis]
            def point(offset,height):
                p=[0,0,0];p[axis]=height
                for k,j in enumerate(transverse):p[j]=center[k]+offset[k]
                return p
            corners=[(-2,-2),(2,-2),(2,2),(-2,2)]
            for i in range(4):
                a=point(corners[i],0);b=point(corners[(i+1)%4],0);c=point(corners[(i+1)%4],3.5);d=point(corners[i],3.5)
                triangles.extend(((a,b,c),(a,c,d)))
        raw=b'\0'*80+struct.pack('<I',len(triangles))
        for t in triangles:raw+=struct.pack('<12fH',0,0,0,*(v for p in t for v in p),0)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'shape.stl';p.write_bytes(raw);rows=hole_sections(p)
        self.assertEqual(len(rows),4)
        for row in rows:
            self.assertAlmostEqual(row['minimum_radial_diameter_mm'],4)
            self.assertAlmostEqual(row['maximum_radial_diameter_mm'],4*math.sqrt(2))
