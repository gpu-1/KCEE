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
    def test_owner_append_only_trigger(self):
        for sql in ('UPDATE design_runs SET validation_status=validation_status','DELETE FROM design_runs','TRUNCATE design_runs'):
            with psycopg.connect(user='kcee',password=os.environ['KCEE_TEST_ADMIN_PASSWORD']) as conn:
                with self.assertRaises(psycopg.errors.RaiseException): conn.execute(sql)
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
