import json,threading,signal,shutil
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from kcee.cfd import benchmark
vortex_lock=threading.Lock()
class Handler(BaseHTTPRequestHandler):
 def send(self,status,data):
  raw=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_GET(self):self.send(200,{'status':'ready','scope':'channel_vortex_and_exploratory_bracket_flow','bracket_flow':all(shutil.which(n) for n in ('surfaceCheck','snappyHexMesh','simpleFoam')),'openfoam_vortex':all(shutil.which(n) for n in ('blockMesh','checkMesh','icoFoam'))}) if self.path=='/health' else self.send(404,{'error':'Not found'})
 def do_POST(self):
  if self.path=='/bracket-flow':
   if not vortex_lock.acquire(blocking=False):self.send(409,{'error':'CFD worker busy'});return
   try:
    import base64
    from kcee.bracket_flow import run_payload
    length=int(self.headers.get('Content-Length','0'))
    if not 1<=length<=17*1024*1024:raise ValueError('Surface payload exceeds limit')
    payload=json.loads(self.rfile.read(length))
    if set(payload)-{'stl_base64','mesh_name','domain_name','bore_level','sampling_version'} or 'stl_base64' not in payload:raise ValueError('Unsupported flow inputs')
    self.send(200,run_payload(base64.b64decode(payload['stl_base64'],validate=True),payload.get('mesh_name','coarse'),payload.get('domain_name','base'),payload.get('bore_level',4),payload.get('sampling_version','compact-radius-v1')))
   except Exception:self.send(503,{'error':'Bracket flow preparation failed'})
   finally:vortex_lock.release()
   return
  if self.path=='/vortex':
   if self.headers.get('Content-Length','0')!='0':self.send(422,{'error':'Fixed vortex case accepts no parameters'});return
   if not vortex_lock.acquire(blocking=False):self.send(409,{'error':'Vortex worker busy'});return
   try:
    from kcee.openfoam_vortex import execute
    self.send(200,execute())
   except Exception:self.send(503,{'error':'OpenFOAM vortex execution failed'})
   finally:vortex_lock.release()
   return
  if self.path!='/benchmark':self.send(404,{'error':'Not found'});return
  try:
   length=int(self.headers.get('Content-Length','0'))
   if not 0<=length<=2048:raise ValueError('Input too large')
   inputs=json.loads(self.rfile.read(length)) if length else None
   if inputs is not None and not isinstance(inputs,dict):raise ValueError('Use a channel input object')
   result=benchmark(inputs)
  except (ValueError,TypeError):self.send(422,{'error':'Invalid channel inputs'});return
  self.send(200,result)
server=ThreadingHTTPServer(('0.0.0.0',8007),Handler)
def stop(*_):threading.Thread(target=server.shutdown,daemon=True).start()
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
try:server.serve_forever()
finally:server.server_close()
