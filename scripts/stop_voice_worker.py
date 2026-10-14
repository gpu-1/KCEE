"""Gracefully stop this project's authenticated native Kokoro worker."""
import os,signal,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.geometry_queue import available,key_bytes,read_signed

def stop_voice(root,timeout=150):
    local=root/'.local/voice';queue=local/'queue';key=local/'key'
    if not available(queue,key):return
    payload=read_signed(queue/'heartbeat.json',key_bytes(key),4096);pid=payload['pid']
    if type(pid) is not int or pid<=1:raise ValueError('Invalid voice worker identity')
    command=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True).strip()
    if not command.endswith(' '+str(root/'scripts/voice_worker.py')):raise ValueError('Voice worker process mismatch; no signal sent')
    os.kill(pid,signal.SIGTERM);deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        current=read_signed(queue/'heartbeat.json',key_bytes(key),4096)
        if current['pid']==pid and current['state']=='stopped':return
        time.sleep(.2)
    raise ValueError('Voice worker did not finish graceful shutdown; no force kill used')

if __name__=='__main__':
    stop_voice(Path(__file__).resolve().parents[1]);print('Local Kokoro worker stopped or already unavailable')
