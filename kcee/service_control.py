"""Signed, bounded requests for a project-local engineering-service supervisor."""
import time,uuid
from pathlib import Path
from kcee.geometry_queue import available,atomic_write,envelope,key_bytes,read_signed,QueueError


def validate_request(payload,job_id):
    if set(payload)!={'job_id','action','created_at'} or payload['job_id']!=job_id or payload['action'] not in ('start','stop'):
        raise ValueError('Unsupported service control request')
    if not -2<=time.time()-payload['created_at']<30:raise ValueError('Expired service control request')
    return payload['action']


def submit(action,queue,key):
    if action not in ('start','stop'):raise ValueError('Unsupported service action')
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
        if payload['job_id']!=job_id:raise QueueError('Service response identity mismatch')
        return payload
    if (queue/(job_id+'.request.json')).exists() or (queue/(job_id+'.processing.json')).exists():return {'job_id':job_id,'status':'pending'}
    raise FileNotFoundError('Unknown service control request')
