import json,threading,signal
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from kcee.thermal import benchmark
class Handler(BaseHTTPRequestHandler):
 def send(self,status,data):
  raw=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_GET(self):self.send(200,{'status':'ready','scope':'steady_1d_verification'}) if self.path=='/health' else self.send(404,{'error':'Not found'})
 def do_POST(self):
  if self.path!='/benchmark':self.send(404,{'error':'Not found'});return
  if int(self.headers.get('Content-Length','0'))!=0:self.send(422,{'error':'Benchmark accepts no parameters'});return
  self.send(200,benchmark())
server=ThreadingHTTPServer(('0.0.0.0',8006),Handler)
def stop(*_):threading.Thread(target=server.shutdown,daemon=True).start()
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
try:server.serve_forever()
finally:server.server_close()
