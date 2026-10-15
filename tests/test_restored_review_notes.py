import copy,hashlib,unittest
from datetime import datetime,timezone,timedelta
from scripts.verify_restored_data import review_note_history
from scripts.backup_project import verify_restore_inventory
from kcee.page_notes import note_digest
from kcee.provenance import IntegrityError
class RestoredReviewNoteTests(unittest.TestCase):
 def fixture(self):
  id='12345678-1234-1234-1234-123456789abc';text='Recorded 0.525 W.\n';page_hash=hashlib.sha256(text.encode()).hexdigest()
  docs={id:{'source_sha256':'a'*64,'pdf':{'extractor':'recorded','pages':[{'page_number':1,'text':text,'text_sha256':page_hash}]}}}
  row={'id':1,'document_id':id,'page_number':1,'source_sha256':'a'*64,'page_text_sha256':page_hash,'extractor':'recorded','note':'Revisar símbolo °C.','created_at':datetime(2026,10,15,tzinfo=timezone.utc)};row['note_sha256']=note_digest(row);return docs,row
 def test_verified_history_binds_notes_to_sources_and_normalizes_timezones(self):
  docs,row=self.fixture();report=review_note_history([row],docs);self.assertEqual(report['count'],1);self.assertEqual(len(report['history_sha256']),64)
  shifted=dict(row,created_at=row['created_at'].astimezone(timezone(timedelta(hours=2))))
  self.assertEqual(review_note_history([shifted],docs),report)
  self.assertEqual(review_note_history([],docs)['count'],0)
 def test_changed_text_or_identity_rejects_audit(self):
  docs,row=self.fixture()
  for change in ({'note':'Changed'},{'source_sha256':'b'*64},{'page_text_sha256':'c'*64},{'page_number':2},{'extractor':'different'},{'id':0}):
   with self.assertRaises(IntegrityError):review_note_history([dict(row,**change)],docs)
  with self.assertRaises(IntegrityError):review_note_history([row,row],docs)
 def test_restore_rejects_rehashed_note_changes_even_when_counts_match(self):
  docs,row=self.fixture();before=review_note_history([row],docs);changed=dict(row,note='Different review observation');changed['note_sha256']=note_digest(changed);after=review_note_history([changed],docs)
  self.assertNotEqual(before['history_sha256'],after['history_sha256'])
  expected={'counts':{'document_page_notes':1},'review_notes':before};verify_restore_inventory(expected,copy.deepcopy(expected))
  with self.assertRaisesRegex(ValueError,'history differs'):verify_restore_inventory(expected,{'counts':expected['counts'],'review_notes':after})
  with self.assertRaises(ValueError):verify_restore_inventory(expected,{'counts':expected['counts']})
  verify_restore_inventory({'counts':{'old_table':0}},{'counts':{'old_table':0}})
