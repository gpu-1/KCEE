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
    def test_thermal_evidence_is_bounded_and_has_no_mechanical_values(self):
        from kcee.thermal import benchmark
        record,_=self.fixture();record['manifest']['artifacts'].update({'thermal.json':'t','temperature.csv':'c'})
        result={'kind':'thermal_benchmark','validation_status':record['validation_status'],'thermal':benchmark()}
        evidence,digest=study_evidence(record,result,{}, {'items':[]})
        self.assertEqual(evidence['study_kind'],'thermal_benchmark');self.assertEqual(evidence['selected_study_result']['cells'],80)
        self.assertEqual(evidence['source']['temperature_csv_sha256'],'c');self.assertNotIn('stress_convergence',evidence['validation'])
        self.assertTrue(all('profile' not in row for row in evidence['mesh_results']));self.assertLess(len(encoded(evidence)),20000)
        self.assertEqual(digest,hashlib.sha256(encoded(evidence)).hexdigest())
    def test_bracket_thermal_snapshot_uses_fine_mesh_and_archive(self):
        record,_=self.fixture();record['manifest']['artifacts'].update({'thermal.json':'t','temperature.csv':'c','thermal-artifacts.zip':'archive'})
        result={'kind':'bracket_thermal','validation_status':record['validation_status'],'thermal':{'mesh_study':[{'target_size_mm':2.5,'hot_reaction_heat_W':1.4,'load_patch_area_mm2':123},{'target_size_mm':1.5,'hot_reaction_heat_W':1.5,'volume_mean_temperature_C':38.2}], 'checks':{'heat_balance':True},'boundary':'20 and 80 C reservoirs','conductivity_W_m_K':15,'limits':['No structural coupling'],'last_relative_heat_flow_change':.001}}
        evidence,_=study_evidence(record,result,{}, {'items':[]})
        self.assertEqual(evidence['source']['solver_archive_sha256'],'archive');self.assertEqual(evidence['selected_study_result']['hot_reaction_heat_W'],1.5)
        self.assertNotIn('load_patch_area_mm2',evidence['mesh_results'][0]);self.assertEqual(evidence['assumptions']['conductivity_W_m_K'],15)
        record['manifest']['kind']='bracket_structural'
        with self.assertRaises(ValueError):study_evidence(record,result,{}, {'items':[]})
    def test_unrecognized_model_citations_are_rejected(self):
        with self.assertRaises(ValueError):validate_answer({'answer':'Claim','source_keys':['internet']})
        with self.assertRaises(ValueError):validate_answer({'answer':'Claim','source_keys':[],'execute':'anything'})
