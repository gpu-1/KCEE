import unittest
from unittest.mock import patch
from kcee.export_verification import verify_records
from kcee.provenance import IntegrityError
class LocalExportVerificationTests(unittest.TestCase):
 def test_source_identity_is_checked_before_passages(self):
  identifier='12345678-1234-1234-1234-123456789abc';document={'id':identifier,'name':'reference.md','source_sha256':'a'*64};passages=[{'document_id':identifier}]
  with patch('kcee.export_verification.Knowledge') as constructor:
   knowledge=constructor.return_value;knowledge.source.return_value=({'name':'reference.md','source_sha256':'a'*64},b'original')
   self.assertEqual(verify_records({'kind':'passages','documents':[document],'passages':passages})['passages'],1);knowledge.verify_citations.assert_called_once_with(passages)
   with self.assertRaises(IntegrityError):verify_records({'kind':'passages','documents':[dict(document,source_sha256='b'*64)],'passages':passages})
 def test_empty_or_excessive_record_requests_rejected(self):
  for data in ({},{'kind':'unknown'}, {'kind':'passages','documents':[],'passages':[]},{'kind':'passages','documents':[{}]*13,'passages':[]}):
   with self.assertRaises(ValueError):verify_records(data)
