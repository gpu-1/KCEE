"""Mocked integrity-error route check: never reads or writes a database."""
import importlib.util,unittest
from unittest.mock import patch
from kcee.provenance import IntegrityError

@unittest.skipUnless(importlib.util.find_spec('app'),'API route tested inside the API image')
class SearchAPITests(unittest.IsolatedAsyncioTestCase):
 async def test_integrity_failure_returns_conflict(self):
  from app import search_local_documents
  from fastapi import HTTPException
  class Request:
   headers={'origin':'http://localhost:5173','x-kcee-knowledge':'1'}
   async def stream(self):yield b'{"question":"reference"}'
  with patch('kcee.knowledge.Knowledge.retrieve',side_effect=IntegrityError('Source hash mismatch')):
   with self.assertRaises(HTTPException) as error:await search_local_documents(Request())
  self.assertEqual(error.exception.status_code,409)
