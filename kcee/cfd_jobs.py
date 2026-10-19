"""Durable single-active CFD jobs. Registry artifacts remain the authoritative evidence."""
import copy,json,os,threading,time,uuid
from pathlib import Path
from urllib.request import Request,urlopen
from kcee.cfd_control import Control,using,Cancelled
KINDS=('flow','refinement','domains','combined','local','reference','joint','vortex','forces','native_forces','layer_forces','force_convergence')
ACTIVE=('queued','running','cancel_requested')
def validate(kind,parent,options):
 if kind not in KINDS or not isinstance(options,dict):raise ValueError('Choose a supported CFD study')
 if kind!='vortex':str(uuid.UUID(str(parent)))
 elif parent is not None:raise ValueError('Vortex does not take a parent')
 if kind!='flow' and options:raise ValueError('This study uses fixed inputs')
 if kind=='flow':
  from kcee.bracket_flow import domain_spec,validate_profile
  if set(options)-{'mesh_name','domain_name','bore_level','sampling_version','local_profile'}:raise ValueError('Unsupported flow inputs')
  mesh=options.get('mesh_name','coarse');domain=options.get('domain_name','base');bore=options.get('bore_level',4);profile=options.get('local_profile','baseline');version=options.get('sampling_version','compact-radius-v1')
  if not isinstance(mesh,str) or not isinstance(domain,str) or type(bore) is not int or bore not in (4,5) or version not in ('compact-radius-v1','first-enclosing-v1'):raise ValueError('Invalid flow recipe')
  domain_spec(mesh,domain);validate_profile(profile,mesh,domain,bore)
  if profile!='baseline' and version!='compact-radius-v1':raise ValueError('Targeted flow requires Compact v1')
class Jobs:
 def __init__(self,root,runner,remote=None):
  self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.runner=runner;self.remote=remote or self._remote;self.lock=threading.RLock();self.jobs={};self.events={}
  for path in sorted(self.root.glob('*.json'),key=lambda p:p.stat().st_mtime)[-100:]:
   try:
    j=json.loads(path.read_text());identifier=str(uuid.UUID(j['id']));assert path.stem==identifier and j['kind'] in KINDS
    assert j['state'] in ACTIVE+('completed','failed','cancelled','interrupted') and isinstance(j['created_at'],(float,int)) and isinstance(j['completed_run_ids'],list)
    validate(j['kind'],j['parent_id'],j['options'])
    self.jobs[identifier]=j
    if j['state'] in ACTIVE:j.update(state='interrupted',stage='interrupted',error='API restarted; saved cases are retained. Retry explicitly.');self._save(j);threading.Thread(target=self._recover_cancel,args=(identifier,),daemon=True).start()
   except (ValueError,KeyError,TypeError,AssertionError):continue
 def _save(self,j):
  j['updated_at']=time.time();tmp=self.root/(j['id']+'.tmp');tmp.write_text(json.dumps(j,indent=2));os.replace(tmp,self.root/(j['id']+'.json'))
 def _remote(self,identifier,cancel=False):
  path='/jobs/'+identifier+('/cancel' if cancel else '');req=Request(os.environ.get('CFD_URL','http://cfd:8007')+path,data=b'' if cancel else None,method='POST' if cancel else 'GET')
  with urlopen(req,timeout=2) as r:return json.load(r)
 def _cancel_remote(self,identifier):
  try:return self.remote(identifier,True)
  except Exception:return None
 def _recover_cancel(self,identifier):
  for _ in range(30):
   status=self._cancel_remote(identifier)
   if status is not None and not status.get('active',False):return
   time.sleep(.5)
 def list(self):
  with self.lock:return copy.deepcopy(sorted(self.jobs.values(),key=lambda j:j['created_at'],reverse=True)[:20])
 def get(self,identifier):
  with self.lock:j=copy.deepcopy(self.jobs[str(identifier)])
  if j['state'] in ACTIVE:
   try:
    status=self.remote(j['id']);j['worker']={k:status[k] for k in (('stage','iteration','iteration_target','case','active','progress_unit') if status.get('active',True) else ('stage','active')) if k in status}
   except Exception:pass
  return j
 def start(self,kind,parent=None,options=None,retry_of=None):
  options=copy.deepcopy(options or {});validate(kind,parent,options)
  with self.lock:
   if any(j['state'] in ACTIVE for j in self.jobs.values()):raise RuntimeError('A CFD job is already active')
   if len(self.jobs)>=100:raise RuntimeError('CFD job history is full; archive its records before starting more jobs')
   identifier=str(uuid.uuid4());now=time.time();j={'id':identifier,'kind':kind,'parent_id':str(parent) if parent else None,'options':options,'retry_of':retry_of,'state':'queued','stage':'queued','created_at':now,'completed_run_ids':[]};self.jobs[identifier]=j;self.events[identifier]=threading.Event();self._save(j)
   threading.Thread(target=self._run,args=(identifier,),daemon=True).start();return copy.deepcopy(j)
 def cancel(self,identifier):
  with self.lock:
   j=self.jobs[str(identifier)];accepted=j['state'] in ('queued','running')
   if accepted:self.events[j['id']].set();j.update(state='cancel_requested',stage='cancelling');self._save(j);threading.Thread(target=self._relay,args=(j['id'],),daemon=True).start()
   return dict(copy.deepcopy(j),cancel_accepted=accepted)
 def _relay(self,identifier):
  while True:
   self._cancel_remote(identifier)
   with self.lock:
    if self.jobs[identifier]['state'] not in ACTIVE:return
   time.sleep(.5)
 def retry(self,identifier):
  with self.lock:
   j=copy.deepcopy(self.jobs[str(identifier)])
   if j['state'] not in ('failed','cancelled','interrupted'):raise ValueError('Only failed, cancelled or interrupted jobs can be retried')
  return self.start(j['kind'],j['parent_id'],j['options'],j['id'])
 def _run(self,identifier):
  with self.lock:j=self.jobs[identifier];event=self.events[identifier];j.update(state='running',stage='verifying_sources');self._save(j)
  def progress(**values):
   with self.lock:
    if not event.is_set():j.update(values);self._save(j)
  def registered(run_id):
   with self.lock:
    if run_id not in j['completed_run_ids']:j['completed_run_ids'].append(run_id);self._save(j)
  try:
   control=Control(event,progress,registered,identifier)
   with using(control):control.check();result=self.runner(j['kind'],j['parent_id'],copy.deepcopy(j['options']))
   # A returned result has completed registration; a late cancellation cannot erase it.
   with self.lock:j.update(state='completed',stage='completed',result=result);self._save(j)
  except Exception as e:
   with self.lock:
    cancelled=event.is_set() or isinstance(e,Cancelled);detail=getattr(e,'detail',None);message=detail if isinstance(detail,str) else str(e)
    if isinstance(detail,dict) and detail.get('run_id'):j['failed_run_id']=str(detail['run_id'])
    j.update(state='cancelled' if cancelled else 'failed',stage='cancelled' if cancelled else 'failed',error='Cancelled; completed cases remain saved.' if cancelled else message[:500]);self._save(j)
