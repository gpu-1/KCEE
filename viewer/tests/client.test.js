import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {artifactUrl,loadRun,request,verifiedBytes} from '../client.js';
const id='12345678-1234-1234-1234-123456789abc';
const result=JSON.stringify({validation_status:'unvalidated_analytical_screening'}),stl='solid example';
const hash=text=>createHash('sha256').update(text).digest('hex');
function mock(t,alter={}){
 const routes={
  [`/api/runs/${id}`]:{id,validation_status:'unvalidated_analytical_screening',manifest:{run_id:id,artifacts:{'bracket.stl':hash(stl),'result.json':hash(result)}}},
  [`/api/runs/${id}/verify`]:{integrity:'verified',run_id:id},
  [artifactUrl(id,'bracket.stl')]:stl,[artifactUrl(id,'result.json')]:result,...alter};
 t.mock.method(globalThis,'fetch',async(path,options)=>{if(options?.signal?.aborted)throw new DOMException('Aborted','AbortError');const value=routes[path];if(value instanceof Response)return value;return new Response(typeof value==='string'?value:JSON.stringify(value));});
}
test('loads only independently hashed geometry and results',async t=>{mock(t);const data=await loadRun(id);assert.equal(new TextDecoder().decode(data.stl),stl);assert.equal(data.result.validation_status,'unvalidated_analytical_screening');});
test('rejects changed geometry after server verification',async t=>{mock(t,{[artifactUrl(id,'bracket.stl')]:'changed'});await assert.rejects(loadRun(id),/integrity check failed/);});
test('rejects failed server verification',async t=>{mock(t,{[`/api/runs/${id}/verify`]:new Response(JSON.stringify({detail:'Artifact hash mismatch'}),{status:409})});await assert.rejects(loadRun(id),error=>error.status===409);});
test('preserves retained run identity in failed registration',async t=>{t.mock.method(globalThis,'fetch',async()=>new Response(JSON.stringify({detail:{message:'Registration failed',run_id:id}}),{status:503}));await assert.rejects(request('/runs/bracket'),error=>error.detail.run_id===id);});
test('rejects unsafe artifact paths',()=>{assert.throws(()=>artifactUrl('../bad','result.json'));assert.throws(()=>artifactUrl(id,'../secret'));});
test('rejects missing hashes and cancelled requests',async t=>{mock(t);await assert.rejects(verifiedBytes(id,'bracket.stl',undefined),/Missing artifact hash/);const c=new AbortController();c.abort();await assert.rejects(loadRun(id,c.signal),error=>error.name==='AbortError');});
