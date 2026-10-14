import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {artifactUrl,loadRun,request,verifiedBytes,comparisonEvidence,comparisonMarkdown,studyMarkdown,numericalCheckRows,voiceEvidence} from '../client.js';
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

test('missing historical numerical checks never display as passed',()=>{
 const fea={mesh_study:[{reaction_z_N:100}],checks:{force_balance:true}};
 const missing=numericalCheckRows(fea).find(row=>row.key==='load_patch_source_agreement');assert.equal(missing.verdict,'Not recorded');assert.equal(missing.value,undefined);
 fea.checks.load_patch_source_agreement=false;fea.relative_source_load_patch_area_error=.15;
 assert.equal(numericalCheckRows(fea).find(row=>row.key==='load_patch_source_agreement').verdict,'Needs attention');
});


test('study energy report retains precision and rejects missing or inconsistent evidence',()=>{
 const study={record:{id,validation_status:'pending',manifest_sha256:hash('m'),manifest:{run_id:id,artifacts:{'bracket.stl':hash('s'),'fea-artifacts.zip':hash('a')}}},result:{kind:'bracket_structural',validation_status:'pending',fea:{mesh_study:[],checks:{}}}};
 const diagnostic={source_load_patch_agreement:true,relative_source_load_patch_area_error:0,energy_consistency:{strain_energy_N_mm:39.5340784053091,half_load_work_N_mm:39.53407814206325,relative_error:6.6587071412271825e-9,relative_tolerance:.001,passes_demo_tolerance:true,method:'Linear elasticity'}};
 diagnostic.regional_refinement={mesh_study:[{target_size_mm:2.5,energy_consistency:diagnostic.energy_consistency}],last_energy_change:.025};
 const text=studyMarkdown(study,diagnostic);
 assert.ok(text.includes('Mesh target: 2.5 mm'));assert.ok(text.includes('Last strain-energy change: 2.5% (informational)'));
 assert.ok(text.includes('Energy consistency: Pass'));assert.ok(text.includes('39.5340784053091 N·mm'));assert.ok(text.includes('39.53407814206325 N·mm'));assert.ok(text.includes('not an engineering acceptance'));
 assert.ok(studyMarkdown(study).includes('Energy consistency: Not recorded'));
 diagnostic.energy_consistency.relative_error=.01;assert.ok(studyMarkdown(study,diagnostic).includes('inconsistent diagnostic verdict'));
 diagnostic.energy_consistency.passes_demo_tolerance=false;assert.ok(studyMarkdown(study,diagnostic).includes('Energy consistency: Needs attention'));
 diagnostic.energy_consistency.strain_energy_N_mm=NaN;assert.ok(studyMarkdown(study,diagnostic).includes('invalid diagnostic values'));
});


test('study export keeps exploratory evidence separate and validates source identity',()=>{
 const study={record:{id,validation_status:'pending',manifest_sha256:hash('m'),manifest:{run_id:id,artifacts:{'bracket.stl':hash('s'),'fea-artifacts.zip':hash('a')}}},result:{kind:'bracket_structural',validation_status:'pending',fea:{mesh_study:[],checks:{}}}};
 const evidence={run_id:id,manifest_sha256:hash('m'),source_stl_sha256:hash('s'),items:[{report_sha256:hash('report'),rows:[{global_target_mm:1.5,root_target_mm:.75,nodes:39447,displacement_mm:.7922995976527467,peak_stress_MPa:334.430322251212,recorded_archive_sha256:hash('archive')}]}]};
 const text=studyMarkdown(study,null,evidence);
 assert.ok(text.includes('## Separate exploratory refinement'));assert.ok(text.includes('334.430322251212'));assert.ok(text.includes(hash('report')));assert.ok(text.includes(hash('archive')));assert.ok(text.includes('recorded evidence only'));
 evidence.items[0].rows[0].archive_integrity='verified';assert.ok(studyMarkdown(study,null,evidence).includes('Verified by local API'));
 assert.ok(!studyMarkdown(study,null,{items:[]}).includes('## Separate exploratory refinement'));
 const wrong=structuredClone(evidence);wrong.source_stl_sha256=hash('other');assert.throws(()=>studyMarkdown(study,null,wrong),/source mismatch/);
 const bad=structuredClone(evidence);bad.items[0].rows[0].peak_stress_MPa=NaN;assert.throws(()=>studyMarkdown(study,null,bad),/Invalid exploration/);
});


test('voice provenance preserves exact checked audio and refuses unrelated sources',()=>{
 const study={record:{id,validation_status:'pending',manifest_sha256:hash('m'),manifest:{run_id:id,artifacts:{'bracket.stl':hash('s'),'fea-artifacts.zip':hash('a'),'voice-summary.json':hash('summary')}}},result:{kind:'bracket_structural',validation_status:'pending'}};
 const job={job_id:id,run_id:id,status:'completed',summary_sha256:hash('summary'),audio_sha256:hash('audio'),model_manifest_sha256:hash('model'),voice:'af_heart',speed:1.2,language:'en-us',sample_rate_Hz:24000};
 const evidence=voiceEvidence(study,job,hash('audio'));
 assert.equal(evidence.source.manifest_sha256,hash('m'));assert.equal(evidence.audio_sha256,hash('audio'));assert.equal(evidence.model_manifest_sha256,hash('model'));assert.equal(evidence.source.validation_status,'pending');assert.equal(evidence.voice,'af_heart');assert.equal(evidence.speed,1.2);assert.equal(evidence.language,'en-us');
 assert.throws(()=>voiceEvidence(study,job,hash('changed')),/provenance/);
 assert.throws(()=>voiceEvidence(study,{...job,summary_sha256:hash('other')},hash('audio')),/source mismatch/);
 assert.throws(()=>voiceEvidence(study,{...job,model_manifest_sha256:null},hash('audio')),/provenance/);
});
