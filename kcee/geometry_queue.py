"""Authenticated local queue for container-to-native geometry jobs."""
import base64,hashlib,hmac,json,os,time,uuid
from pathlib import Path

class QueueError(RuntimeError):pass

def key_bytes(path):
    key=Path(path).read_bytes()
    if len(key)!=32:raise QueueError('Invalid geometry signing key')
    return key

def encoded(payload):return json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def envelope(payload,key):return {'payload':payload,'signature':hmac.new(key,encoded(payload),hashlib.sha256).hexdigest()}
def authenticate(document,key):
    payload=document['payload'];signature=document['signature']
    if not isinstance(signature,str) or not hmac.compare_digest(signature,hmac.new(key,encoded(payload),hashlib.sha256).hexdigest()):raise QueueError('Geometry message signature mismatch')
    return payload

def atomic_write(path,data):
    path=Path(path);temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temp.open('x') as f:json.dump(data,f,allow_nan=False)
        os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)

def read_signed(path,key,max_bytes=16*1024*1024):
    path=Path(path)
    if path.is_symlink() or path.stat().st_size>max_bytes:raise QueueError('Unsafe geometry queue message')
    return authenticate(json.loads(path.read_text()),key)

def available(queue,key_path):
    try:
        payload=read_signed(Path(queue)/'heartbeat.json',key_bytes(key_path),4096)
        return payload['state']=='ready' and -2<=time.time()-payload['created_at']<10
    except (OSError,ValueError,KeyError,TypeError,QueueError):return False

def submit(request,queue,key_path,timeout=135):
    queue=Path(queue)
    if not available(queue,key_path):raise QueueError('Native geometry worker unavailable. Start it on this Mac.')
    key=key_bytes(key_path)
    if len(list(queue.glob('*.request.json')))+len(list(queue.glob('*.processing.json')))>=8:raise QueueError('Native geometry queue is full')
    job_id=str(uuid.uuid4());request_path=queue/(job_id+'.request.json');response_path=queue/(job_id+'.response.json')
    payload={'schema_version':1,'job_id':job_id,'created_at':time.time(),'request':request}
    atomic_write(request_path,envelope(payload,key));deadline=time.monotonic()+timeout
    try:
        while time.monotonic()<deadline:
            if response_path.exists():
                result=read_signed(response_path,key)
                if result['job_id']!=job_id:raise QueueError('Geometry response identity mismatch')
                if result.get('request_sha256')!=hashlib.sha256(encoded(request)).hexdigest() and result['status']=='completed':raise QueueError('Geometry response request mismatch')
                if result['status']!='completed':raise QueueError(result.get('error','Native generation failed'))
                stl=base64.b64decode(result['stl_base64'],validate=True)
                if hashlib.sha256(stl).hexdigest()!=result['stl_sha256']:raise QueueError('Geometry response hash mismatch')
                return stl,result['metadata']
            time.sleep(.1)
        raise QueueError('Native geometry job timed out; no fallback was generated')
    except (OSError,ValueError,KeyError,TypeError) as exc:raise QueueError('Invalid native geometry response') from exc
    finally:
        request_path.unlink(missing_ok=True);response_path.unlink(missing_ok=True)
