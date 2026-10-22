import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from kcee.bracket_flow import make_case,validate_profile
from kcee.force_history import FINE_PROFILE,HOTSPOT_PROFILE
from kcee.hotspot_refinement import REGIONS
from kcee.cfd_jobs import validate
class HotspotRefinementTests(unittest.TestCase):
 def test_new_recipe_only_adds_two_fixed_boxes_to_fine_v2(self):
  with tempfile.TemporaryDirectory() as tmp,patch('kcee.bracket_flow.prepare_surface',return_value=(b'solid bracket\nendsolid bracket\n',{})):
   a=Path(tmp)/'a';b=Path(tmp)/'b';make_case(a,b'fixture','fine','far',5,FINE_PROFILE);make_case(b,b'fixture','fine','far',5,HOTSPOT_PROFILE)
   from kcee.hotspot_refinement import refine_dictionary
   for p in a.rglob('*'):
    if not p.is_file():continue
    other=b/p.relative_to(a)
    if p.name=='snappyHexMeshDict':self.assertEqual(other.read_text(),refine_dictionary(p.read_text()))
    else:self.assertEqual(other.read_bytes(),p.read_bytes())
   text=(b/'system/snappyHexMeshDict').read_text();self.assertIn('maxBoundarySkewness 3.5',text);self.assertIn('maxGlobalCells 350000',text)
   for region in REGIONS:self.assertIn(region['name']+' {mode inside;levels ((1e15 5));}',text)
 def test_profile_and_job_inputs_are_bounded(self):
  validate_profile(HOTSPOT_PROFILE,'fine','far',5)
  for mesh,domain,bore in [('medium','far',5),('fine','outer',5),('fine','far',4)]:
   with self.assertRaises(ValueError):validate_profile(HOTSPOT_PROFILE,mesh,domain,bore)
  parent='00000000-0000-0000-0000-000000000001';validate('hotspot_refinement',parent,{})
  with self.assertRaises(ValueError):validate('hotspot_refinement',parent,{'level':8})
