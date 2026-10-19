"""Layer recipes retain historical cases and report measured partial coverage."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from kcee.bracket_flow import make_case,layer_audit,validate_profile
from kcee.cfd_jobs import validate
class Layers(unittest.TestCase):
 def test_partial_final_coverage(self):
  a=layer_audit('Extruding 95 out of 100 faces (95%).\nExtruding 83 out of 100 faces (83%).')
  self.assertEqual(a['extruded_faces'],83);self.assertEqual(a['extruded_face_fraction'],.83)
  self.assertEqual(a['requested_layers'],3)
 def test_missing_or_invalid_coverage(self):
  for text in ('layers requested 3','Extruding 2 out of 1 faces','Extruding 0 out of 0 faces'):
   with self.assertRaises(ValueError):layer_audit(text)
 def test_layer_recipe_changes_only_meshing(self):
  with tempfile.TemporaryDirectory() as tmp,patch('kcee.bracket_flow.prepare_surface',return_value=(b'solid bracket\nendsolid bracket\n',{})):
   a=Path(tmp)/'old';b=Path(tmp)/'new'
   make_case(a,b'fixture','medium','far',4,'wake-below-v1');make_case(b,b'fixture','medium','far',4,'wall-layers-v1')
   differences=[p.relative_to(a).as_posix() for p in a.rglob('*') if p.is_file() and p.read_bytes()!=(b/p.relative_to(a)).read_bytes()]
   self.assertEqual(differences,['system/snappyHexMeshDict'])
   self.assertIn('addLayers false', (a/differences[0]).read_text());self.assertIn('nSurfaceLayers 3',(b/differences[0]).read_text())
 def test_bounded_layer_recipe_and_job(self):
  for args in [('coarse','far',4),('medium','base',4),('fine','far',5)]:
   with self.assertRaises(ValueError):validate_profile('wall-layers-v1',*args)
  validate('layer_forces','2fa09ea6-4874-4401-ad53-1269fb21426a',{})
  with self.assertRaises(ValueError):validate('layer_forces','2fa09ea6-4874-4401-ad53-1269fb21426a',{'commands':'anything'})

 def test_sensitivity_preserves_signed_changes_without_error_claim(self):
  from kcee.native_forces_run import layer_sensitivity
  rows=[{'loads':{k:[v,0,0] for k in ('pressure_force_N','viscous_force_N','total_force_N')}} for v in (4,2,3,2.5)]
  r=layer_sensitivity(rows)
  self.assertEqual(r['medium_to_fine']['without_layers']['total_force_N']['signed_change'],[-2,0,0])
  self.assertEqual(r['medium_to_fine']['with_layers']['total_force_N']['relative_change_to_fine_norm'],.2)
  self.assertEqual(r['convergence'],'not_established')
