import json,tempfile,threading,time,unittest,sys
from pathlib import Path
from kcee.cfd_jobs import Jobs,validate
from kcee.cfd_control import checkpoint,current,run_logged,Control,using,Cancelled,registered
class CFDJobsTests(unittest.TestCase):
 def wait(self,jobs,i):
  end=time.monotonic()+5
  while time.monotonic()<end:
   j=jobs.get(i)
   if j['state'] not in ('queued','running','cancel_requested'):return j
   time.sleep(.01)
  self.fail('job did not finish')
 def test_cancel_retains_completed_cases_and_retry_uses_new_id(self):
  ready=threading.Event();attempts=[]
  def run(kind,parent,options):
   attempts.append(options);registered('saved-case')
   if len(attempts)==1:
    ready.set();current.get().event.wait(3);checkpoint()
   return {'run_id':'complete'}
  with tempfile.TemporaryDirectory() as tmp:
   jobs=Jobs(tmp,run,remote=lambda *a:{});first=jobs.start('vortex');ready.wait(2)
   with self.assertRaises(RuntimeError):jobs.start('vortex')
   jobs.cancel(first['id']);j=self.wait(jobs,first['id']);self.assertEqual(j['state'],'cancelled');self.assertEqual(j['completed_run_ids'],['saved-case'])
   second=jobs.retry(first['id']);self.assertNotEqual(first['id'],second['id']);self.assertEqual(second['retry_of'],first['id']);self.assertEqual(self.wait(jobs,second['id'])['state'],'completed')
   restored=Jobs(tmp,run,remote=lambda *a:{});self.assertEqual(restored.get(first['id'])['state'],'cancelled')
 def test_late_cancel_does_not_hide_committed_result(self):
  gate=threading.Event();ready=threading.Event()
  def run(*args):ready.set();gate.wait(2);return {'run_id':'committed'}
  with tempfile.TemporaryDirectory() as tmp:
   jobs=Jobs(tmp,run,remote=lambda *a:{});j=jobs.start('vortex');ready.wait(2);jobs.cancel(j['id']);gate.set();done=self.wait(jobs,j['id']);self.assertEqual(done['state'],'completed');self.assertEqual(done['result']['run_id'],'committed');self.assertFalse(jobs.cancel(j['id'])['cancel_accepted'])
 def test_restart_marks_active_jobs_interrupted_and_preserves_recipe(self):
  import uuid
  with tempfile.TemporaryDirectory() as tmp:
   i=str(uuid.uuid4());p=Path(tmp)/(i+'.json');p.write_text(json.dumps({'id':i,'kind':'vortex','parent_id':None,'options':{},'state':'running','stage':'solver','created_at':1,'completed_run_ids':['saved']}));jobs=Jobs(tmp,lambda *a:{},remote=lambda *a:{});j=jobs.get(i);self.assertEqual(j['state'],'interrupted');self.assertEqual(j['completed_run_ids'],['saved']);self.assertEqual(json.loads(p.read_text())['state'],'interrupted')
 def test_validation_rejects_unbounded_or_unknown_recipes(self):
  import uuid
  for kind,parent,options in [('unknown',None,{}),('vortex',None,{'anything':1}),('flow',str(uuid.uuid4()),{'mesh_name':[]}),('joint','bad',{})]:
   with self.assertRaises((ValueError,TypeError)):validate(kind,parent,options)
 def test_cancel_kills_solver_process_group_and_does_not_run_next_stage(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);ready=root/'ready';late=root/'late';control=Control();errors=[]
   child="import time,pathlib;time.sleep(1);pathlib.Path("+repr(str(late))+").write_text('orphan')"
   code="import subprocess,sys,time,pathlib;subprocess.Popen([sys.executable,'-c',"+repr(child)+"]);pathlib.Path("+repr(str(ready))+").write_text('ready');time.sleep(10)"
   def run():
    try:
     with using(control):run_logged([sys.executable,'-c',code],root,'solver',5)
    except Cancelled:errors.append('cancelled')
   thread=threading.Thread(target=run);thread.start();end=time.monotonic()+2
   while not ready.exists() and time.monotonic()<end:time.sleep(.01)
   self.assertTrue(ready.exists());control.event.set();thread.join(3);self.assertFalse(thread.is_alive());self.assertEqual(errors,['cancelled']);time.sleep(1.1);self.assertFalse(late.exists())
 def test_failure_is_retryable_but_success_is_not(self):
  def fail(*a):raise ValueError('bounded failure')
  with tempfile.TemporaryDirectory() as tmp:
   jobs=Jobs(tmp,fail,remote=lambda *a:{});j=jobs.start('vortex');self.assertEqual(self.wait(jobs,j['id'])['state'],'failed');self.assertEqual(self.wait(jobs,jobs.retry(j['id'])['id'])['error'],'bounded failure')
 def test_malformed_history_cannot_break_new_jobs(self):
  import uuid
  with tempfile.TemporaryDirectory() as tmp:
   i=str(uuid.uuid4());(Path(tmp)/(i+'.json')).write_text(json.dumps({'id':i,'kind':'vortex'}));jobs=Jobs(tmp,lambda *a:{'run_id':'ok'},remote=lambda *a:{});self.assertEqual(jobs.list(),[]);j=jobs.start('vortex');self.assertEqual(self.wait(jobs,j['id'])['state'],'completed')
 def test_three_mesh_retry_reuses_verified_sources_without_solver(self):
  from unittest.mock import patch
  from kcee.flow_refinement import run_refinement
  sources=[{'run_id':mesh,'flow':{}} for mesh in ('coarse','medium','fine')]
  with patch('kcee.flow_sources.reusable',side_effect=sources) as reuse,patch('kcee.flow_refinement.run_bracket_flow') as solver,patch('kcee.flow_refinement.save_comparison',return_value='report') as save:
   self.assertEqual(run_refinement('/unused','parent',{},object()),'report');solver.assert_not_called();self.assertEqual(reuse.call_count,3);self.assertEqual(save.call_args.args[-1],sources)
