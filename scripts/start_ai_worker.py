"""Start verified loopback-only Metal inference and its signed native gateway."""
import fcntl,hashlib,json,secrets,re,os,subprocess,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.geometry_queue import available
from kcee.ai_runtime import verify_ai_runtime
root=Path(__file__).resolve().parents[1];runtime=root/'.local/ai';local=root/'.local/assistant';queue=local/'queue';key=local/'key'
if not (runtime/'runtime-manifest.json').is_file():raise SystemExit('Provision the AI runtime first: scripts/provision_ai.py')
queue.mkdir(parents=True,exist_ok=True);local.chmod(0o700);queue.chmod(0o700);runtime.chmod(0o700)
lock=(local/'start.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
verify_ai_runtime(root)
if (root/'.local/embedding-runtime/model-manifest.json').is_file():subprocess.run([sys.executable,str(root/'scripts/start_embeddings.py')],cwd=root,check=True,timeout=75)
if available(queue,key):print('Local study AI ready');raise SystemExit(0)
manifest=json.loads((runtime/'runtime-manifest.json').read_text())
server_key=runtime/'server.key'
if not server_key.exists():
    with server_key.open('x') as stream:stream.write(secrets.token_hex(32)+'\n')
    server_key.chmod(0o600)
if not key.exists():
    with key.open('xb') as stream:stream.write(secrets.token_bytes(32))
    key.chmod(0o600)
def server_ready():
    try:
        request=urllib.request.Request('http://127.0.0.1:8081/v1/models',headers={'Authorization':'Bearer '+server_key.read_text().strip()})
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=2) as response:return any(item.get('id')=='kcee-study-qwen3-4b' for item in json.load(response).get('data',[]))
    except Exception:return False
if not server_ready():
    devices=subprocess.check_output([str(root/manifest['server_relative_path']),'--list-devices'],text=True,timeout=15)
    metal=re.search(r'(?m)^\s*(MTL[0-9]+):',devices)
    if not metal:raise SystemExit('No native Metal device available; CPU fallback is not enabled')
    command=[str(root/manifest['server_relative_path']),'-m',str(root/manifest['model_relative_path']),'--host','127.0.0.1','--port','8081','--api-key-file',str(server_key),'--alias','kcee-study-qwen3-4b','--device',metal.group(1),'--verbosity','4','-ngl','99','-c','8192','-np','1','-t','4','-n','768','--reasoning','off','--chat-template-kwargs','{"enable_thinking":false}','--no-webui']
    with (runtime/'server.log').open('ab') as log:server=subprocess.Popen(command,cwd=root,stdout=log,stderr=log,start_new_session=True,env={name:value for name,value in os.environ.items() if not name.startswith('LLAMA_')})
    (runtime/'server.pid').write_text(str(server.pid))
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        if server_ready():break
        if server.poll() is not None:raise SystemExit('Native AI server exited; inspect .local/ai/server.log')
        time.sleep(.5)
    else:raise SystemExit('Native AI server not ready; inspect .local/ai/server.log')
with (local/'worker.log').open('ab') as log:worker=subprocess.Popen([sys.executable,str(root/'scripts/assistant_worker.py')],cwd=root,stdout=log,stderr=log,start_new_session=True)
for _ in range(100):
    if available(queue,key):print('Local study AI ready');break
    if worker.poll() is not None:raise SystemExit('AI gateway exited; inspect .local/assistant/worker.log')
    time.sleep(.1)
else:raise SystemExit('AI gateway not ready; inspect .local/assistant/worker.log')
