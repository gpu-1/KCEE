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

class PageNoteExportTests(unittest.TestCase):
 def test_changed_note_is_rejected_before_export(self):
  from unittest.mock import patch
  from kcee.page_notes import export_notes
  from kcee.provenance import IntegrityError
  identity={'document_id':'12345678-1234-1234-1234-123456789abc','page_number':2,'source_sha256':'a'*64,'page_text_sha256':'b'*64,'extractor':'recorded'}
  note={**identity,'note':'Changed','note_sha256':'0'*64}
  with patch('kcee.page_notes.Knowledge') as constructor,patch('kcee.page_notes.verified_page',return_value=identity):
   knowledge=constructor.return_value;knowledge.source.return_value=({'name':'scan.pdf'},b'original');knowledge.connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value=[note]
   with self.assertRaises(IntegrityError):export_notes(identity['document_id'],2)
