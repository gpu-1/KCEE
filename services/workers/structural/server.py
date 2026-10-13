import base64,json,tempfile,threading
from http.server import BaseHTTPRequestHandler,HTTPServer
from kcee.fea import benchmark
class Handler(BaseHTTPRequestHandler):
    def send(self,status,body):
        raw=json.dumps(body).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        self.send(200,{'status':'ready'}) if self.path=='/health' else self.send(404,{'error':'Not found'})
    def do_POST(self):
        if self.path!='/benchmark':self.send(404,{'error':'Not found'});return
        try:
            with tempfile.TemporaryDirectory() as tmp:result,archive=benchmark(tmp)
            self.send(200,{'result':result,'artifacts_base64':base64.b64encode(archive).decode()})
        except Exception as exc:self.send(503,{'error':str(exc)})
HTTPServer(('0.0.0.0',8005),Handler).serve_forever()
