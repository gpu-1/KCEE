import unittest
from kcee.library_coverage import TABLES,fingerprint_records,compare_library
class CoverageTests(unittest.TestCase):
 def test_matching_counts_alone_are_unknown(self):
  now=fingerprint_records({t:[] for t in TABLES});self.assertEqual(compare_library({'counts':now['counts']},now)['status'],'unknown')
 def test_equal_counts_changed_identity_is_detected(self):
  groups={t:[] for t in TABLES};groups['local_documents']=[{'id':'one','source_sha256':'a'}];old=fingerprint_records(groups);groups['local_documents']=[{'id':'two','source_sha256':'b'}];now=fingerprint_records(groups)
  self.assertEqual(compare_library({'counts':old['counts'],'library_snapshot':old,'bundle_present':True},now)['status'],'differs')
 def test_missing_bundle_changes_and_matching_metadata(self):
  now=fingerprint_records({t:[] for t in TABLES});saved={'counts':now['counts'],'library_snapshot':now,'bundle_present':True}
  self.assertEqual(compare_library(saved,now)['status'],'matches_metadata');saved['bundle_present']=False;self.assertEqual(compare_library(saved,now)['status'],'missing_bundle');self.assertEqual(compare_library(None,now)['status'],'no_backup');saved['counts']={};self.assertEqual(compare_library(saved,now)['status'],'differs')
