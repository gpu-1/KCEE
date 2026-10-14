"""Bounded authenticated native voice queue; no remote TTS or runtime downloads."""
import base64,hashlib,time,uuid
from pathlib import Path
from kcee.geometry_queue import available,atomic_write,envelope,key_bytes,read_signed,QueueError

def validate_voice_request(payload,job_id):
    if set(payload)!={'job_id','created_at','run_id','summary_sha256','text'} or payload['job_id']!=job_id:raise ValueError('Invalid voice job identity')
    if str(uuid.UUID(payload['run_id']))!=payload['run_id'] or not -2<=time.time()-payload['created_at']<30:raise ValueError('Invalid or expired voice source')
    if not isinstance(payload['text'],str) or not 1<=len(payload['text'])<=600:raise ValueError('Voice summary exceeds limit')
    if len(payload['summary_sha256'])!=64 or any(c not in '0123456789abcdef' for c in payload['summary_sha256']):raise ValueError('Invalid summary hash')
    return payload

def submit_voice(run_id,summary_sha256,text,queue,key):
    queue=Path(queue)
    if not available(queue,key):raise QueueError('Local Kokoro worker unavailable')
    if len(list(queue.glob('*.request.json')))+len(list(queue.glob('*.processing.json')))>=8:raise QueueError('Voice queue is full')
    job_id=str(uuid.uuid4());payload={'job_id':job_id,'created_at':time.time(),'run_id':run_id,'summary_sha256':summary_sha256,'text':text};validate_voice_request(payload,job_id)
    atomic_write(queue/(job_id+'.request.json'),envelope(payload,key_bytes(key)));return job_id

def voice_result(job_id,queue,key):
    job_id=str(uuid.UUID(job_id));queue=Path(queue);path=queue/(job_id+'.response.json')
    if not path.exists():
        if (queue/(job_id+'.request.json')).exists() or (queue/(job_id+'.processing.json')).exists():return {'job_id':job_id,'status':'pending'},None
        raise FileNotFoundError('Voice job not found or expired')
    payload=read_signed(path,key_bytes(key))
    if payload['job_id']!=job_id or payload['status'] not in ('completed','failed'):raise QueueError('Voice response identity mismatch')
    if payload['status']=='failed':return payload,None
    raw=base64.b64decode(payload['audio_base64'],validate=True)
    if not 44<=len(raw)<=6*1024*1024 or hashlib.sha256(raw).hexdigest()!=payload['audio_sha256'] or raw[:4]!=b'RIFF' or raw[8:12]!=b'WAVE':raise QueueError('Voice audio integrity mismatch')
    return {key:value for key,value in payload.items() if key!='audio_base64'},raw
