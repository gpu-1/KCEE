import base64,hashlib,io,tempfile,time,unittest,uuid,wave
from pathlib import Path
from kcee.geometry_queue import atomic_write,envelope,QueueError
from kcee.voice import validate_voice_request,submit_voice,voice_result
class VoiceTests(unittest.TestCase):
    def test_request_bounds_expiry_and_identity(self):
        job=str(uuid.uuid4());payload={'job_id':job,'run_id':str(uuid.uuid4()),'summary_sha256':'a'*64,'created_at':time.time(),'text':'Unvalidated bracket summary.'}
        self.assertEqual(validate_voice_request(payload,job),payload)
        for change in ({'text':'x'*601},{'text':''},{'created_at':time.time()-40},{'run_id':'../bad'},{'summary_sha256':'wrong'},{'job_id':'other'},{'executable':'bad'}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):validate_voice_request(dict(payload,**change),job)
    def test_signed_audio_hash_and_job_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            queue=Path(directory);key=queue/'key';key.write_bytes(b'x'*32)
            with self.assertRaises(QueueError):submit_voice(str(uuid.uuid4()),'a'*64,'summary',queue,key)
            atomic_write(queue/'heartbeat.json',envelope({'state':'ready','created_at':time.time()},key.read_bytes()))
            job=submit_voice(str(uuid.uuid4()),'a'*64,'summary',queue,key);self.assertEqual(voice_result(job,queue,key)[0]['status'],'pending')
            buffer=io.BytesIO()
            with wave.open(buffer,'wb') as wav:wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000);wav.writeframes(b'\x01\x00'*100)
            raw=buffer.getvalue();payload={'job_id':job,'status':'completed','audio_base64':base64.b64encode(raw).decode(),'audio_sha256':hashlib.sha256(raw).hexdigest()}
            path=queue/(job+'.response.json');atomic_write(path,envelope(payload,key.read_bytes()));metadata,audio=voice_result(job,queue,key);self.assertEqual(audio,raw);self.assertNotIn('audio_base64',metadata)
            payload['audio_sha256']='0'*64;atomic_write(path,envelope(payload,key.read_bytes()))
            with self.assertRaises(QueueError):voice_result(job,queue,key)
            payload['job_id']='wrong';atomic_write(path,envelope(payload,key.read_bytes()))
            with self.assertRaises(QueueError):voice_result(job,queue,key)
