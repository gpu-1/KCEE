"""Cooperative CFD control; fixed solver commands run in cancellable process groups."""
import contextvars,os,signal,subprocess,threading,time
from contextlib import contextmanager
current=contextvars.ContextVar('cfd_control',default=None)
class Cancelled(Exception):pass
class Control:
 def __init__(self,event=None,progress=None,registered=None,identifier=None):self.event=event or threading.Event();self.progress=progress or (lambda **v:None);self.registered=registered or (lambda identifier:None);self.identifier=identifier
 def check(self):
  if self.event.is_set():raise Cancelled('CFD job cancelled')
@contextmanager
def using(control):
 token=current.set(control)
 try:yield control
 finally:current.reset(token)
def checkpoint(stage=None,**values):
 c=current.get()
 if c:
  c.check()
  if stage:c.progress(stage=stage,**values)
def headers():
 c=current.get();return {'X-KCEE-Job-ID':c.identifier} if c and c.identifier else {}
def registered(identifier):
 c=current.get()
 if c:c.registered(str(identifier))
def run_logged(command,root,name,timeout,env=None):
 c=current.get()
 if c is None:
  with (root/(name+'.log')).open('w') as log:return subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=timeout,cwd=root,env=env)
 c.check();c.progress(stage=name,log_path=str(root/(name+'.log')))
 with (root/(name+'.log')).open('w') as log:
  proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,cwd=root,start_new_session=True,env=env);deadline=time.monotonic()+timeout
  try:
   while proc.poll() is None:
    c.check()
    if time.monotonic()>deadline:raise subprocess.TimeoutExpired(command,timeout)
    c.event.wait(.2)
  except BaseException:
   try:os.killpg(proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:proc.wait(timeout=2)
   except subprocess.TimeoutExpired:
    try:os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    proc.wait()
   raise
 return subprocess.CompletedProcess(command,proc.returncode)
