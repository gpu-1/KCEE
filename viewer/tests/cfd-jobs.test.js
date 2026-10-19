import test from 'node:test';import assert from 'node:assert/strict';
import {activeJob,jobSummary} from '../cfd-jobs.js';
test('CFD progress uses actual current-case iteration and API stage after worker finishes',()=>{
 assert.equal(activeJob({state:'cancel_requested'}),true);assert.equal(activeJob({state:'cancelled'}),false);
 assert.match(jobSummary({state:'running',stage:'solver',worker:{stage:'simpleFoam',iteration:0,iteration_target:1500}}),/0 \/ 1500/);
 assert.match(jobSummary({state:'running',stage:'verifying_solver_evidence',worker:{active:false,stage:'finished'}}),/Verifying results/);
 assert.match(jobSummary({state:'cancel_requested',stage:'solver'}),/Stopping/);
});
test('CFD job controls exist once in the website',async()=>{const {readFile}=await import('node:fs/promises');const html=await readFile(new URL('../index.html',import.meta.url),'utf8');for(const id of ['cfd-job-history','cfd-job-status','cfd-job-cancel','cfd-job-retry','cfd-job-open','cfd-job-progress','cfd-job-runs'])assert.equal(html.split('id="'+id+'"').length-1,1,id);});
