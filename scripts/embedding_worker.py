import fcntl,hashlib,json,os,signal,sys,threading,time,urllib.request,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.geometry_queue import atomic_write,envelope,key_bytes,read_signed
from kcee.embeddings import validate_job,input_text,float32_vector,DIMENSIONS,MODEL_SHA
root=Path(__file__).resolve().parents[1];local=root/'.local/embeddings';queue=local/'queue';runtime=root/'.local/embedding-runtime';key=key_bytes(local/'key');server_key=(runtime/'server.key').read_text().strip();fingerprint=hashlib.sha256((runtime/'model-manifest.json').read_bytes()).hexdigest()
lock=(local/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);stop=threading.Event();signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
def request(path,body=None,timeout=3):
    req=urllib.request.Request('http://127.0.0.1:8085'+path,data=json.dumps(body).encode() if body else None,headers={'Authorization':'Bearer '+server_key,'Content-Type':'application/json'})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=timeout) as response:return json.load(response)
def heartbeat():
    while not stop.is_set():
        try:ready=any(model.get('id')=='kcee-nomic-v1.5-f16' for model in request('/v1/models').get('data',[]))
        except Exception:ready=False
        atomic_write(queue/'heartbeat.json',envelope({'state':'ready' if ready else 'unavailable','pid':os.getpid(),'created_at':time.time(),'model_sha256':MODEL_SHA,'model_manifest_sha256':fingerprint,'dimensions':DIMENSIONS},key));stop.wait(2)
# A new lock owner can retire jobs interrupted by a crashed prior gateway.
for path in queue.glob('*.processing.json'):
    job=str(uuid.UUID(path.name.removesuffix('.processing.json')));atomic_write(queue/(job+'.response.json'),envelope({'job_id':job,'status':'failed'},key));path.unlink()
thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
try:
    while not stop.is_set():
        for path in sorted(queue.glob('*.request.json')):
            try:
                job=str(uuid.UUID(path.name.removesuffix('.request.json')));payload=validate_job(read_signed(path,key,16384),job);claimed=queue/(job+'.processing.json');path.rename(claimed)
            except (ValueError,OSError,KeyError,TypeError):path.unlink(missing_ok=True);continue
            try:
                text=input_text(payload['kind'],payload['text']);data=request('/v1/embeddings',{'model':'kcee-nomic-v1.5-f16','input':text,'encoding_format':'float'},20)
                vector,digest=float32_vector(data['data'][0]['embedding'])
                if data.get('usage',{}).get('prompt_tokens',0)>2048:raise ValueError('Embedding input exceeded context; no truncation accepted')
                result={'job_id':job,'status':'completed','input_sha256':hashlib.sha256(text.encode()).hexdigest(),'vector':vector,'vector_sha256':digest,'model_sha256':MODEL_SHA,'model_manifest_sha256':fingerprint}
            except Exception as error:
                with (local/'errors.log').open('a') as stream:stream.write(type(error).__name__+': '+str(error)+'\n')
                result={'job_id':job,'status':'failed'}
            atomic_write(queue/(job+'.response.json'),envelope(result,key));claimed.unlink(missing_ok=True)
        for path in queue.glob('*.response.json'):
            if time.time()-path.stat().st_mtime>600:path.unlink(missing_ok=True)
        stop.wait(.05)
finally:
    stop.set();thread.join(timeout=5);atomic_write(queue/'heartbeat.json',envelope({'state':'stopped','pid':os.getpid(),'created_at':time.time()},key))
