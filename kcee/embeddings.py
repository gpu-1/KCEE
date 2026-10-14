"""Bounded signed embedding transport; no remote inference or fabricated vectors."""
import hashlib,json,math,os,struct,time,uuid
from pathlib import Path
from kcee.geometry_queue import available,atomic_write,envelope,key_bytes,read_signed,encoded,QueueError
DIMENSIONS=768
MODEL_SHA='f7af6f66802f4df86eda10fe9bbcfc75c39562bed48ef6ace719a251cf1c2fdb'
PREFIXES={'document':'search_document: ','query':'search_query: '}
def float32_vector(values):
    if not isinstance(values,list) or len(values)!=DIMENSIONS or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ValueError('Invalid embedding dimensions or values')
    norm=math.sqrt(sum(v*v for v in values))
    if not math.isfinite(norm) or abs(norm-1)>1e-3:raise ValueError('Embedding must be L2 normalized')
    raw=struct.pack('<'+str(DIMENSIONS)+'f',*values);return list(struct.unpack('<'+str(DIMENSIONS)+'f',raw)),hashlib.sha256(raw).hexdigest()
def input_text(kind,text):
    if kind not in PREFIXES or not isinstance(text,str) or not 1<=len(text)<= (1800 if kind=='document' else 800):raise ValueError('Invalid bounded embedding input')
    return PREFIXES[kind]+text
def validate_job(payload,job):
    if set(payload)!={'job_id','created_at','kind','text'} or payload['job_id']!=job or not -2<=time.time()-payload['created_at']<30:raise ValueError('Invalid or expired embedding job')
    input_text(payload['kind'],payload['text']);return payload
def paths():return Path(os.environ.get('KCEE_EMBEDDING_QUEUE','/data/embeddings/queue')),Path(os.environ.get('KCEE_EMBEDDING_KEY','/data/embeddings/key'))
def status():
    queue,key=paths()
    if not available(queue,key):return {'available':False,'dimensions':DIMENSIONS}
    state=read_signed(queue/'heartbeat.json',key_bytes(key),4096)
    if state.get('model_sha256')!=MODEL_SHA or state.get('dimensions')!=DIMENSIONS:raise QueueError('Embedding worker model mismatch')
    return {'available':True,'dimensions':DIMENSIONS,'model':'nomic-ai/nomic-embed-text-v1.5-GGUF','model_sha256':MODEL_SHA,'model_manifest_sha256':state['model_manifest_sha256']}
def embed(kind,text):
    expected=status()
    if not expected['available']:raise QueueError('Local embedding service unavailable')
    queue,key_path=paths();key=key_bytes(key_path)
    if any(queue.glob('*.request.json')) or any(queue.glob('*.processing.json')):raise QueueError('Local embedding worker busy')
    job=str(uuid.uuid4());payload={'job_id':job,'created_at':time.time(),'kind':kind,'text':text};validate_job(payload,job)
    atomic_write(queue/(job+'.request.json'),envelope(payload,key));deadline=time.monotonic()+25
    response=queue/(job+'.response.json')
    while time.monotonic()<deadline:
        if response.exists():
            result=read_signed(response,key,32768)
            if result.get('job_id')!=job or result.get('status')!='completed':raise QueueError('Local embedding failed or response identity mismatch')
            vector,digest=float32_vector(result['vector'])
            if result['input_sha256']!=hashlib.sha256(input_text(kind,text).encode()).hexdigest() or result['vector_sha256']!=digest or result['model_sha256']!=expected['model_sha256'] or result['model_manifest_sha256']!=expected['model_manifest_sha256']:raise QueueError('Embedding response fingerprint mismatch')
            return {**expected,'vector':vector,'vector_sha256':digest,'input_sha256':result['input_sha256']}
        time.sleep(.05)
    raise QueueError('Local embedding request timed out')

def verify_runtime(root):
    root=Path(root);raw=(root/'.local/embedding-runtime/model-manifest.json').read_bytes();manifest=json.loads(raw)
    if manifest['model_sha256']!=MODEL_SHA or manifest['dimensions']!=DIMENSIONS or manifest['pooling']!='mean' or manifest['context_tokens']!=2048 or manifest['prefixes']!=PREFIXES:raise ValueError('Embedding configuration differs from pinned model')
    def check(relative,expected,base):
        path=root/relative;path.resolve().relative_to((root/base).resolve())
        if path.is_symlink():raise ValueError('Unsafe embedding runtime path')
        value=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
        if value.hexdigest()!=expected:raise ValueError('Embedding runtime hash mismatch')
    check(manifest['model_relative_path'],MODEL_SHA,'models/embeddings')
    if manifest['runtime_files'].get(manifest['server_relative_path'])!=manifest['server_sha256']:raise ValueError('Incomplete embedding runtime manifest')
    for relative,expected in manifest['runtime_files'].items():check(relative,expected,'.local/ai/llama')
    return {'model_sha256':MODEL_SHA,'model_manifest_sha256':hashlib.sha256(raw).hexdigest(),'dimensions':DIMENSIONS}
