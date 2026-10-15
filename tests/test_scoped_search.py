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
