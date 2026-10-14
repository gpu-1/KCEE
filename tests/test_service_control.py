import tempfile,time,unittest,uuid
from pathlib import Path
from kcee.geometry_queue import atomic_write,envelope,QueueError
from kcee.service_control import validate_request,submit,result

class ServiceControlTests(unittest.TestCase):
    def test_request_is_bounded_and_expires(self):
        job=str(uuid.uuid4());payload={'job_id':job,'action':'start','created_at':time.time()}
        self.assertEqual(validate_request(payload,job),'start')
        for change in ({'action':'shell'},{'job_id':'wrong'},{'created_at':time.time()-40},{'command':'anything'}):
            with self.assertRaises(ValueError):validate_request(dict(payload,**change),job)
    def test_queue_requires_live_supervisor_and_signed_response(self):
        with tempfile.TemporaryDirectory() as directory:
            queue=Path(directory);key=queue/'key';key.write_bytes(b'x'*32)
            with self.assertRaises(QueueError):submit('start',queue,key)
            atomic_write(queue/'heartbeat.json',envelope({'state':'ready','created_at':time.time()},key.read_bytes()))
            job=submit('stop',queue,key)
            self.assertEqual(result(job,queue,key)['status'],'pending')
            with self.assertRaises(QueueError):submit('start',queue,key)
            atomic_write(queue/(job+'.response.json'),envelope({'job_id':job,'status':'completed'},b'y'*32))
            with self.assertRaises(QueueError):result(job,queue,key)
            atomic_write(queue/(job+'.response.json'),envelope({'job_id':'wrong','status':'completed'},key.read_bytes()))
            with self.assertRaises(QueueError):result(job,queue,key)
            atomic_write(queue/(job+'.response.json'),envelope({'job_id':job,'status':'completed'},key.read_bytes()))
            self.assertEqual(result(job,queue,key)['status'],'completed')
            with self.assertRaises(ValueError):submit('shell',queue,key)
