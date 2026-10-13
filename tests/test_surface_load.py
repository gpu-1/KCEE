import unittest
from kcee.surface_load import strip_weights

class SurfaceLoadTests(unittest.TestCase):
    def test_full_quadratic_face(self):
        area,weights=strip_weights([(0,0,0),(2,0,0),(0,2,0)],0)
        self.assertAlmostEqual(area,2)
        for w in weights[:3]:self.assertAlmostEqual(w,0)
        for w in weights[3:]:self.assertAlmostEqual(w,2/3)
    def test_clipped_area_and_first_moment(self):
        area,w=strip_weights([(0,0,0),(2,0,0),(0,2,0)],1)
        self.assertAlmostEqual(area,.5);self.assertAlmostEqual(sum(w),area)
        self.assertAlmostEqual(sum(a*b for a,b in zip(w,[0,2,0,1,1,0])),area*4/3)
        self.assertAlmostEqual(sum(a*b for a,b in zip(w,[0,0,2,0,1,1])),area/3)
    def test_outside_face(self):
        self.assertEqual(strip_weights([(0,0,0),(2,0,0),(0,2,0)],3),(0.,[0.]*6))

    def test_source_stl_strip_area(self):
        import struct,tempfile
        from pathlib import Path
        from kcee.surface_load import stl_strip_area
        raw=b'\0'*80+struct.pack('<I',1)+struct.pack('<12fH',0,0,1,54,0,3.5,56,0,3.5,54,2,3.5,0)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'face.stl';p.write_bytes(raw);self.assertAlmostEqual(stl_strip_area(p),.5)
            p.write_bytes(raw[:-1])
            with self.assertRaises(ValueError):stl_strip_area(p)
