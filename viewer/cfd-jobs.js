import {request} from './client.js';
const titles={flow:'Bracket flow',refinement:'Mesh refinement',domains:'Boundary distances',combined:'CFD verification',local:'Wake & below',reference:'Pressure study',joint:'Meshes & domains',vortex:'Vortex benchmark'};
const stages={solver:'Running CFD',surfaceCheck:'Checking surface',blockMesh:'Preparing mesh',snappyHexMesh:'Refining mesh',checkMesh:'Checking mesh',simpleFoam:'Solving',icoFoam:'Solving',postprocessing:'Processing fields',verifying_solver_evidence:'Verifying results',verifying_sources:'Verifying saved cases'};
export const activeJob=job=>['queued','running','cancel_requested'].includes(job?.state);
export function jobSummary(job){
 const worker=job.worker,stage=job.state==='cancel_requested'?'Stopping at a safe stage…':worker?.active===false?job.stage:worker?.stage||job.stage;
 const iteration=Number.isFinite(worker?.iteration)&&Number.isFinite(worker?.iteration_target)?` · ${worker.iteration} / ${worker.iteration_target} ${worker.progress_unit||'iterations'}`:'';
 const state=job.state.replaceAll('_',' '),label=stages[stage]||String(stage).replaceAll('_',' ');
 return `${state}${label===state?'':' · '+label}${iteration}`;
}
export function mountCfdJobs({busy,completed}){
 const $=id=>document.getElementById(id);let selected=null,timer=null,mutation=false,serial=0,delivered=new Set(),runningId=null;
 const schedule=()=>{clearTimeout(timer);timer=setTimeout(()=>poll(),1500);};
 function render(job){
  selected=job;$('cfd-job-status').textContent=jobSummary(job);$('cfd-job-error').textContent=job.error||'';$('cfd-job-details').textContent=[titles[job.kind]||job.kind,job.mesh,job.domain,job.worker?.case].filter(Boolean).join(' · ');$('cfd-job-cancel').disabled=mutation||!activeJob(job)||job.state==='cancel_requested';$('cfd-job-retry').disabled=mutation||!['failed','cancelled','interrupted'].includes(job.state);$('cfd-job-open').disabled=!job.result?.run_id;$('cfd-job-runs').replaceChildren();
  for(const id of job.completed_run_ids||[]){const b=document.createElement('button');b.textContent='Open saved case '+id.slice(0,8);b.onclick=()=>completed({run_id:id});$('cfd-job-runs').append(b);}
  const w=job.worker,p=$('cfd-job-progress');if(activeJob(job)&&['simpleFoam','icoFoam'].includes(w?.stage)&&Number.isFinite(w.iteration)&&Number.isFinite(w.iteration_target)){p.hidden=false;p.max=w.iteration_target;p.value=Math.min(w.iteration,w.iteration_target);p.setAttribute('aria-label','Current case solver progress');}else p.hidden=true;
 }
 async function history(preferred){
  const data=await request('/cfd-jobs');$('cfd-job-history').replaceChildren();for(const j of data.items){const o=document.createElement('option');o.value=j.id;o.textContent=(titles[j.kind]||j.kind)+' · '+j.state.replaceAll('_',' ')+' · '+j.id.slice(0,8);$('cfd-job-history').append(o);}
  const running=data.items.find(activeJob);runningId=running?.id;busy(Boolean(running));const id=preferred||running?.id||data.items[0]?.id;if(id){$('cfd-job-history').value=id;return id;}return null;
 }
 async function poll(){
  if(!selected)return;const ticket=++serial,id=selected.id;
  try{const job=await request('/cfd-jobs/'+id);if(ticket!==serial)return;render(job);await history(id);if(activeJob(job)||runningId)schedule();if(!activeJob(job)&&job.state==='completed'&&!delivered.has(id)){delivered.add(id);await completed(job.result);}}
  catch(error){$('cfd-job-error').textContent='Status unavailable. Reconnecting… '+error.message;schedule();}
 }
 async function choose(id){++serial;clearTimeout(timer);selected={id};await poll();}
 async function mutate(action){if(mutation)return;mutation=true;let failure=null;try{const job=await action();render(job);await history(job.id);schedule();}catch(error){failure=error.message;}finally{mutation=false;if(selected?.state)render(selected);if(failure)$('cfd-job-error').textContent=failure;}}
 $('cfd-job-cancel').onclick=()=>selected&&mutate(()=>request('/cfd-jobs/'+selected.id+'/cancel',{method:'POST'}));
 $('cfd-job-retry').onclick=()=>selected&&mutate(()=>request('/cfd-jobs/'+selected.id+'/retry',{method:'POST'}));
 $('cfd-job-open').onclick=()=>selected?.result&&completed(selected.result);
 $('cfd-job-history').onchange=()=>choose($('cfd-job-history').value);
 $('cfd-job-refresh').onclick=async()=>{try{const id=await history();if(id)await choose(id);}catch(e){$('cfd-job-error').textContent=e.message;}};
 async function start(kind,parent=null,options={}){if(mutation)return;busy(true);await mutate(()=>request('/cfd-jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,parent_id:parent,options})}));if(!selected||!activeJob(selected))await history();}
 (async()=>{try{const id=await history();if(id){const initial=await request('/cfd-jobs/'+id);if(!activeJob(initial))delivered.add(id);await choose(id);}}catch(e){busy(false);$('cfd-job-error').textContent='CFD job status unavailable: '+e.message;}})();
 return {start};
}
