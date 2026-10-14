"""Stop local services without removing containers, volumes or saved artifacts."""
import argparse,os,signal,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.geometry_queue import available,key_bytes,read_signed
from scripts.stop_voice_worker import stop_voice


def worker_command_matches(command,root):
    expected=' -m kcee.geometry_worker --queue '+str(root/'.local/geometry/queue')+' --key '+str(root/'.local/geometry/key')+' --executable '+str(root/'host/macos/picogk/generate.sh')
    return command.strip().endswith(expected) and bool(command.strip()[:-len(expected)])


def stop_native(root,timeout=150):
    local=root/'.local/geometry';queue=local/'queue';key=local/'key'
    if not available(queue,key):
        print('No ready native geometry worker found.')
        return 0
    payload=read_signed(queue/'heartbeat.json',key_bytes(key),4096)
    pid=payload['pid']
    if type(pid) is not int or pid<=1 or (local/'worker.pid').read_text().strip()!=str(pid):raise ValueError('Native worker PID identity mismatch')
    command=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True)
    if not worker_command_matches(command,root):raise ValueError('Native worker process identity mismatch; no signal sent')
    os.kill(pid,signal.SIGTERM)
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        state=read_signed(queue/'heartbeat.json',key_bytes(key),4096)
        if state['pid']==pid and state['state']=='stopped':
            print('Native geometry worker stopped.')
            return 0
        time.sleep(.2)
    raise ValueError('Native worker has not finished its graceful shutdown; no forced termination was used')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout',type=int,default=150,help='Grace period in seconds (1–300; default 150)')
    args=parser.parse_args()
    if not 1<=args.timeout<=300:parser.error('Timeout must be between 1 and 300 seconds')
    root=Path(__file__).resolve().parents[1];local=root/'.local/geometry';queue=local/'queue';key=local/'key'
    try:
        subprocess.run(['docker','compose','--profile','viewer','--profile','fea','stop','--timeout',str(args.timeout)],cwd=root,check=True)
        stop_native(root,args.timeout)
        stop_voice(root,args.timeout)
        print('KCEE stopped. Database volumes, models and run artifacts retained.')
        return 0
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as error:
        print('Shutdown incomplete: '+str(error),file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
