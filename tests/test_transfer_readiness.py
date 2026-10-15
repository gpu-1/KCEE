import unittest
from kcee.transfer_readiness import study_fingerprint,restore_link,transfer_readiness
from kcee.library_coverage import fingerprint_records,TABLES
class TransferReadinessTests(unittest.TestCase):
 def fixtures(self):
  library=fingerprint_records({t:[] for t in TABLES});studies=study_fingerprint({'design_runs':[{'id':'one','manifest_sha256':'a'}],'run_visibility_events':[]});backup={'record_name':'x.zip.receipt.json','bundle_name':'x.zip','bundle_sha256':'a'*64,'bundle_present':True,'counts':library['counts'],'library_snapshot':library,'study_snapshot':studies};restored={'record_name':'r.json','tested_bundle_sha256':'a'*64};return {'backup':backup,'restore':restored,'warnings':[]},library,studies
 def test_exact_archive_identity_and_legacy_unknown(self):
  saved,library,studies=self.fixtures();self.assertEqual(restore_link(saved['backup'],saved['restore'])['status'],'matches');saved['restore']['tested_bundle_sha256']='b'*64;self.assertEqual(restore_link(saved['backup'],saved['restore'])['status'],'different_backup');del saved['restore']['tested_bundle_sha256'];self.assertEqual(restore_link(saved['backup'],saved['restore'])['status'],'unknown')
 def test_data_ready_keeps_destination_and_browser_acceptance_separate(self):
  saved,library,studies=self.fixtures();r=transfer_readiness(saved,library,studies);self.assertEqual(r['status'],'source_data_ready');self.assertEqual([c['status'] for c in r['checks'][-2:]],['manual','pending'])
 def test_same_counts_changed_study_identity_is_detected(self):
  saved,library,studies=self.fixtures();changed=study_fingerprint({'design_runs':[{'id':'two','manifest_sha256':'b'}],'run_visibility_events':[]});self.assertEqual(changed['counts'],studies['counts']);r=transfer_readiness(saved,library,changed);self.assertEqual(r['status'],'needs_attention');self.assertEqual(r['checks'][2]['status'],'attention');saved['backup'].pop('study_snapshot');self.assertEqual(transfer_readiness(saved,library,studies)['checks'][2]['status'],'unknown')

 def test_legacy_receipt_can_prove_a_count_difference(self):
  saved,library,studies=self.fixtures();saved['backup'].pop('study_snapshot');saved['backup']['counts']['design_runs']=0;self.assertEqual(transfer_readiness(saved,library,studies)['checks'][2]['status'],'attention')

 def test_restore_rejects_equal_counts_with_changed_study_fingerprint(self):
  from scripts.backup_project import verify_restore_inventory
  expected={'counts':{'design_runs':1},'study_snapshot':{'scheme':'kcee.study-metadata.v1','sha256':'a'}}
  with self.assertRaisesRegex(ValueError,'study metadata'):verify_restore_inventory(expected,{'counts':{'design_runs':1},'study_snapshot':{'scheme':'kcee.study-metadata.v1','sha256':'b'}})
