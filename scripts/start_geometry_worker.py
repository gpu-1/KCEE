"""Start a project-local native worker; settings/logs live under ignored .local/."""
import fcntl,os,secrets,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.geometry_queue import available,read_signed,key_bytes
root=Path(__file__).resolve().parents[1];local=root/'.local/geometry';queue=local/'queue';key=local/'key'
if not (root/'.local/picogk/Kcee.Geometry').is_file():raise SystemExit('Provision PicoGK before starting the geometry worker')
queue.mkdir(parents=True,exist_ok=True);local.chmod(0o700);queue.chmod(0o700)
lock=(local/'start.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
if not key.exists():
    with key.open('xb') as f:f.write(secrets.token_bytes(32))
    key.chmod(0o600)
if available(queue,key):print('Native geometry worker already ready');raise SystemExit(0)
with (local/'worker.log').open('ab') as log:
    process=subprocess.Popen([sys.executable,'-m','kcee.geometry_worker','--queue',str(queue),'--key',str(key),'--executable',str(root/'host/macos/picogk/generate.sh')],cwd=root,stdout=log,stderr=log,start_new_session=True)
(local/'worker.pid').write_text(str(process.pid))
for _ in range(100):
    if available(queue,key):print('Native geometry worker ready');break
    if process.poll() is not None:raise SystemExit('Worker exited; inspect .local/geometry/worker.log')
    time.sleep(.1)
else:raise SystemExit('Worker not ready; inspect .local/geometry/worker.log')
