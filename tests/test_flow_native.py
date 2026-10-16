import unittest
from kcee.flow_native import decomposition_centres,audit
class NativeAuditTests(unittest.TestCase):
 def text(self,cell_id=0):
  return '# vtk DataFile Version 2.0\ncase\nASCII\nDATASET UNSTRUCTURED_GRID\nPOINTS 5 float\n0 0 0 1 0 0 0 1 0 0 0 1 .25 .25 .25\nCELLS 2 10\n4 0 1 2 4\n4 0 1 3 4\nCELL_TYPES 2\n10 10\nCELL_DATA 2\nFIELD FieldData 1\ncellID 1 2 int\n0 '+str(cell_id)+'\n'
 def test_native_centres_addressed_by_original_cell_id(self):self.assertEqual(decomposition_centres(self.text(),4,1),{0:[.25,.25,.25]})
 def test_invalid_or_ambiguous_cell_addressing_rejected(self):
  with self.assertRaises(ValueError):decomposition_centres(self.text(1),4,2)
  with self.assertRaises(ValueError):decomposition_centres(self.text(-1),4,1)
  with self.assertRaises(ValueError):decomposition_centres(self.text().replace('.25','nan'),4,1)
 def test_partial_audit_counts_probe_support_coverage(self):
  d=audit(self.text(),4,{'cells':1,'field':[{'x_m':.25,'y_m':.25,'z_m':.25}],'fixed_probes':[{'name':'probe','support_cell_indices':[0]}]});self.assertEqual(d['maximum_difference_m'],0);self.assertEqual(d['probe_support_coverage'][0]['native_support_cells_exported'],1)
 def test_audit_arithmetic_and_coverage_tampering_rejected(self):
  from kcee.flow_native import validate_audit
  f={'cells':1,'field':[{'x_m':.25,'y_m':.25,'z_m':.25}],'fixed_probes':[{'name':'probe','support_cell_indices':[0]}]};d=audit(self.text(),4,f);d['exported_centres_m']={'0':[.25,.25,.25]}
  for key in ('exporter_sha256','native_export_sha256','source_archive_sha256'):d[key]='a'*64
  self.assertTrue(validate_audit(d,f));d['probe_support_coverage'][0]['native_support_cells_exported']=0
  with self.assertRaises(ValueError):validate_audit(d,f)
 def test_verification_tolerates_roundoff_but_rejects_material_distance_changes(self):
  import math
  from kcee.flow_native import validate_audit
  f={'cells':1,'field':[{'x_m':.251,'y_m':.25,'z_m':.25}],'fixed_probes':[]};d=audit(self.text(),4,f);d['exported_centres_m']={'0':[.25,.25,.25]}
  for key in ('exporter_sha256','native_export_sha256','source_archive_sha256'):d[key]='a'*64
  d['rms_difference_m']=math.nextafter(d['rms_difference_m'],math.inf);self.assertTrue(validate_audit(d,f));d['maximum_difference_m']+=1e-5
  with self.assertRaises(ValueError):validate_audit(d,f)
