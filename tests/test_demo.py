import copy, hashlib, json, tempfile, unittest
from collections import Counter
from unittest.mock import patch
from kcee.demo import DEFAULT, run, screen, validate, stl

class DemoTests(unittest.TestCase):
    def setUp(self): self.req=json.loads(DEFAULT.read_text())
    def test_scaling(self):
        a=screen(self.req,3); b=screen(self.req,6)
        self.assertAlmostEqual(a['stress_MPa']/b['stress_MPa'],4)
        self.assertAlmostEqual(a['tip_deflection_mm']/b['tip_deflection_mm'],8)
    def test_invalid(self):
        for val in (0,-1,float('nan'),float('inf')):
            req=copy.deepcopy(self.req);req['load_N']=val
            with self.assertRaises(ValueError): validate(req)
    def test_provenance_and_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=run(tmp); m=json.loads((dest/'manifest.json').read_text())
            for name,digest in m['artifacts'].items(): self.assertEqual(hashlib.sha256((dest/name).read_bytes()).hexdigest(),digest)
            result=json.loads((dest/'result.json').read_text());self.assertEqual(result['selected']['thickness_mm'],3.5)
            self.assertEqual(result['validation_status'],'unvalidated_analytical_screening')
    def test_closed_mesh(self):
        vertices=[tuple(map(float,line.split()[1:])) for line in stl(self.req['geometry_mm']).splitlines() if line.startswith('vertex')]
        edges=Counter()
        for i in range(0,len(vertices),3):
            a,b,c=vertices[i:i+3]
            for p,q in ((a,b),(b,c),(c,a)): edges[tuple(sorted((p,q)))]+=1
        self.assertTrue(all(n==2 for n in edges.values()))

    def test_run_without_git_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('kcee.demo.subprocess.check_output',side_effect=FileNotFoundError):
                dest=run(tmp)
            manifest=json.loads((dest/'manifest.json').read_text())
            self.assertIsNone(manifest['software_commit'])
            self.assertEqual(len(manifest['source_sha256']),64)
