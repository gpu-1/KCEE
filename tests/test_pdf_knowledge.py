import hashlib,importlib.util,json,unittest
from unittest.mock import patch
from pdf_fixture import pdf_bytes
from kcee.pdf_text import extract_pdf,EXTRACTOR
from kcee.knowledge import Knowledge
from kcee.provenance import IntegrityError

@unittest.skipUnless(importlib.util.find_spec('pypdf'),'PDF dependency tested in API image')
class PDFTests(unittest.TestCase):
 def test_pages_and_hashes(self):
  result=extract_pdf(pdf_bytes())
  self.assertEqual(result['extractor'],EXTRACTOR);self.assertEqual(result['page_count'],2)
  self.assertIn('20 degrees C',result['pages'][0]['text'])
  self.assertIn('not a material allowable',result['pages'][1]['text'])
  for p in result['pages']:self.assertEqual(hashlib.sha256(p['text'].encode()).hexdigest(),p['text_sha256'])
 def test_blank_and_malformed_rejected(self):
  for raw in (b'%PDF-1.4\nbroken',pdf_bytes(('',)),b'not PDF'):
   with self.assertRaises(ValueError):extract_pdf(raw)
 def test_empty_page_keeps_physical_number(self):
  result=extract_pdf(pdf_bytes(('','Reference on physical page two.')))
  self.assertEqual(result['empty_pages'],[1]);self.assertEqual(result['pages'][1]['page_number'],2)
 def test_encrypted_rejected(self):
  import io
  from pypdf import PdfReader,PdfWriter
  writer=PdfWriter();writer.append(PdfReader(io.BytesIO(pdf_bytes())));writer.encrypt('private');out=io.BytesIO();writer.write(out)
  with self.assertRaises(ValueError):extract_pdf(out.getvalue())
 def test_page_limit(self):
  with self.assertRaises(ValueError):extract_pdf(pdf_bytes(tuple('Page' for _ in range(301))))
 def test_wrong_page_and_literal_content_rejected(self):
  raw=pdf_bytes();pdf=extract_pdf(raw);row={'name':'reference.pdf','source_sha256':hashlib.sha256(raw).hexdigest()};text=pdf['pages'][0]['text']
  chunk={'document_id':'id','name':row['name'],'source_sha256':row['source_sha256'],'line_start':1,'line_end':1,'page_number':1,'content':text,'chunk_sha256':hashlib.sha256(text.encode()).hexdigest()}
  k=Knowledge()
  with patch.object(k,'source',return_value=(row,raw)),patch.object(k,'reference_lines',return_value=(''.join(p['text'] for p in pdf['pages']).splitlines(keepends=True),pdf)):
   k.verify_citations([chunk])
   for change in ({'page_number':2},{'page_number':None},{'content':'false passage'},{'extractor':'fake'},{'page_text_sha256':'wrong'},{'extraction_method':'fake'}):
    with self.assertRaises(IntegrityError):k.verify_citations([dict(chunk,**change)])
 def test_timeout_reported(self):
  import subprocess
  with patch('kcee.pdf_text.subprocess.run',side_effect=subprocess.TimeoutExpired('pdf',15)):
   with self.assertRaisesRegex(ValueError,'600-second'):extract_pdf(pdf_bytes())

@unittest.skipUnless(importlib.util.find_spec('pypdf'),'PDF dependency tested in API image')
class LargePDFTests(unittest.TestCase):
 def test_sixty_pages_allowed(self):
  self.assertEqual(extract_pdf(pdf_bytes(tuple('Page reference' for _ in range(60))))['page_count'],60)
 def test_legacy_extraction_preserved(self):
  from kcee.pdf_text import LEGACY_EXTRACTOR
  from kcee.pdf_legacy import extract_direct
  raw=pdf_bytes();self.assertEqual(extract_pdf(raw,LEGACY_EXTRACTOR),extract_direct(raw))
 def test_larger_than_old_size_limit(self):
  import io
  from pypdf import PdfReader,PdfWriter
  writer=PdfWriter();writer.append(PdfReader(io.BytesIO(pdf_bytes())));writer.add_attachment('size-test.txt',b'x'*(6*1024*1024));stream=io.BytesIO();writer.write(stream)
  raw=stream.getvalue();self.assertGreater(len(raw),5*1024*1024);self.assertEqual(extract_pdf(raw)['page_count'],2)

@unittest.skipUnless(__import__('pathlib').Path('/usr/bin/tesseract').exists(),'Local OCR tested in API image')
class OCRTests(unittest.TestCase):
 def test_actual_scan_is_recognized_with_page_provenance(self):
  from pathlib import Path
  raw=(Path(__file__).parent/'fixtures/scanned-thermal-guide.pdf').read_bytes();result=extract_pdf(raw)
  self.assertEqual(result['ocr_pages'],[1,2]);self.assertEqual(result['pages'][1]['method'],'ocr');self.assertIn('0.525',result['pages'][1]['text']);self.assertIn('thermal',result['pages'][0]['text'].lower())
  self.assertEqual(len(result['ocr_runtime_sha256']),4)
  selected=extract_pdf(raw,EXTRACTOR,[2]);self.assertEqual(selected['pages'],[result['pages'][1]]);self.assertEqual(selected['page_count'],2)

@unittest.skipUnless(__import__('pathlib').Path('/usr/bin/tesseract').exists(),'Local OCR tested in API image')
class CancellableOCRTests(unittest.TestCase):
 def test_cancel_during_ocr_reports_progress_and_stops_process_group(self):
  import threading
  from pathlib import Path
  from kcee.pdf_text import ImportCancelled
  event=threading.Event();updates=[]
  def progress(value):
   updates.append(value)
   if value['stage']=='ocr':event.set()
  with self.assertRaises(ImportCancelled):extract_pdf((Path(__file__).parent/'fixtures/scanned-thermal-guide.pdf').read_bytes(),cancel_event=event,progress=progress)
  self.assertTrue(any(u['total_pages']==2 and u['stage']=='ocr' for u in updates))
 def test_completed_import_progress_matches_pages(self):
  import threading
  updates=[];result=extract_pdf(pdf_bytes(),cancel_event=threading.Event(),progress=updates.append)
  self.assertEqual(result['page_count'],2);self.assertTrue(updates);self.assertEqual(updates[-1]['total_pages'],2)
