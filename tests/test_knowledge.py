import hashlib,unittest
from kcee.knowledge import document_parts
from kcee.study_assistant import validate_answer
class KnowledgeTests(unittest.TestCase):
 def test_original_bytes_and_line_ranges_are_preserved(self):
  raw=('Header\r\n'+('Thermal conductivity naïve reference.\r\n'*100)).encode();digest,chunks=document_parts('reference.md',raw);lines=raw.decode().splitlines(keepends=True)
  self.assertEqual(digest,hashlib.sha256(raw).hexdigest());self.assertEqual(''.join(c['content'] for c in chunks).encode(),raw)
  for chunk in chunks:
   self.assertEqual(chunk['content'],''.join(lines[chunk['line_start']-1:chunk['line_end']]))
   self.assertEqual(chunk['chunk_sha256'],hashlib.sha256(chunk['content'].encode()).hexdigest());self.assertLessEqual(len(chunk['content']),1800)
 def test_unsafe_or_unsupported_documents_rejected(self):
  for name,raw in [('../file.md',b'text'),('file.pdf',b'text'),('file.txt',b'\xff'),('file.txt',b'a\x00b'),('file.txt',b' '),('file.txt',b'a'*1801),('file.txt',b'a'*(256*1024+1))]:
   with self.assertRaises(ValueError):document_parts(name,raw)
 def test_citations_must_be_supplied_and_any_inline_markers_listed(self):
  good={'answer':'The reference states 15 W/(m K) [D1].','source_keys':['documents'],'document_citations':['D1']};self.assertEqual(validate_answer(good,['D1']),good);self.assertEqual(validate_answer(dict(good,answer='The reference states 15 W/(m K).'),['D1'])['document_citations'],['D1'])
  for change in ({'document_citations':['D99']},{'document_citations':[]},{'source_keys':[]},{'answer':'A claim [D2].'}):
   with self.assertRaises(ValueError):validate_answer(dict(good,**change),['D1'])
  with self.assertRaises(ValueError):validate_answer({'answer':'Claim','source_keys':['documents']})

class CitationIntegrityTests(unittest.TestCase):
 def test_cited_passage_is_checked_against_original_bytes(self):
  from unittest.mock import patch
  from kcee.knowledge import Knowledge
  from kcee.provenance import IntegrityError
  raw=b'Exact original reference.\r\n';digest=hashlib.sha256(raw).hexdigest();row={'name':'ref.md','source_sha256':digest}
  chunk={'document_id':'00000000-0000-4000-8000-000000000001','name':'ref.md','line_start':1,'line_end':1,'content':raw.decode(),'source_sha256':digest,'chunk_sha256':digest}
  knowledge=Knowledge()
  with patch.object(knowledge,'source',return_value=(row,raw)):
   knowledge.verify_citations([chunk])
   for change in ({'content':'Forged excerpt'},{'source_sha256':'wrong'},{'line_start':0},{'name':'another.md'},{'content':raw.decode().replace('\r\n','\n')}):
    with self.assertRaises(IntegrityError):knowledge.verify_citations([dict(chunk,**change)])

class EmptyDocumentAnswerTests(unittest.TestCase):
 def test_signed_no_match_answer_uses_normal_schema(self):
  import tempfile,uuid
  from pathlib import Path
  from kcee.geometry_queue import atomic_write,envelope,encoded
  from kcee.study_assistant import assistant_result
  job=str(uuid.uuid4());evidence={'source':{'run_id':str(uuid.uuid4())},'documents':[],'document_search':{'matches':0}}
  payload={'job_id':job,'status':'completed','evidence':evidence,'evidence_sha256':hashlib.sha256(encoded(evidence)).hexdigest(),'answer':{'answer':'No matching document information is available.','source_keys':['validation']}}
  with tempfile.TemporaryDirectory() as temporary:
   queue=Path(temporary);key=queue/'key';key.write_bytes(b'x'*32);atomic_write(queue/(job+'.response.json'),envelope(payload,key.read_bytes()))
   self.assertEqual(assistant_result(job,queue,key)['answer'],payload['answer'])
