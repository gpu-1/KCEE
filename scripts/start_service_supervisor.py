"""Start the local engineering-service supervisor idempotently."""
import fcntl,secrets,subprocess,sys,time,hashlib,os,signal
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.geometry_queue import available,key_bytes,read_signed
root=Path(__file__).resolve().parents[1];local=root/'.local/control';queue=local/'queue';key=local/'key'
queue.mkdir(parents=True,exist_ok=True);local.chmod(0o700);queue.chmod(0o700)
lock=(local/'start.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
if not key.exists():
    with key.open('xb') as stream:stream.write(secrets.token_bytes(32))
    key.chmod(0o600)
if available(queue,key):
    state=read_signed(queue/'heartbeat.json',key_bytes(key),4096)
    if state.get('source_sha256')==hashlib.sha256((root/'scripts/service_supervisor.py').read_bytes()).hexdigest():print('Local service supervisor ready');raise SystemExit(0)
    if any(queue.glob('*.request.json')) or any(queue.glob('*.processing.json')):raise SystemExit('Finish the active service operation before reloading the supervisor')
    pid=state['pid']
    if type(pid) is not int or pid<=1:raise SystemExit('Invalid supervisor process identity')
    command=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True).strip()
    if not command.endswith(' '+str(root/'scripts/service_supervisor.py')):raise SystemExit('Supervisor process mismatch; no signal sent')
    os.kill(pid,signal.SIGTERM)
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        state=read_signed(queue/'heartbeat.json',key_bytes(key),4096)
        if state['pid']==pid and state['state']=='stopped':break
        time.sleep(.1)
    else:raise SystemExit('Supervisor has not stopped; no forced termination used')

with (local/'worker.log').open('ab') as log:
    worker=subprocess.Popen([sys.executable,str(root/'scripts/service_supervisor.py')],cwd=root,stdout=log,stderr=log,start_new_session=True)
for _ in range(100):
    if available(queue,key):print('Local service supervisor ready');break
    if worker.poll() is not None:raise SystemExit('Supervisor exited; inspect .local/control/worker.log')
    time.sleep(.1)
else:raise SystemExit('Supervisor unavailable; inspect .local/control/worker.log')
