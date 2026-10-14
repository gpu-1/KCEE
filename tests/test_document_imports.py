import threading,time,unittest
from unittest.mock import patch
from kcee.document_imports import Imports
from kcee.pdf_text import ImportCancelled

class ImportTests(unittest.TestCase):
 def wait(self,manager,id):
  deadline=time.monotonic()+3
  while time.monotonic()<deadline:
   job=manager.get(id)
   if job['state'] in ('completed','cancelled','failed'):return job
   time.sleep(.01)
  self.fail('Import did not terminate')
 def test_cancel_stops_before_registration(self):
  started=threading.Event()
  def extraction(raw,**options):
   started.set();options['cancel_event'].wait(2);raise ImportCancelled()
  manager=Imports()
  with patch('kcee.document_imports.extract_pdf',side_effect=extraction),patch('kcee.document_imports.Knowledge.ingest') as ingest:
   id=manager.start('scan.pdf',b'%PDF-test')['id'];self.assertTrue(started.wait(1))
   self.assertTrue(manager.cancel(id)['cancel_accepted']);self.assertEqual(self.wait(manager,id)['state'],'cancelled');ingest.assert_not_called()
 def test_registration_cannot_be_cancelled_after_gate(self):
  saving=threading.Event();finish=threading.Event();manager=Imports()
  def ingest(name,raw,**options):options['before_save']();saving.set();finish.wait(2);return {'id':'saved'}
  with patch('kcee.document_imports.Knowledge.ingest',side_effect=ingest):
   id=manager.start('notes.txt',b'Reference')['id'];self.assertTrue(saving.wait(1));self.assertFalse(manager.cancel(id)['cancel_accepted']);finish.set();self.assertEqual(self.wait(manager,id)['state'],'completed')
 def test_single_active_import_and_failed_extraction(self):
  entered=threading.Event();finish=threading.Event();manager=Imports()
  def extraction(raw,**options):entered.set();finish.wait(2);raise ValueError('Unreadable PDF')
  with patch('kcee.document_imports.extract_pdf',side_effect=extraction),patch('kcee.document_imports.Knowledge.ingest') as ingest:
   id=manager.start('scan.pdf',b'%PDF-test')['id'];entered.wait(1)
   with self.assertRaises(RuntimeError):manager.start('second.txt',b'text')
   finish.set();self.assertEqual(self.wait(manager,id)['state'],'failed');ingest.assert_not_called()
