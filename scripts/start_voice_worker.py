"""Start provisioned local Kokoro; no model download or audio playback."""
import fcntl,secrets,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.geometry_queue import available
root=Path(__file__).resolve().parents[1];local=root/'.local/voice';queue=local/'queue';key=local/'key'
if not (root/'.local/kokoro/venv/bin/python').is_file() or not (root/'models/kokoro/runtime-manifest.json').is_file():raise SystemExit('Provision Kokoro first; see host/macos/kokoro/README.md')
queue.mkdir(parents=True,exist_ok=True);local.chmod(0o700);queue.chmod(0o700)
lock=(local/'start.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
if not key.exists():
    with key.open('xb') as stream:stream.write(secrets.token_bytes(32))
    key.chmod(0o600)
if available(queue,key):print('Local Kokoro worker ready');raise SystemExit(0)
with (local/'worker.log').open('ab') as log:worker=subprocess.Popen([sys.executable,str(root/'scripts/voice_worker.py')],cwd=root,stdout=log,stderr=log,start_new_session=True)
for _ in range(100):
    if available(queue,key):print('Local Kokoro worker ready');break
    if worker.poll() is not None:raise SystemExit('Voice worker exited; inspect .local/voice/worker.log')
    time.sleep(.1)
else:raise SystemExit('Voice worker unavailable; inspect .local/voice/worker.log')
