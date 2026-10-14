import json,os,signal,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.geometry_queue import key_bytes,read_signed

def stop_embeddings(root,timeout=30):
    local=root/'.local/embeddings';runtime=root/'.local/embedding-runtime'
    if (local/'key').is_file() and (local/'queue/heartbeat.json').is_file():
        state=read_signed(local/'queue/heartbeat.json',key_bytes(local/'key'),4096)
        if state['state']!='stopped' and -2<=time.time()-state['created_at']<10:
            pid=state['pid']
            if type(pid) is not int or pid<=1:raise ValueError('Invalid embedding gateway identity')
            command=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True).strip()
            if not command.endswith(' '+str(root/'scripts/embedding_worker.py')):raise ValueError('Embedding gateway process mismatch')
            os.kill(pid,signal.SIGTERM);deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                state=read_signed(local/'queue/heartbeat.json',key_bytes(local/'key'),4096)
                if state['pid']==pid and state['state']=='stopped':break
                time.sleep(.1)
            else:raise ValueError('Embedding gateway still running; no force kill used')
    if not (runtime/'server.pid').is_file():return
    pid=int((runtime/'server.pid').read_text());manifest=json.loads((runtime/'model-manifest.json').read_text())
    try:command=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True).strip()
    except subprocess.CalledProcessError:return
    if pid<=1 or not command.startswith(str(root/manifest['server_relative_path'])+' ') or str(root/manifest['model_relative_path']) not in command:raise ValueError('Embedding model process mismatch')
    os.kill(pid,signal.SIGTERM);deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        process=subprocess.run(['ps','-p',str(pid),'-o','stat='],capture_output=True,text=True)
        if process.returncode or process.stdout.strip().startswith('Z'):return
        time.sleep(.1)
    raise ValueError('Embedding model still running; no force kill used')
if __name__=='__main__':stop_embeddings(Path(__file__).resolve().parents[1]);print('Local semantic search stopped')
