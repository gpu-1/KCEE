import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {artifactUrl,loadRun,request,verifiedBytes,comparisonEvidence,comparisonMarkdown,studyMarkdown} from '../client.js';
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

test('comparison export preserves provenance, precision and limitations',()=>{
 const study={record:{id,validation_status:'pending',manifest_sha256:hash('manifest'),manifest:{run_id:id,artifacts:{'bracket.stl':hash('stl'),'fea-artifacts.zip':hash('archive')}}},result:{kind:'bracket_structural',validation_status:'pending'}};
 const values=[{measure:'Displacement',reference:.780280685488149,selected:.7835951600371827}];
 const report=JSON.parse(JSON.stringify(comparisonEvidence(study,study,values,.4247797761340433)));
 assert.equal(report.reference.solver_archive_sha256,hash('archive'));assert.deepEqual(report.measures,values);assert.equal(report.loaded_displacement_change_percent,.4247797761340433);assert.ok(report.limitations.includes('Stress peaks remain unconverged'));
 const broken=structuredClone(study);broken.record.manifest.run_id='wrong';assert.throws(()=>comparisonEvidence(broken,study,values,0),/identity/);
 const missing=structuredClone(study);missing.record.manifest_sha256=null;assert.throws(()=>comparisonEvidence(missing,study,values,0),/provenance/);
});

test('readable comparison preserves evidence and escapes table separators',()=>{
 const source={run_id:id,manifest_sha256:hash('m'),source_stl_sha256:hash('s'),solver_archive_sha256:hash('a'),validation_status:'pending'};
 const text=comparisonMarkdown({exported_at:'2026-10-13',reference:source,selected:source,measures:[{measure:'Stress | note',reference:1,selected:2}],loaded_displacement_change_percent:1,limitations:['Stress remains unconverged']});
 assert.ok(text.includes(hash('a')));assert.ok(text.includes('Stress \\| note'));assert.ok(text.includes('Stress remains unconverged'));
});

test('single-study report distinguishes recorded pass from retrospective failure',()=>{
 const study={record:{id,parent_id:id,validation_status:'pending',manifest_sha256:hash('m'),manifest:{run_id:id,artifacts:{'bracket.stl':hash('s'),'fea-artifacts.zip':hash('a')}}},result:{kind:'bracket_structural',validation_status:'pending',geometry_backend:'PicoGK',fea:{boundary:'Ideal clamp',load:'100 N',mesh_study:[],checks:{force_balance:true},stress_note:'Stress unconverged'}}};
 const text=studyMarkdown(study,{source_load_patch_agreement:false,relative_source_load_patch_area_error:.15});
 assert.ok(text.includes('force_balance: Pass'));assert.ok(text.includes('Source load-area agreement: Needs attention'));assert.ok(text.includes(hash('m')));assert.ok(text.includes('Engineering validation remains pending'));
});
