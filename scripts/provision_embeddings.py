"""Explicit download of official pinned F16 embedding weights; reuse verified llama runtime."""
import hashlib,json,sys,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.ai_runtime import verify_ai_runtime
from kcee.embeddings import MODEL_SHA,DIMENSIONS,PREFIXES,verify_runtime
root=Path(__file__).resolve().parents[1];verify_ai_runtime(root)
revision='0188c9bf409793f810680a5a431e7b899c46104c';name='nomic-embed-text-v1.5.f16.gguf';url='https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/'+revision+'/'+name;size=274290560
runtime=root/'.local/embedding-runtime';runtime.mkdir(parents=True,exist_ok=True);runtime.chmod(0o700);models=root/'models/embeddings';models.mkdir(parents=True,exist_ok=True);path=models/name
def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()
if not path.exists():
    partial=path.with_suffix('.gguf.part');offset=partial.stat().st_size if partial.exists() else 0
    req=urllib.request.Request(url,headers={'Range':f'bytes={offset}-'} if offset else {})
    with urllib.request.urlopen(req,timeout=60) as response:
        if offset and (response.status!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {offset}-')):offset=0
        total=offset;last=int(total/size*10)
        with partial.open('ab' if offset else 'wb') as stream:
            for block in iter(lambda:response.read(1024*1024),b''):
                total+=len(block)
                if total>size:raise ValueError('Embedding download exceeds pinned size')
                stream.write(block);progress=int(total/size*10)
                if progress>last:print(str(min(progress*10,100))+'%',flush=True);last=progress
    if partial.stat().st_size!=size or digest(partial)!=MODEL_SHA:raise ValueError('Embedding asset differs from official digest')
    partial.rename(path)
if path.stat().st_size!=size or digest(path)!=MODEL_SHA:raise ValueError('Embedding weight integrity mismatch')
ai=json.loads((root/'.local/ai/runtime-manifest.json').read_text())
manifest={'schema_version':1,'model':'nomic-ai/nomic-embed-text-v1.5-GGUF','model_revision':revision,'model_relative_path':str(path.relative_to(root)),'model_sha256':MODEL_SHA,'model_size_bytes':size,'source_url':url,'dimensions':DIMENSIONS,'pooling':'mean','context_tokens':2048,'prefixes':PREFIXES,'normalization':'L2 float32','runtime_version':'llama.cpp b11417','runtime_files':ai['runtime_files'],'server_relative_path':ai['server_relative_path'],'server_sha256':ai['server_sha256']}
(runtime/'model-manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(verify_runtime(root)))
