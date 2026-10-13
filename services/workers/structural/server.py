import base64,io,json,subprocess,sys,tempfile,zipfile,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from kcee.fea import benchmark
job_lock=threading.Lock()
class Handler(BaseHTTPRequestHandler):
    def send(self,status,body):
        raw=json.dumps(body).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):self.send(200,{'status':'ready'}) if self.path=='/health' else self.send(404,{'error':'Not found'})
    def do_POST(self):
        if self.path not in ('/benchmark','/bracket'):self.send(404,{'error':'Not found'});return
        if not job_lock.acquire(blocking=False):self.send(503,{'error':'Structural worker busy; retry when the current job completes'});return
        try:
            self.execute_job()
        finally:job_lock.release()
    def execute_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                if self.path=='/benchmark':result,archive=benchmark(tmp)
                else:
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<length<12*1024*1024:raise ValueError('Invalid request size')
                    data=json.loads(self.rfile.read(length));stl=base64.b64decode(data['stl_base64'],validate=True)
                    if len(stl)>8*1024*1024:raise ValueError('STL exceeds bounded demo size')
                    path=Path(tmp)/'source.stl';path.write_bytes(stl);output=Path(tmp)/'study'
                    process=subprocess.run([sys.executable,'-m','kcee.bracket_fea','--stl',str(path),'--output',str(output),'--expected-volume',str(float(data['expected_volume_mm3']))],capture_output=True,text=True,timeout=300)
                    (Path(tmp)/'job.log').write_text(process.stdout+'\n'+process.stderr)
                    if process.returncode!=0:raise RuntimeError('Bracket meshing/solve failed; see retained job.log')
                    result=json.loads((output/'fea.json').read_text());archive=(output/'fea-artifacts.zip').read_bytes()
                self.send(200,{'result':result,'artifacts_base64':base64.b64encode(archive).decode()})
            except Exception as exc:
                archive=io.BytesIO()
                with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zipped:
                    for p in Path(tmp).rglob('*'):
                        if p.is_file():zipped.write(p,p.relative_to(tmp))
                self.send(503,{'error':str(exc),'artifacts_base64':base64.b64encode(archive.getvalue()).decode()})
ThreadingHTTPServer(('0.0.0.0',8005),Handler).serve_forever()
