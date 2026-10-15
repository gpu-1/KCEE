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

class MultiDocumentSelectionTests(unittest.TestCase):
 def test_round_robin_includes_each_matching_source_before_second_passage(self):
  from kcee.knowledge import balanced_document_passages
  groups=[[{'document_id':name,'content':name+str(i),'citation_id':'D'+str(i+1)} for i in range(4)] for name in ('a','b','c')]
  result=balanced_document_passages(groups)
  self.assertEqual([p['document_id'] for p in result],['a','b','c','a']);self.assertEqual([p['citation_id'] for p in result],['D1','D2','D3','D4']);self.assertEqual(groups[1][0]['citation_id'],'D1')
  self.assertEqual([p['document_id'] for p in balanced_document_passages([groups[0],[],groups[2]])],['a','c','a','c'])
 def test_duplicate_empty_and_excessive_scopes_rejected(self):
  from kcee.knowledge import attach_documents
  id='12345678-1234-1234-1234-123456789abc'
  for ids in ([],[id,id],[id]*4):
   with self.assertRaises(ValueError):attach_documents({},'Question',document_ids=ids)

@__import__('unittest').skipUnless(__import__('importlib').util.find_spec('app'),'API image required')
class MultiDocumentAPITests(unittest.TestCase):
 def test_invalid_scope_requests_reject_before_reading_study(self):
  import uuid
  from app import ask_study,StudyQuestion
  from fastapi import HTTPException
  class Request:headers={'origin':'http://localhost:5173','x-kcee-assistant':'1'}
  id=str(uuid.uuid4())
  for fields in ({'document_ids':[],'include_documents':True},{'document_ids':[id,id],'include_documents':True},{'document_ids':[id]},{'document_id':id,'document_ids':[id],'include_documents':True}):
   with self.assertRaises(HTTPException) as error:ask_study(uuid.uuid4(),StudyQuestion(question='Question',**fields),Request())
   self.assertEqual(error.exception.status_code,422)

class RangedAssistantTests(unittest.TestCase):
 def test_range_is_forwarded_and_bound_to_evidence_hash(self):
  import hashlib
  from kcee.knowledge import attach_documents
  from kcee.geometry_queue import encoded
  identifier='12345678-1234-1234-1234-123456789abc'
  with patch('kcee.knowledge.Knowledge') as constructor:
   knowledge=constructor.return_value;knowledge.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value={'id':identifier};knowledge.source.return_value=({'name':'selected.pdf','source_sha256':'hash'},b'original');knowledge.retrieve.return_value=([],{'matches':0,'page_range':{'start':2,'end':2}})
   evidence,digest=attach_documents({},'Question',identifier,page_start=2,page_end=2);knowledge.retrieve.assert_called_once_with('Question',with_metadata=True,document_id=identifier,page_start=2,page_end=2);self.assertEqual(evidence['document_search']['scope']['page_range'],{'start':2,'end':2});self.assertEqual(digest,hashlib.sha256(encoded(evidence)).hexdigest())
 def test_ranges_without_single_source_fail_before_retrieval(self):
  from kcee.knowledge import attach_documents
  for args in ({'page_start':2,'page_end':2},{'document_ids':['12345678-1234-1234-1234-123456789abc'],'page_start':2,'page_end':2}):
   with self.assertRaises(ValueError):attach_documents({},'Question',**args)
