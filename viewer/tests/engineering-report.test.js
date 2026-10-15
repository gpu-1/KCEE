import test from 'node:test';
import assert from 'node:assert/strict';
import {combinedEngineeringReport,engineeringReportMarkdown,guideCanRun} from '../engineering-report.js';
import {textHash} from '../search-export.js';
const sha='a'.repeat(64);
function study(kind,id){const physics={source_stl_sha256:sha,boundary:'Recorded boundary',load:'100 N downward',material:{youngs_modulus_MPa:69000},conductivity_W_m_K:15,stress_note:'Not converged',checks:{balance:true},mesh_study:[{tip_deflection_mm:.7,reaction_z_N:100,maximum_von_mises_MPa:217,minimum_temperature_C:20,maximum_temperature_C:80,volume_mean_temperature_C:38,hot_reaction_heat_W:1.5}]};return {record:{id,parent_id:'parent',validation_status:'numerical_only',manifest_sha256:sha,manifest:{kind,run_id:id,artifacts:{'bracket.stl':sha,'result.json':sha,'fea-artifacts.zip':sha,'thermal-artifacts.zip':sha}}},result:{kind,validation_status:'numerical_only',geometry_backend:'PicoGK',...(kind==='bracket_structural'?{fea:physics}:{thermal:physics})}};}
test('consolidated report binds both verified studies, preserves physics and hashes snapshot',async()=>{
 const s=study('bracket_structural','s'),t=study('bracket_thermal','t'),r=await combinedEngineeringReport(s,t);const {snapshot_sha256,...raw}=r;assert.equal(snapshot_sha256,await textHash(JSON.stringify(raw)));assert.equal(r.structural.source.run_id,'s');assert.equal(r.thermal.source.run_id,'t');assert.equal(r.thermal.conductivity_W_m_K,15);assert.match(engineeringReportMarkdown(r),/no thermal expansion or coupled thermal stress/);assert.match(engineeringReportMarkdown(r),/217 MPa/);s.result.fea.checks.balance=false;assert.equal(r.structural.checks.balance,true);
});
test('unrelated geometry, missing provenance and wrong physics cannot produce a report',async()=>{
 const s=study('bracket_structural','s'),t=study('bracket_thermal','t');t.result.thermal.source_stl_sha256='b'.repeat(64);t.record.manifest.artifacts['bracket.stl']='b'.repeat(64);await assert.rejects(combinedEngineeringReport(s,t),/same STL/);t.record.manifest.artifacts['bracket.stl']=sha;await assert.rejects(combinedEngineeringReport(s,t),/geometry mismatch/);await assert.rejects(combinedEngineeringReport(t,s),/identity/);
});
test('guided runs require a native selection and a supported sequence',()=>{
 assert.equal(guideCanRun(null,'both'),false);assert.equal(guideCanRun(study('bracket_thermal','t'),'both'),false);const s=study('bracket_structural','s');assert.equal(guideCanRun(s,'both'),true);s.result.geometry_backend='mesh';assert.equal(guideCanRun(s,'structural'),false);
});
