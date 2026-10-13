"""Native macOS worker: signed file queue, no host TCP listener."""
import argparse,base64,hashlib,json,os,signal,tempfile,threading,time,uuid
from pathlib import Path
from kcee.geometry_queue import atomic_write,envelope,key_bytes,read_signed,encoded
from kcee.picogk import generate

def serve(queue,key_path,executable):
    queue=Path(queue);queue.mkdir(parents=True,exist_ok=True);key=key_bytes(key_path);stop=threading.Event()
    def terminate(*_):stop.set()
    signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
    def heartbeat():
        while not stop.is_set():
            atomic_write(queue/'heartbeat.json',envelope({'state':'ready','pid':os.getpid(),'created_at':time.time()},key));stop.wait(2)
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
    try:
        while not stop.is_set():
            for path in sorted(queue.glob('*.request.json')):
                # Requests cannot supply filesystem paths or executable names.
                try:
                    job_id=str(uuid.UUID(path.name.removesuffix('.request.json')))
                    payload=read_signed(path,key,8192)
                    if payload['job_id']!=job_id or payload['schema_version']!=1 or not -2<=time.time()-payload['created_at']<135:raise ValueError('Invalid or expired job')
                    if (queue/(job_id+'.done')).exists():path.unlink();continue
                    claimed=queue/(job_id+'.processing.json');os.replace(path,claimed)
                except (OSError,ValueError,KeyError,TypeError,RuntimeError):
                    path.unlink(missing_ok=True);continue
                try:
                    req=payload['request']
                    if set(req)!={'geometry_mm','options'}:raise ValueError('Unsupported request fields')
                    with tempfile.TemporaryDirectory(prefix='kcee-native-') as temporary:
                        metadata=generate(temporary,req['geometry_mm'],req['options'],executable)
                        metadata['transport']='signed_local_queue'
                        stl=(Path(temporary)/'bracket.stl').read_bytes()
                        if len(stl)>8*1024*1024:raise ValueError('Native artifact exceeds queue limit')
                    result={'job_id':job_id,'status':'completed','request_sha256':hashlib.sha256(encoded(req)).hexdigest(),'metadata':metadata,'stl_sha256':hashlib.sha256(stl).hexdigest(),'stl_base64':base64.b64encode(stl).decode()}
                except Exception as exc:
                    result={'job_id':job_id,'status':'failed','error':str(exc)[-2000:]}
                atomic_write(queue/(job_id+'.response.json'),envelope(result,key));(queue/(job_id+'.done')).touch();claimed.unlink(missing_ok=True)
            # Expired responses/replay markers are safe to discard after their request TTL.
            for pattern in ('*.done','*.response.json'):
                for path in queue.glob(pattern):
                    try:
                        if time.time()-path.stat().st_mtime>300:path.unlink(missing_ok=True)
                    except FileNotFoundError:pass
            stop.wait(.1)
    finally:
        stop.set();thread.join(timeout=3)
        atomic_write(queue/'heartbeat.json',envelope({'state':'stopped','pid':os.getpid(),'created_at':time.time()},key))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--queue',required=True);parser.add_argument('--key',required=True);parser.add_argument('--executable',required=True);args=parser.parse_args()
    serve(args.queue,args.key,args.executable)
