import fcntl,json,os,re,secrets,subprocess,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.embeddings import verify_runtime
from kcee.geometry_queue import available
root=Path(__file__).resolve().parents[1];runtime=root/'.local/embedding-runtime';local=root/'.local/embeddings';queue=local/'queue';verify_runtime(root);manifest=json.loads((runtime/'model-manifest.json').read_text());queue.mkdir(parents=True,exist_ok=True);local.chmod(0o700);queue.chmod(0o700)
lock=(local/'start.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
if available(queue,local/'key'):print('Local semantic search ready');raise SystemExit(0)
for path,binary in ((local/'key',True),(runtime/'server.key',False)):
    if not path.exists():
        if binary:path.write_bytes(secrets.token_bytes(32))
        else:path.write_text(secrets.token_hex(32)+'\n')
        path.chmod(0o600)
def ready():
    try:
        req=urllib.request.Request('http://127.0.0.1:8085/v1/models',headers={'Authorization':'Bearer '+(runtime/'server.key').read_text().strip()})
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=2) as response:return any(row.get('id')=='kcee-nomic-v1.5-f16' for row in json.load(response).get('data',[]))
    except Exception:return False
if not ready():
    devices=subprocess.check_output([str(root/manifest['server_relative_path']),'--list-devices'],text=True,timeout=15);match=re.search(r'(?m)^\s*(MTL[0-9]+):',devices)
    if not match:raise SystemExit('No Metal device; embedding CPU fallback is not enabled')
    args=[str(root/manifest['server_relative_path']),'-m',str(root/manifest['model_relative_path']),'--host','127.0.0.1','--port','8085','--api-key-file',str(runtime/'server.key'),'--alias','kcee-nomic-v1.5-f16','--device',match.group(1),'-ngl','99','--verbosity','4','--embeddings','--pooling','mean','-c','2048','-b','2048','-ub','2048','-np','1','-t','4','--no-webui']
    with (runtime/'server.log').open('ab') as log:server=subprocess.Popen(args,cwd=root,stdout=log,stderr=log,start_new_session=True,env={key:value for key,value in os.environ.items() if not key.startswith('LLAMA_')})
    (runtime/'server.pid').write_text(str(server.pid));deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        if ready():break
        if server.poll() is not None:raise SystemExit('Embedding model exited; inspect .local/embedding-runtime/server.log')
        time.sleep(.2)
    else:raise SystemExit('Embedding model not ready')
with (local/'worker.log').open('ab') as log:worker=subprocess.Popen([sys.executable,str(root/'scripts/embedding_worker.py')],cwd=root,stdout=log,stderr=log,start_new_session=True)
for _ in range(100):
    if available(queue,local/'key'):print('Local semantic search ready');break
    if worker.poll() is not None:raise SystemExit('Embedding gateway exited')
    time.sleep(.1)
else:raise SystemExit('Embedding gateway not ready')
