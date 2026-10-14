"""Start the local engineering-service supervisor idempotently."""
import fcntl,secrets,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.geometry_queue import available
root=Path(__file__).resolve().parents[1];local=root/'.local/control';queue=local/'queue';key=local/'key'
queue.mkdir(parents=True,exist_ok=True);local.chmod(0o700);queue.chmod(0o700)
lock=(local/'start.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
if not key.exists():
    with key.open('xb') as stream:stream.write(secrets.token_bytes(32))
    key.chmod(0o600)
if available(queue,key):print('Local service supervisor ready');raise SystemExit(0)
with (local/'worker.log').open('ab') as log:
    worker=subprocess.Popen([sys.executable,str(root/'scripts/service_supervisor.py')],cwd=root,stdout=log,stderr=log,start_new_session=True)
for _ in range(100):
    if available(queue,key):print('Local service supervisor ready');break
    if worker.poll() is not None:raise SystemExit('Supervisor exited; inspect .local/control/worker.log')
    time.sleep(.1)
else:raise SystemExit('Supervisor unavailable; inspect .local/control/worker.log')
