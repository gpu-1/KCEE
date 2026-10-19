"""Ephemeral worker command status; cancellation is scoped to a validated job UUID."""
import re,threading,time,uuid
from pathlib import Path
from kcee.cfd_control import Control
lock=threading.RLock();jobs={}
def begin(identifier):
 identifier=str(uuid.UUID(identifier))
 with lock:
  existing=jobs.get(identifier)
  if existing and existing['active']:raise ValueError('Worker job is already active')
  # Keep cancellation set across sequential cases belonging to the same API job.
  event=existing['event'] if existing else threading.Event()
  jobs[identifier]={'stage':'preparing','active':True,'event':event,'updated_at':time.time()}
  for key in list(jobs):
   if key!=identifier and not jobs[key]['active'] and (len(jobs)>100 or time.time()-jobs[key]['updated_at']>3600):del jobs[key]
 def progress(**values):
  with lock:jobs[identifier].update(values,updated_at=time.time())
 return Control(event,progress,identifier=identifier)
def end(identifier):
 with lock:jobs[identifier].update(active=False,stage='finished',updated_at=time.time())
def status(identifier,cancel=False):
 with lock:
  j=jobs[str(uuid.UUID(identifier))]
  if cancel and j['active']:j['event'].set()
  result={'stage':j['stage'],'active':j['active'],'cancel_requested':j['event'].is_set()};path=j.get('log_path')
 if path:
  result['case']=j.get('case','Current case')
  try:
   with Path(path).open('rb') as stream:stream.seek(max(0,stream.seek(0,2)-65536));text=stream.read().decode(errors='replace')
   times=re.findall(r'^Time = ([\d.eE+-]+)',text,re.M)
   if times:result['iteration']=float(times[-1]);result['iteration_target']=j.get('iteration_target',1500) if j['stage']=='simpleFoam' else .5 if j['stage']=='icoFoam' else None;result['progress_unit']='s' if j['stage']=='icoFoam' else 'iterations'
  except OSError:pass
 return result
