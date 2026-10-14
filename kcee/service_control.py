"""Signed, bounded requests for a project-local engineering-service supervisor."""
import time,uuid
from pathlib import Path
from kcee.geometry_queue import available,atomic_write,envelope,key_bytes,read_signed,QueueError


def validate_request(payload,job_id):
    if set(payload)!={'job_id','action','created_at'} or payload['job_id']!=job_id or payload['action'] not in ('start','stop','voice_start','voice_stop'):
        raise ValueError('Unsupported service control request')
    if not -2<=time.time()-payload['created_at']<30:raise ValueError('Expired service control request')
    return payload['action']


def submit(action,queue,key):
    if action not in ('start','stop','voice_start','voice_stop'):raise ValueError('Unsupported service action')
    queue=Path(queue)
    if not available(queue,key):raise QueueError('Local service supervisor unavailable. Run scripts/start_kcee.py on this Mac.')
    if any(queue.glob('*.request.json')) or any(queue.glob('*.processing.json')):raise QueueError('Service control already in progress')
    job_id=str(uuid.uuid4())
    atomic_write(queue/(job_id+'.request.json'),envelope({'job_id':job_id,'action':action,'created_at':time.time()},key_bytes(key)))
    return job_id


def result(job_id,queue,key):
    job_id=str(uuid.UUID(job_id));queue=Path(queue)
    path=queue/(job_id+'.response.json')
    if path.exists():
        payload=read_signed(path,key_bytes(key),8192)
        if payload['job_id']!=job_id or payload.get('status') not in ('completed','failed'):raise QueueError('Service response identity or status mismatch')
        return payload
    if (queue/(job_id+'.request.json')).exists() or (queue/(job_id+'.processing.json')).exists():return {'job_id':job_id,'status':'pending'}
    raise FileNotFoundError('Unknown service control request')


def active_operation(queue,key):
    """Read authenticated pending work without trusting filenames as commands."""
    queue=Path(queue)
    for path in sorted([*queue.glob('*.processing.json'),*queue.glob('*.request.json')]):
        try:
            job_id=str(uuid.UUID(path.name.split('.')[0]))
            if (queue/(job_id+'.response.json')).exists():
                result(job_id,queue,key)
                continue
            payload=read_signed(path,key_bytes(key),4096)
            if set(payload)!={'job_id','action','created_at'} or payload['job_id']!=job_id or payload['action'] not in ('start','stop','voice_start','voice_stop'):raise ValueError('Invalid pending operation')
            age=time.time()-payload['created_at']
            if not -2<=age:raise ValueError('Invalid operation time')
            return {'job_id':job_id,'action':payload['action'],'status':'stalled' if age>510 else 'pending'}
        except (OSError,ValueError,KeyError,TypeError,QueueError):
            return {'status':'blocked','message':'Control queue needs inspection on this Mac; no operation was resumed.'}
    return None
