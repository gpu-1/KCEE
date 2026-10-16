import json,threading,signal
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from kcee.cfd import benchmark
class Handler(BaseHTTPRequestHandler):
 def send(self,status,data):
  raw=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_GET(self):self.send(200,{'status':'ready','scope':'fully_developed_plane_poiseuille_verification'}) if self.path=='/health' else self.send(404,{'error':'Not found'})
 def do_POST(self):
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
