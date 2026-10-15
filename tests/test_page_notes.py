import unittest
from kcee.page_notes import note_digest,save_note
class PageNoteTests(unittest.TestCase):
 def test_digest_binds_source_page_extractor_and_literal_note(self):
  row={'document_id':'12345678-1234-1234-1234-123456789abc','page_number':2,'source_sha256':'a'*64,'page_text_sha256':'b'*64,'extractor':'recorded','note':'Check 0.525 W.'}
  digest=note_digest(row);self.assertEqual(len(digest),64)
  for key,value in [('page_number',1),('source_sha256','c'*64),('page_text_sha256','d'*64),('extractor','other'),('note','Check 0.525 kW.')]:self.assertNotEqual(note_digest(dict(row,**{key:value})),digest)
 def test_invalid_notes_rejected_before_database_access(self):
  for note in ('',' ',None,'x'*2001,'invalid\x00'):
   with self.assertRaises(ValueError):save_note('id',1,{'source_sha256':'a'*64,'page_text_sha256':'b'*64,'note':note})
