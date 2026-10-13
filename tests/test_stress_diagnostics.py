import math,unittest
from kcee.stress_diagnostics import tetra_quality,stress_records,regional_peaks,diagnose

class StressDiagnosticsTests(unittest.TestCase):
    def test_regular_tetrahedron_quality_and_scale(self):
        points=[(0,0,0),(1,0,0),(.5,math.sqrt(3)/2,0),(.5,math.sqrt(3)/6,math.sqrt(2/3))]
        volume,quality=tetra_quality(points)
        self.assertAlmostEqual(quality,1);self.assertAlmostEqual(volume,math.sqrt(2)/12)
        scaled_volume,scaled_quality=tetra_quality([tuple(3*x for x in p) for p in points])
        self.assertAlmostEqual(scaled_quality,1);self.assertAlmostEqual(scaled_volume,27*volume)
    def test_inverted_tetrahedron_rejected(self):
        with self.assertRaises(ValueError):tetra_quality([(0,0,0),(0,1,0),(1,0,0),(0,0,1)])

    def test_non_finite_geometry_rejected(self):
        with self.assertRaises(ValueError):tetra_quality([(0,0,0),(1,0,0),(0,1,0),(0,0,float('nan'))])
    def test_complete_stress_table(self):
        rows=[[1,ip,10,0,0,0,0,0] for ip in (1,2,3,4)]
        self.assertEqual([r[0] for r in stress_records(rows,{1})],[10]*4)
    def test_missing_duplicate_and_invalid_stresses_rejected(self):
        rows=[[1,ip,10,0,0,0,0,0] for ip in (1,2,3,4)]
        for damaged in (rows[:-1],rows+[rows[0]],[[2,1,10,0,0,0,0,0]]+rows,[[1,1,float('nan'),0,0,0,0,0]]+rows[1:],[[1,1.5,10,0,0,0,0,0]]+rows[1:]):
            with self.subTest(damaged=damaged):
                with self.assertRaises(ValueError):stress_records(damaged,{1})

    def test_regional_peaks_keep_global_data_and_exclude_nominal_regions(self):
        stresses=[(100,1,1),(40,2,1),(200,3,1),(80,4,1)]
        centers={1:(0,15,10),2:(10,15,3),3:(58,15,3.5),4:(1.5,15,10)}
        rows=regional_peaks(stresses,centers)
        self.assertEqual([row['maximum_von_mises_MPa'] for row in rows],[80,40,40])
        self.assertEqual([row['included_elements'] for row in rows],[2,1,1]);self.assertEqual(max(stresses)[0],200)

    def test_mesh_selection_is_bounded(self):
        with self.assertRaisesRegex(ValueError,'Unsupported'):diagnose('unused.zip','../other')
