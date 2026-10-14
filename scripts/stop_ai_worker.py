"""Gracefully stop this project's signed AI gateway and private model server."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.geometry_queue import key_bytes,read_signed

def stop_ai(root,timeout=170):
    local=root/'.local/assistant';runtime=root/'.local/ai'
    if (local/'key').is_file() and (local/'queue/heartbeat.json').is_file():
        state=read_signed(local/'queue/heartbeat.json',key_bytes(local/'key'),4096)
        if state['state']!='stopped' and -2<=time.time()-state['created_at']<10:
            pid=state['pid']
            if type(pid) is not int or pid<=1:raise ValueError('Invalid AI gateway identity')
            command=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True).strip()
            if not command.endswith(' '+str(root/'scripts/assistant_worker.py')):raise ValueError('AI gateway process mismatch; no signal sent')
            os.kill(pid,signal.SIGTERM);deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                state=read_signed(local/'queue/heartbeat.json',key_bytes(local/'key'),4096)
                if state['pid']==pid and state['state']=='stopped':break
                time.sleep(.2)
            else:raise ValueError('AI gateway has not stopped; no force kill used')
    if not (runtime/'server.pid').is_file():return
    pid=int((runtime/'server.pid').read_text());manifest=json.loads((runtime/'runtime-manifest.json').read_text())
    try:command=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True).strip()
    except subprocess.CalledProcessError:return
    if pid<=1 or not command.startswith(str(root/manifest['server_relative_path'])+' ') or str(root/manifest['model_relative_path']) not in command:raise ValueError('AI model process mismatch; no signal sent')
    os.kill(pid,signal.SIGTERM)
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        result=subprocess.run(['ps','-p',str(pid),'-o','stat='],capture_output=True,text=True)
        if result.returncode or result.stdout.strip().startswith('Z'):return
        time.sleep(.1)
    raise ValueError('AI model server has not stopped; no force kill used')

if __name__=='__main__':stop_ai(Path(__file__).resolve().parents[1]);print('Local study AI stopped or already unavailable')
