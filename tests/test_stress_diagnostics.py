import math,unittest
from kcee.stress_diagnostics import tetra_quality

class StressDiagnosticsTests(unittest.TestCase):
    def test_regular_tetrahedron_quality_and_scale(self):
        points=[(0,0,0),(1,0,0),(.5,math.sqrt(3)/2,0),(.5,math.sqrt(3)/6,math.sqrt(2/3))]
        volume,quality=tetra_quality(points)
        self.assertAlmostEqual(quality,1);self.assertAlmostEqual(volume,math.sqrt(2)/12)
        scaled_volume,scaled_quality=tetra_quality([tuple(3*x for x in p) for p in points])
        self.assertAlmostEqual(scaled_quality,1);self.assertAlmostEqual(scaled_volume,27*volume)
    def test_inverted_tetrahedron_rejected(self):
        with self.assertRaises(ValueError):tetra_quality([(0,0,0),(0,1,0),(1,0,0),(0,0,1)])
