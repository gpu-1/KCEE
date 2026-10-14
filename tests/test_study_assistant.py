import hashlib,tempfile,time,unittest,uuid
from pathlib import Path
from kcee.geometry_queue import atomic_write,envelope,encoded,QueueError
from kcee.study_assistant import study_evidence,validate_assistant_request,validate_answer,submit_assistant,assistant_result
class StudyAssistantTests(unittest.TestCase):
    def fixture(self):
        run_id=str(uuid.uuid4());record={'id':run_id,'validation_status':'pending','manifest_sha256':'m','manifest':{'run_id':run_id,'artifacts':{'result.json':'r','fea-artifacts.zip':'a'}}}
        result={'kind':'bracket_structural','validation_status':'pending','fea':{'checks':{'force_balance':True},'boundary':'Ideal clamp','load':'100 N','material':{'source':'Illustrative'},'stress_note':'Unconverged','mesh_study':[{'target_size_mm':1.5,'tip_deflection_mm':0.79068,'maximum_von_mises_MPa':217.24}]}}
        return record,result
    def test_evidence_identity_and_validation_limits(self):
        record,result=self.fixture();evidence,digest=study_evidence(record,result,{}, {'items':[]})
        self.assertEqual(digest,hashlib.sha256(encoded(evidence)).hexdigest());self.assertEqual(evidence['validation']['engineering_acceptance'],'pending');self.assertEqual(evidence['validation']['stress_convergence'],'not_established')
        self.assertEqual(evidence['selected_study_result']['loaded_patch_displacement_mm'],0.79068)
        result['validation_status']='accepted'
        with self.assertRaises(ValueError):study_evidence(record,result,{}, {'items':[]})
    def test_bounded_signed_jobs_and_response_snapshot(self):
        record,result=self.fixture();evidence,digest=study_evidence(record,result,{}, {'items':[]});job=str(uuid.uuid4());payload={'job_id':job,'created_at':time.time(),'question':'Explain the result','evidence':evidence,'evidence_sha256':digest}
        self.assertEqual(validate_assistant_request(payload,job),payload)
        for change in ({'question':'x'*801},{'created_at':time.time()-40},{'evidence_sha256':'wrong'},{'execute':'bad'}):
            with self.assertRaises(ValueError):validate_assistant_request(dict(payload,**change),job)
        with tempfile.TemporaryDirectory() as directory:
            queue=Path(directory);key=queue/'key';key.write_bytes(b'x'*32)
            with self.assertRaises(QueueError):submit_assistant('Explain',evidence,digest,queue,key)
            atomic_write(queue/'heartbeat.json',envelope({'state':'ready','created_at':time.time()},key.read_bytes()))
            job=submit_assistant('Explain',evidence,digest,queue,key)
            self.assertEqual(assistant_result(job,queue,key)['status'],'pending')
            with self.assertRaises(QueueError):submit_assistant('Another',evidence,digest,queue,key)
            response={'job_id':job,'status':'completed','evidence':evidence,'evidence_sha256':digest,'answer':{'answer':'Validation remains pending.','source_keys':['validation']}}
            path=queue/(job+'.response.json');atomic_write(path,envelope(response,key.read_bytes()));self.assertEqual(assistant_result(job,queue,key)['status'],'completed')
            response['evidence_sha256']='wrong';atomic_write(path,envelope(response,key.read_bytes()))
            with self.assertRaises(QueueError):assistant_result(job,queue,key)
    def test_unrecognized_model_citations_are_rejected(self):
        with self.assertRaises(ValueError):validate_answer({'answer':'Claim','source_keys':['internet']})
        with self.assertRaises(ValueError):validate_answer({'answer':'Claim','source_keys':[],'execute':'anything'})
