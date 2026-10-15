"""Original PDF viewing retains source integrity and attachment downloads."""
import importlib.util,unittest,uuid
from unittest.mock import patch
from kcee.provenance import IntegrityError
@unittest.skipUnless(importlib.util.find_spec('app'),'API route tested inside the API image')
class PDFSourceTests(unittest.TestCase):
 def test_original_pdf_inline_and_download(self):
  from app import knowledge_source
  with patch('kcee.knowledge.Knowledge.source',return_value=({'name':'scan.pdf','source_sha256':'recorded'},b'%PDF-source')):
   for inline in (False,True):
    response=knowledge_source(uuid.uuid4(),inline=inline)
    self.assertEqual(response.body,b'%PDF-source');self.assertEqual(response.media_type,'application/pdf')
    self.assertTrue(response.headers['content-disposition'].startswith('inline' if inline else 'attachment'))
    self.assertEqual(response.headers['x-source-sha256'],'recorded');self.assertEqual(response.headers['x-content-type-options'],'nosniff')
 def test_changed_source_cannot_be_opened_inline(self):
  from app import knowledge_source
  from fastapi import HTTPException
  with patch('kcee.knowledge.Knowledge.source',side_effect=IntegrityError('Source hash mismatch')):
   with self.assertRaises(HTTPException) as error:knowledge_source(uuid.uuid4(),inline=True)
   self.assertEqual(error.exception.status_code,409)
 def test_text_sources_remain_downloads(self):
  from app import knowledge_source
  from fastapi import HTTPException
  with patch('kcee.knowledge.Knowledge.source',return_value=({'name':'notes.txt','source_sha256':'recorded'},b'notes')):
   with self.assertRaises(HTTPException) as error:knowledge_source(uuid.uuid4(),inline=True)
   self.assertEqual(error.exception.status_code,422)
