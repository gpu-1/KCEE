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
  with self.assertRaises(ValueError):extract_pdf(pdf_bytes(tuple('Page' for _ in range(41))))
 def test_wrong_page_and_literal_content_rejected(self):
  raw=pdf_bytes();pdf=extract_pdf(raw);row={'name':'reference.pdf','source_sha256':hashlib.sha256(raw).hexdigest()};text=pdf['pages'][0]['text']
  chunk={'document_id':'id','name':row['name'],'source_sha256':row['source_sha256'],'line_start':1,'line_end':1,'page_number':1,'content':text,'chunk_sha256':hashlib.sha256(text.encode()).hexdigest()}
  k=Knowledge()
  with patch.object(k,'source',return_value=(row,raw)),patch.object(k,'reference_lines',return_value=(''.join(p['text'] for p in pdf['pages']).splitlines(keepends=True),pdf)):
   k.verify_citations([chunk])
   for change in ({'page_number':2},{'page_number':None},{'content':'false passage'},{'extractor':'fake'},{'page_text_sha256':'wrong'}):
    with self.assertRaises(IntegrityError):k.verify_citations([dict(chunk,**change)])
 def test_timeout_reported(self):
  import subprocess
  with patch('kcee.pdf_text.subprocess.run',side_effect=subprocess.TimeoutExpired('pdf',15)):
   with self.assertRaisesRegex(ValueError,'15-second'):extract_pdf(pdf_bytes())
