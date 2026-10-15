"""Project-local service supervisor. No network listener or arbitrary commands."""
import fcntl,os,signal,hashlib,subprocess,sys,threading,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.geometry_queue import atomic_write,envelope,key_bytes,read_signed
from kcee.service_control import validate_request
from scripts.stop_kcee import stop_native
from scripts.stop_voice_worker import stop_voice
from scripts.stop_ai_worker import stop_ai
# The AI lifecycle now includes the provisioned semantic embedding service.
root=Path(__file__).resolve().parents[1];local=root/'.local/control';queue=local/'queue';key=key_bytes(local/'key')
lock=(local/'worker.lock').open('a')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
source_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
stop=threading.Event()
signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
def heartbeat():
    while not stop.is_set():
        atomic_write(queue/'heartbeat.json',envelope({'state':'ready','pid':os.getpid(),'created_at':time.time(),'source_sha256':source_hash},key));stop.wait(2)
thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
try:
    while not stop.is_set():
        for path in sorted(queue.glob('*.request.json')):
            try:
                job_id=str(uuid.UUID(path.name.removesuffix('.request.json')))
                action=validate_request(read_signed(path,key,4096),job_id)
                claimed=queue/(job_id+'.processing.json');path.rename(claimed)
                if (queue/(job_id+'.response.json')).exists():claimed.unlink();continue
            except (OSError,ValueError,KeyError,TypeError,RuntimeError):
                path.unlink(missing_ok=True);continue
            try:
                with (local/'operations.log').open('ab') as log:
                    if action=='ai_start':
                        subprocess.run([sys.executable,str(root/'scripts/start_ai_worker.py')],cwd=root,stdout=log,stderr=log,check=True,timeout=150)
                    elif action=='ai_stop':stop_ai(root,170)
                    elif action=='voice_start':
                        subprocess.run([sys.executable,str(root/'scripts/start_voice_worker.py')],cwd=root,stdout=log,stderr=log,check=True,timeout=30)
                    elif action=='voice_stop':stop_voice(root,150)
                    elif action=='start':
                        subprocess.run([sys.executable,str(root/'scripts/start_geometry_worker.py')],cwd=root,stdout=log,stderr=log,check=True,timeout=30)
                        command=['docker','compose','--profile','fea','up','-d','--no-deps','--wait','--wait-timeout','60','structural','thermal','cfd']
                    elif action=='stop':command=['docker','compose','--profile','fea','stop','--timeout','300','structural','thermal','cfd']
                    if action in ('start','stop'):subprocess.run(command,cwd=root,stdout=log,stderr=log,check=True,timeout=320)
                    if action=='stop':stop_native(root,150)
                response={'job_id':job_id,'action':action,'status':'completed'}
            except Exception:
                response={'job_id':job_id,'action':action,'status':'failed','message':'Service operation failed. Inspect .local/control/operations.log and refresh service status.'}
            atomic_write(queue/(job_id+'.response.json'),envelope(response,key));claimed.unlink(missing_ok=True)
        for path in queue.glob('*.response.json'):
            if time.time()-path.stat().st_mtime>86400:path.unlink(missing_ok=True)
        stop.wait(.2)
finally:
    stop.set();thread.join(timeout=3)
    atomic_write(queue/'heartbeat.json',envelope({'state':'stopped','pid':os.getpid(),'created_at':time.time()},key))
