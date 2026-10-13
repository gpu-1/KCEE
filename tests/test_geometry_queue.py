import base64,hashlib,json,os,sys,tempfile,threading,time,unittest
from pathlib import Path
from kcee.geometry_queue import QueueError,authenticate,available,atomic_write,encoded,envelope,submit
class QueueTests(unittest.TestCase):
    def test_signature_and_tampering(self):
        key=b'x'*32;message=envelope({'job_id':'a'},key)
        self.assertEqual(authenticate(message,key)['job_id'],'a')
        message['payload']['job_id']='b'
        with self.assertRaises(QueueError):authenticate(message,key)
    def test_stale_or_wrong_key_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            q=Path(tmp);key=q/'key';key.write_bytes(b'x'*32)
            atomic_write(q/'heartbeat.json',envelope({'state':'ready','created_at':time.time()-20},key.read_bytes()))
            self.assertFalse(available(q,key))
            with self.assertRaises(QueueError):submit({},q,key,timeout=.2)
            atomic_write(q/'heartbeat.json',envelope({'state':'ready','created_at':time.time()},b'y'*32))
            self.assertFalse(available(q,key))
    def exchange(self,alter=None):
        with tempfile.TemporaryDirectory() as tmp:
            q=Path(tmp);key=q/'key';key.write_bytes(b'x'*32);secret=key.read_bytes()
            atomic_write(q/'heartbeat.json',envelope({'state':'ready','created_at':time.time()},secret))
            request={'geometry_mm':{'length':60},'options':{}};stl=b'kernel fixture'
            def worker():
                while not list(q.glob('*.request.json')):time.sleep(.01)
                path=next(q.glob('*.request.json'));job=authenticate(json.loads(path.read_text()),secret)
                response={'job_id':job['job_id'],'status':'completed','request_sha256':hashlib.sha256(encoded(request)).hexdigest(),'stl_base64':base64.b64encode(stl).decode(),'stl_sha256':hashlib.sha256(stl).hexdigest(),'metadata':{'backend':'PicoGK'}}
                if alter:alter(response)
                atomic_write(q/(job['job_id']+'.response.json'),envelope(response,secret))
            thread=threading.Thread(target=worker);thread.start()
            try:return submit(request,q,key,timeout=2)
            finally:thread.join(timeout=2)
    def test_signed_exchange(self):self.assertEqual(self.exchange()[0],b'kernel fixture')
    def test_changed_bytes_rejected(self):
        with self.assertRaises(QueueError):self.exchange(lambda p:p.update(stl_base64=base64.b64encode(b'changed').decode()))
    def test_wrong_request_rejected(self):
        with self.assertRaises(QueueError):self.exchange(lambda p:p.update(request_sha256='0'*64))
    def test_timeout_cleans_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            q=Path(tmp);key=q/'key';key.write_bytes(b'x'*32)
            atomic_write(q/'heartbeat.json',envelope({'state':'ready','created_at':time.time()},key.read_bytes()))
            with self.assertRaises(QueueError):submit({},q,key,timeout=.1)
            self.assertFalse(list(q.glob('*.request.json')))
