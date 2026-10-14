"""Native Kokoro summary worker with signed local file transport."""
import base64,fcntl,hashlib,json,os,signal,subprocess,sys,tempfile,threading,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.geometry_queue import atomic_write,envelope,key_bytes,read_signed
from kcee.voice import validate_voice_request,DEFAULT_VOICE,DEFAULT_SPEED,DEFAULT_LANGUAGE
root=Path(__file__).resolve().parents[1];local=root/'.local/voice';queue=local/'queue';key=key_bytes(local/'key');models=root/'models/kokoro'
manifest=json.loads((models/'runtime-manifest.json').read_text())
if set(manifest['files'])!={'kokoro-v1.0.int8.onnx','voices-v1.0.bin'}:raise ValueError('Incomplete Kokoro model manifest')
for name,metadata in manifest['files'].items():
    if name not in ('kokoro-v1.0.int8.onnx','voices-v1.0.bin') or hashlib.sha256((models/name).read_bytes()).hexdigest()!=metadata['sha256']:raise ValueError('Kokoro model integrity mismatch')
lock=(local/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
stop=threading.Event();signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
def heartbeat():
    while not stop.is_set():
        atomic_write(queue/'heartbeat.json',envelope({'state':'ready','pid':os.getpid(),'created_at':time.time()},key));stop.wait(2)
thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
try:
    while not stop.is_set():
        for path in sorted(queue.glob('*.request.json')):
            try:
                job_id=str(uuid.UUID(path.name.removesuffix('.request.json')));request=validate_voice_request(read_signed(path,key,8192),job_id)
                claimed=queue/(job_id+'.processing.json');path.rename(claimed)
                if (queue/(job_id+'.response.json')).exists():claimed.unlink();continue
            except (OSError,ValueError,KeyError,TypeError,RuntimeError):path.unlink(missing_ok=True);continue
            try:
                with tempfile.TemporaryDirectory(prefix='kcee-voice-') as tmp:
                    tmp=Path(tmp);(tmp/'request.json').write_text(json.dumps(request))
                    with (local/'synthesis.log').open('ab') as log:
                        subprocess.run([str(root/'.local/kokoro/venv/bin/python'),str(root/'host/macos/kokoro/synthesize.py'),'--request',str(tmp/'request.json'),'--models',str(models),'--output',str(tmp/'audio.wav')],cwd=root,stdout=log,stderr=log,check=True,timeout=120,env={**os.environ,'OMP_NUM_THREADS':'1'})
                    audio=(tmp/'audio.wav').read_bytes()
                response={'job_id':job_id,'status':'completed','run_id':request['run_id'],'summary_sha256':request['summary_sha256'],'audio_sha256':hashlib.sha256(audio).hexdigest(),'model_manifest_sha256':hashlib.sha256((models/'runtime-manifest.json').read_bytes()).hexdigest(),'voice':DEFAULT_VOICE,'speed':DEFAULT_SPEED,'language':DEFAULT_LANGUAGE,'sample_rate_Hz':24000,'audio_base64':base64.b64encode(audio).decode()}
            except Exception:response={'job_id':job_id,'status':'failed','message':'Local Kokoro synthesis failed; inspect .local/voice/synthesis.log'}
            atomic_write(queue/(job_id+'.response.json'),envelope(response,key));claimed.unlink(missing_ok=True)
        for path in queue.glob('*.response.json'):
            if time.time()-path.stat().st_mtime>3600:path.unlink(missing_ok=True)
        stop.wait(.2)
finally:
    stop.set();thread.join(timeout=3);atomic_write(queue/'heartbeat.json',envelope({'state':'stopped','pid':os.getpid(),'created_at':time.time()},key))
