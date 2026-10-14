import math,time,unittest
from unittest.mock import patch
from kcee.embeddings import float32_vector,input_text,validate_job
from kcee.semantic_knowledge import fuse,retrieve

class EmbeddingTests(unittest.TestCase):
 def test_canonical_vector(self):
  v=[1.0]+[0.0]*767
  canonical,digest=float32_vector(v)
  self.assertEqual(float32_vector(canonical)[1],digest)
  self.assertEqual(len(digest),64)
 def test_invalid_vectors(self):
  for v in ([1.0], [0.0]*768, [float('nan')]+[0.0]*767,[True]+[0.0]*767,[2.0]+[0.0]*767):
   with self.assertRaises(ValueError):float32_vector(v)
 def test_task_prefix_and_bounds(self):
  self.assertEqual(input_text('query','heat'),'search_query: heat')
  self.assertEqual(input_text('document','heat'),'search_document: heat')
  with self.assertRaises(ValueError):input_text('query','x'*801)
 def test_expired_job(self):
  with self.assertRaises(ValueError):validate_job(dict(job_id='a',created_at=time.time()-31,kind='query',text='heat'),'a')
 def test_rank_fusion_deduplicates(self):
  rows=fuse([{'chunk_id':1},{'chunk_id':2}],[{'chunk_id':2,'cosine_similarity':.8,'embedding_vector_sha256':'hash'}])
  self.assertEqual([r['chunk_id'] for r in rows],[2,1])
  self.assertEqual(rows[0]['retrieval_ranks'],{'keyword':2,'semantic':1})
 def test_offline_keyword_fallback(self):
  with patch('kcee.semantic_knowledge.coverage',return_value={'available':False}):
   rows,meta=retrieve(None,'heat',[{'chunk_id':1}])
  self.assertEqual(rows,[{'chunk_id':1}]);self.assertFalse(meta['semantic_embeddings'])
  self.assertIn('unavailable',meta['semantic_fallback'])
