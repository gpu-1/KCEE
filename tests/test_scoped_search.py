import unittest
from unittest.mock import MagicMock,patch
from kcee.semantic_knowledge import retrieve
class ScopedSemanticTests(unittest.TestCase):
 def test_semantic_scope_is_applied_before_rank_limit(self):
  knowledge=MagicMock();connection=knowledge.connect.return_value.__enter__.return_value;connection.execute.return_value.fetchall.return_value=[]
  state={'available':True,'indexed_passages':10,'total_passages':10,'model_manifest_sha256':'manifest','model':'local','model_sha256':'model','dimensions':2}
  result={'vector':[1.,0.],'model_manifest_sha256':'manifest','input_sha256':'input','vector_sha256':'vector'}
  identifier='12345678-1234-1234-1234-123456789abc'
  with patch('kcee.semantic_knowledge.coverage',return_value=state),patch('kcee.semantic_knowledge.embed',return_value=result):
   rows,metadata=retrieve(knowledge,'thermal',[],document_id=identifier)
  sql,params=connection.execute.call_args.args
  self.assertIn('d.id=%s::uuid',sql);self.assertLess(sql.index('d.id=%s::uuid'),sql.index('LIMIT 12'));self.assertEqual(params[2:4],(identifier,identifier));self.assertEqual(rows,[])

class AssistantDocumentScopeTests(unittest.TestCase):
 def test_scope_and_source_identity_are_hashed_even_without_matches(self):
  import hashlib
  from kcee.knowledge import attach_documents
  from kcee.geometry_queue import encoded
  identifier='12345678-1234-1234-1234-123456789abc'
  with patch('kcee.knowledge.Knowledge') as constructor:
   knowledge=constructor.return_value
   knowledge.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value={'id':identifier}
   knowledge.source.return_value=({'name':'selected.pdf','source_sha256':'original-hash'},b'original')
   knowledge.retrieve.return_value=([],{'matches':0,'document_id':identifier})
   evidence,digest=attach_documents({'source':{'run_id':'study'}},'What is recorded?',identifier)
   knowledge.retrieve.assert_called_once_with('What is recorded?',with_metadata=True,document_id=identifier)
   self.assertEqual(evidence['document_search']['scope'],{'document_id':identifier,'name':'selected.pdf','source_sha256':'original-hash'})
   self.assertEqual(digest,hashlib.sha256(encoded(evidence)).hexdigest())
 def test_archived_or_missing_source_never_falls_back_to_other_documents(self):
  from kcee.knowledge import attach_documents
  with patch('kcee.knowledge.Knowledge') as constructor:
   knowledge=constructor.return_value;knowledge.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value=None
   with self.assertRaisesRegex(ValueError,'unavailable or archived'):attach_documents({},'Question','12345678-1234-1234-1234-123456789abc')
   knowledge.retrieve.assert_not_called()
