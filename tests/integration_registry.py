"""Run inside the API image on an isolated Compose test project."""
import hashlib, json, os, tempfile, unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import psycopg
from kcee.demo import run
from kcee.registry import Registry
from kcee.provenance import IntegrityError

BASE='http://api:8000'
def request(path,method='GET'):
    req=Request(BASE+path,data=b'{}' if method=='POST' else None,method=method,headers={'Content-Type':'application/json'})
    with urlopen(req,timeout=15) as response: return response.status,json.load(response)

class RegistryIntegration(unittest.TestCase):
    def test_native_thermal_rejects_wrong_study_kind(self):
        run_id=request('/runs/bracket','POST')[1]['run_id']
        for path,method in [('/runs/'+run_id+'/thermal','POST'),('/runs/'+run_id+'/temperature-surface','GET')]:
            with self.assertRaises(HTTPError) as error:request(path,method)
            self.assertEqual(error.exception.code,422)

    @unittest.skipUnless(os.environ.get('KCEE_TEST_FEA'),'Engineering workers required')
    def test_thermal_benchmark_registry_and_tamper(self):
        self.assertTrue(request('/capabilities')[1]['thermal']['steady_1d'])
        status,data=request('/runs/thermal-benchmark','POST');self.assertEqual(status,201)
        run_id=data['run_id'];record=request('/runs/'+run_id)[1]
        self.assertEqual(record['manifest']['kind'],'thermal_benchmark')
        req=Request(BASE+'/runs/'+run_id+'/assistant',data=json.dumps({'question':'Explain heat balance'}).encode(),headers={'Content-Type':'application/json','Origin':'http://localhost:5173','X-KCEE-Assistant':'1'},method='POST')
        with self.assertRaises(HTTPError) as error:urlopen(req,timeout=15)
        self.assertEqual(error.exception.code,503) # Correct thermal scope reaches unavailable AI gateway.
        self.assertEqual(request('/runs/'+run_id+'/verify')[1]['integrity'],'verified')
        result=json.loads((Path('/data/runs')/run_id/'result.json').read_text())
        self.assertTrue(all(result['thermal']['checks'].values()))
        self.assertLess(result['thermal']['mesh_study'][-1]['maximum_temperature_error_C'],.003)
        with urlopen(BASE+'/artifacts/'+run_id+'/temperature.csv') as response:raw=response.read()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),record['manifest']['artifacts']['temperature.csv'])
        path=Path('/data/runs')/run_id/'temperature.csv';path.write_bytes(raw+b'tamper')
        with self.assertRaises(HTTPError) as error:request('/runs/'+run_id+'/verify')
        self.assertEqual(error.exception.code,409)

    def test_service_control_requires_local_origin_confirmation_and_supervisor(self):
        self.assertFalse(request('/services/control')[1]['available'])
        cases=[({}, {'action':'start'},403),({'Origin':'https://example.com','X-KCEE-Control':'1'},{'action':'start'},403),({'Origin':'http://localhost:5173','X-KCEE-Control':'1'},{'action':'stop'},422),({'Origin':'http://localhost:5173','X-KCEE-Control':'1'},{'action':'start'},503),({'Origin':'http://localhost:5173','X-KCEE-Control':'1'},{'action':'voice_stop'},422),({'Origin':'http://localhost:5173','X-KCEE-Control':'1'},{'action':'voice_start'},503),({'Origin':'http://localhost:5173','X-KCEE-Control':'1'},{'action':'ai_start'},503),({'Origin':'http://localhost:5173','X-KCEE-Control':'1'},{'action':'ai_stop'},422)]
        for headers,body,status in cases:
            req=Request(BASE+'/services/control',data=json.dumps(body).encode(),method='POST',headers={'Content-Type':'application/json',**headers})
            with self.assertRaises(HTTPError) as error:urlopen(req,timeout=15)
            self.assertEqual(error.exception.code,status)

    def test_local_assistant_scope_and_source_integrity(self):
        self.assertFalse(request('/assistant/status')[1]['available'])
        run_id=request('/runs/bracket','POST')[1]['run_id'];headers={'Origin':'http://localhost:5173','X-KCEE-Assistant':'1','Content-Type':'application/json'}
        def ask(identifier,question='Explain',request_headers=headers):
            return urlopen(Request(BASE+'/runs/'+identifier+'/assistant',data=json.dumps({'question':question}).encode(),method='POST',headers={'Content-Type':'application/json',**request_headers}),timeout=15)
        for question,request_headers,status in [('Explain',{},403),('Explain',{**headers,'Origin':'https://example.com'},403),('',headers,422),('x'*801,headers,422),('Explain',headers,422)]:
            with self.assertRaises(HTTPError) as error:ask(run_id,question,request_headers)
            self.assertEqual(error.exception.code,status)
        with self.assertRaises(HTTPError) as error:ask('00000000-0000-0000-0000-000000000000')
        self.assertEqual(error.exception.code,404)
        path=Path('/data/runs')/run_id/'report.md';original=path.read_bytes()
        try:
            path.write_text('changed')
            with self.assertRaises(HTTPError) as error:ask(run_id)
            self.assertEqual(error.exception.code,409)
        finally:path.write_bytes(original)
        with self.assertRaises(HTTPError) as error:request('/assistant/jobs/00000000-0000-0000-0000-000000000000')
        self.assertEqual(error.exception.code,404)

    def test_voice_worker_unavailable_and_source_integrity(self):
        self.assertFalse(request('/voice/status')[1]['available'])
        run_id=request('/runs/bracket','POST')[1]['run_id']
        def prepare(identifier,headers):
            req=Request(BASE+'/runs/'+identifier+'/voice',data=b'',method='POST',headers=headers)
            return urlopen(req,timeout=15)
        with self.assertRaises(HTTPError) as error:prepare(run_id,{})
        self.assertEqual(error.exception.code,403)
        headers={'Origin':'http://localhost:5173','X-KCEE-Voice':'1'}
        with self.assertRaises(HTTPError) as error:prepare(run_id,headers)
        self.assertEqual(error.exception.code,503)
        with self.assertRaises(HTTPError) as error:prepare('00000000-0000-0000-0000-000000000000',headers)
        self.assertEqual(error.exception.code,404)
        path=Path('/data/runs')/run_id/'voice-summary.json';original=path.read_bytes()
        try:
            path.write_text('{}')
            with self.assertRaises(HTTPError) as error:prepare(run_id,headers)
            self.assertEqual(error.exception.code,409)
        finally:path.write_bytes(original)
        with self.assertRaises(HTTPError) as error:request('/voice/jobs/00000000-0000-0000-0000-000000000000')
        self.assertEqual(error.exception.code,404)

    def test_diagnostic_scope_and_integrity(self):
        run_id=request('/runs/bracket','POST')[1]['run_id']
        for endpoint in ('geometry-measurements','stress-diagnostics','displacement-surface','refinement-explorations','refinement-explorations/global-1.3/archive'):
            with self.assertRaises(HTTPError) as error:request('/runs/'+run_id+'/'+endpoint)
            self.assertEqual(error.exception.code,422)
            with self.assertRaises(HTTPError) as error:request('/runs/00000000-0000-0000-0000-000000000000/'+endpoint)
            self.assertEqual(error.exception.code,404)
        path=Path('/data/runs')/run_id/'report.md';original=path.read_bytes()
        try:
            path.write_text('changed')
            for endpoint in ('geometry-measurements','stress-diagnostics','displacement-surface','refinement-explorations','refinement-explorations/global-1.3/archive'):
                with self.assertRaises(HTTPError) as error:request('/runs/'+run_id+'/'+endpoint)
                self.assertEqual(error.exception.code,409)
        finally:path.write_bytes(original)

    def test_retained_failure_listing_is_separate(self):
        import uuid
        run_id=str(uuid.uuid4());directory=Path('/data/runs')/run_id;directory.mkdir()
        (directory/'failure.json').write_text(json.dumps({'run_id':run_id,'status':'failed','stage':'geometry'}))
        failures=request('/failures?limit=100')[1]['items']
        self.assertTrue(any(item['run_id']==run_id for item in failures))
        self.assertFalse(any(item['id']==run_id for item in request('/runs?limit=100')[1]['items']))
        with self.assertRaises(HTTPError) as error:request('/failures?limit=0')
        self.assertEqual(error.exception.code,422)


    def test_visibility_history_append_only(self):
        for sql in ('UPDATE run_visibility_events SET hidden=hidden','DELETE FROM run_visibility_events','TRUNCATE run_visibility_events'):
            with Registry().connect() as conn:
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):conn.execute(sql)
            with psycopg.connect(user='kcee',password=os.environ['KCEE_TEST_ADMIN_PASSWORD']) as conn:
                with self.assertRaises(psycopg.errors.RaiseException):conn.execute(sql)

    def test_visibility_confirmation_and_restore(self):
        run_id=request('/runs/bracket','POST')[1]['run_id']
        before=request('/runs/'+run_id)[1]['manifest_sha256']
        def change(hidden,confirm):
            req=Request(BASE+'/runs/'+run_id+'/visibility',data=json.dumps({'confirm_run_id':confirm,'hidden':hidden}).encode(),headers={'Content-Type':'application/json'},method='POST')
            with urlopen(req) as response:return json.load(response)
        with self.assertRaises(HTTPError) as error:change(True,'00000000-0000-0000-0000-000000000000')
        self.assertEqual(error.exception.code,422)
        self.assertTrue(change(True,run_id)['hidden'])
        self.assertFalse(any(x['id']==run_id for x in request('/runs?limit=100')[1]['items']))
        self.assertTrue(any(x['id']==run_id for x in request('/runs?hidden=true&limit=100')[1]['items']))
        self.assertEqual(request('/runs/'+run_id+'/verify')[1]['integrity'],'verified')
        self.assertFalse(change(False,run_id)['hidden'])
        self.assertTrue(any(x['id']==run_id for x in request('/runs?limit=100')[1]['items']))
        self.assertEqual(request('/runs/'+run_id)[1]['manifest_sha256'],before)

    def test_api_lifecycle_and_tamper(self):
        self.assertEqual(request('/ready')[0],200)
        status,data=request('/runs/bracket','POST');self.assertEqual(status,201)
        run_id=data['run_id'];record=request('/runs/'+run_id)[1]
        self.assertEqual(record['validation_status'],'unvalidated_analytical_screening')
        self.assertTrue(any(x['id']==run_id for x in request('/runs?limit=100')[1]['items']))
        self.assertEqual(request('/runs/'+run_id+'/verify')[1]['integrity'],'verified')
        directory=Path('/data/runs')/run_id
        raw=(directory/'manifest.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),record['manifest_sha256'])
        self.assertEqual(Registry().register(directory),run_id) # idempotent recovery
        report=directory/'report.md';original=report.read_bytes()
        try:
            report.write_text('tampered')
            with self.assertRaises(HTTPError) as context: request('/runs/'+run_id+'/verify')
            self.assertEqual(context.exception.code,409)
        finally: report.write_bytes(original)
        self.assertEqual(request('/runs/'+run_id+'/verify')[0],200)
        for sql in ('UPDATE design_runs SET validation_status=validation_status','DELETE FROM design_runs','TRUNCATE design_runs'):
            with Registry().connect() as conn:
                with self.assertRaises(psycopg.errors.InsufficientPrivilege): conn.execute(sql)
        with self.assertRaises(HTTPError) as context: request('/runs/not-a-uuid')
        self.assertEqual(context.exception.code,422)
    def test_registration_failure_and_recovery(self):
        admin=lambda: psycopg.connect(user='kcee',password=os.environ['KCEE_TEST_ADMIN_PASSWORD'])
        with admin() as conn: conn.execute('REVOKE INSERT ON design_runs FROM kcee_app')
        try:
            with self.assertRaises(HTTPError) as context: request('/runs/bracket','POST')
            self.assertEqual(context.exception.code,503)
            detail=json.load(context.exception)['detail'];run_id=detail['run_id']
            self.assertIsNone(Registry().get(run_id))
            self.assertTrue((Path('/data/runs')/run_id/'manifest.json').is_file())
        finally:
            with admin() as conn: conn.execute('GRANT INSERT ON design_runs TO kcee_app')
        directory=Path('/data/runs')/run_id
        self.assertEqual(Registry().register(directory),run_id)
        self.assertEqual(Registry().verify('/data/runs',run_id)['integrity'],'verified')
        path=directory/'manifest.json';raw=path.read_bytes()
        try:
            changed=json.loads(raw);changed['software_commit']='changed'
            path.write_text(json.dumps(changed))
            with self.assertRaises(IntegrityError): Registry().register(directory)
        finally: path.write_bytes(raw)
        self.assertEqual(Registry().verify('/data/runs',run_id)['integrity'],'verified')
    @unittest.skipUnless(os.environ.get('KCEE_TEST_VIEWER_URL'), 'Viewer profile not requested')
    def test_viewer_proxy(self):
        base=os.environ['KCEE_TEST_VIEWER_URL']
        with urlopen(base,timeout=15) as response:
            self.assertIn('Design workspace',response.read().decode())
        with urlopen(base+'/api/ready',timeout=15) as response:
            self.assertEqual(json.load(response)['status'],'ready')
        req=Request(base+'/api/runs/bracket',data=b'',method='POST')
        with urlopen(req,timeout=15) as response: data=json.load(response)
        with urlopen(base+'/api/runs/'+data['run_id']+'/verify',timeout=15) as response:
            self.assertEqual(json.load(response)['integrity'],'verified')
        with urlopen(base+'/api/artifacts/'+data['run_id']+'/bracket.stl',timeout=15) as response:
            self.assertTrue(response.read().startswith(b'solid bracket'))
    def test_native_unavailable_and_invalid_backend(self):
        self.assertFalse(request('/capabilities')[1]['geometry']['picogk'])
        for backend,expected in [('picogk',503),('unknown',422)]:
            req=Request(BASE+'/runs/bracket',data=json.dumps({'geometry_backend':backend}).encode(),method='POST',headers={'Content-Type':'application/json'})
            with self.assertRaises(HTTPError) as context: urlopen(req,timeout=15)
            self.assertEqual(context.exception.code,expected)
    @unittest.skipUnless(os.environ.get('KCEE_TEST_FEA'),'Structural profile not requested')
    def test_structural_benchmark_provenance(self):
        self.assertTrue(request('/capabilities')[1]['structural']['calculix'])
        status,data=request('/runs/structural-benchmark','POST');self.assertEqual(status,201)
        run_id=data['run_id'];record=request('/runs/'+run_id)[1]
        self.assertEqual(record['manifest']['kind'],'structural_benchmark')
        self.assertEqual(record['validation_status'],'benchmark_verified_only')
        self.assertEqual(request('/runs/'+run_id+'/verify')[1]['integrity'],'verified')
        directory=Path('/data/runs')/run_id
        result=json.loads((directory/'result.json').read_text())
        self.assertTrue(all(result['fea']['checks'].values()))
        self.assertLess(result['fea']['relative_displacement_error'],.05)
        import zipfile
        with zipfile.ZipFile(directory/'fea-artifacts.zip') as archive:self.assertIn('mesh-24/beam.frd',archive.namelist())
        with self.assertRaises(HTTPError) as context:request('/runs/'+run_id+'/structural','POST')
        self.assertEqual(context.exception.code,422)
    def test_owner_append_only_trigger(self):
        for sql in ('UPDATE design_runs SET validation_status=validation_status','DELETE FROM design_runs','TRUNCATE design_runs'):
            with psycopg.connect(user='kcee',password=os.environ['KCEE_TEST_ADMIN_PASSWORD']) as conn:
                with self.assertRaises(psycopg.errors.RaiseException): conn.execute(sql+' CASCADE' if sql=='TRUNCATE design_runs' else sql)
    def test_database_unavailable_is_not_success(self):
        # Use the API ASGI app in-process with an unreachable connection.
        from fastapi import HTTPException
        from app import bracket
        old=os.environ.get('PGPORT');os.environ['PGPORT']='1'
        before=set(Path('/data/runs').iterdir())
        try:
            with self.assertRaises(HTTPException) as context: bracket()
            self.assertEqual(context.exception.status_code,503)
            self.assertEqual(before,set(Path('/data/runs').iterdir()))
        finally:
            if old is None: os.environ.pop('PGPORT',None)
            else: os.environ['PGPORT']=old

if __name__=='__main__': unittest.main(verbosity=2)
