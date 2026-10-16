import {samplingLabel} from './flow-sampling-view.js';
import {mountPressure} from './flow-pressure-view.js';
import {mountCombined} from './flow-combined-view.js';
import {mountDomainView} from './flow-domain-view.js';
import {flowPoints} from './bracket-flow-view.js';
import {convergenceSeries,drawConvergence} from './vortex-convergence.js';
import {drawVortex} from './vortex-view.js';
import {cfdComparison,cfdComparisonMarkdown} from './cfd-comparison.js';
import {drawCFDChart} from './cfd-chart.js';
import {installEngineeringWorkflow} from './engineering-workflow.js';
import {verifyAssistantEvidence} from './assistant-evidence.js';
import './search-page-filter-ui.js';
import './saved-searches-ui.js';
import './backup-status-ui.js';
import {handoffSources,scopeRequest,scopeMatches,answerScopes,scopeDescription} from './assistant-scope.js';
import {appendPdfPageLink} from './pdf-source.js';
import './knowledge-ui.js';
import {drawThermalChart} from './thermal-chart.js';
import * as THREE from 'three';
import {STLLoader} from 'three/addons/loaders/STLLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {request, loadRun, artifactUrl, comparisonEvidence, comparisonMarkdown, studyMarkdown, numericalCheckRows, voiceEvidence} from './client.js';
const $=id=>document.getElementById(id);
let assistantDocumentScope=[];let workflowStudy=null;
function resetAssistantScope(){assistantDocumentScope=[];$('assistant-document-scope').textContent='Reference scope: all active documents.';$('assistant-all-documents').hidden=true;}
$('assistant-all-documents').onclick=()=>{if(!assistantBusy)resetAssistantScope();};
$('assistant-documents').onchange=()=>{if(!$('assistant-documents').checked)resetAssistantScope();};
const structuralBoundaryLegend=$("boundary-legend").textContent;
let studyReportUrl=null,assistantEvidenceUrl=null,assistantTextUrl=null;
function clearAssistantExport(){$("assistant-documents-note").textContent="";$("assistant-document-citations").replaceChildren();if(assistantTextUrl)URL.revokeObjectURL(assistantTextUrl);assistantTextUrl=null;$("download-assistant-text").removeAttribute("href");if(assistantEvidenceUrl)URL.revokeObjectURL(assistantEvidenceUrl);assistantEvidenceUrl=null;$("assistant-downloads").hidden=true;$("download-assistant").removeAttribute("href");$("assistant-evidence-text").value="";$("assistant-evidence-view").open=false;}
let comparisonId=null,currentStudy=null,comparisonUrl=null,comparisonMarkdownUrl=null;
function clearComparisonExport(){if(comparisonMarkdownUrl)URL.revokeObjectURL(comparisonMarkdownUrl);comparisonMarkdownUrl=null;$("download-comparison-markdown").removeAttribute("href");$("comparison-markdown").value="";$("comparison-markdown-view").open=false;if(comparisonUrl)URL.revokeObjectURL(comparisonUrl);comparisonUrl=null;$("comparison-json").value="";$("comparison-json-view").open=false;$("download-comparison").removeAttribute("href");}
let selectedIsThermal=false;
let fieldData=null, sourceStl=null, archiveDigest=null;
let flowCloud=null,flowSourceId=null;
let mesh, renderer, controls, camera, scene, boundaryMarkers;
let modelCenter=new THREE.Vector3(),isBracketStudy=false;
let pendingRemoval=null,removing=false,selectedVerified=false;
let selection=0, activeRequest, listRequest, offset=0, selectedId=null;
const PAGE_SIZE=10;
let assistantAvailable=false,assistantBusy=false,assistantRequest=null,assistantStatusPinned=false;
let serviceBusy=false,controlAvailable=false,voiceAvailable=false,voiceBusy=false,voiceRequest=null,voiceUrl=null,voiceEvidenceUrl=null;
let nativeAvailable=false,creating=false,structuralAvailable=false,thermalAvailable=false,cfdAvailable=false,vortexAvailable=false,bracketFlowAvailable=false,selectedIsNative=false;
function updateServiceButtons(){$("toggle-ai").disabled=!controlAvailable || serviceBusy || assistantBusy || creating;$("toggle-ai").textContent=assistantAvailable?"Stop":"Start";$("toggle-ai").setAttribute("aria-label",assistantAvailable?"Stop local AI":"Start local AI");$("toggle-voice").disabled=!controlAvailable || serviceBusy || voiceBusy || creating;$("toggle-voice").textContent=voiceAvailable?"Stop":"Start";$("toggle-voice").setAttribute("aria-label",voiceAvailable?"Stop local voice":"Start local voice");$("start-services").disabled=!controlAvailable || serviceBusy || creating || (nativeAvailable && structuralAvailable && thermalAvailable && cfdAvailable);$("stop-services").disabled=!controlAvailable || serviceBusy || creating || (!nativeAvailable && !structuralAvailable && !thermalAvailable && !cfdAvailable);}
function updateCreation(){$('verify-flow-combined').disabled=creating||serviceBusy||!bracketFlowAvailable||!flowSourceId;$('verify-flow-domain').disabled=creating||serviceBusy||!bracketFlowAvailable||!flowSourceId;$('verify-bracket-flow').disabled=creating||serviceBusy||!bracketFlowAvailable||!flowSourceId;$('analyze-flow').disabled=creating||serviceBusy||!bracketFlowAvailable||!selectedIsNative;$('run-cfd-vortex').disabled=creating||serviceBusy||!vortexAvailable;for(const id of ['cfd-gap','cfd-gradient','cfd-viscosity','cfd-density','cfd-length','cfd-reset'])$(id).disabled=creating||serviceBusy;$('run-cfd-benchmark').disabled=creating||serviceBusy||!cfdAvailable;$("assistant-all-documents").disabled=assistantBusy || serviceBusy || !currentStudy;$("assistant-documents").disabled=assistantBusy || serviceBusy || !currentStudy;$("analyze-thermal").disabled=creating || serviceBusy || !structuralAvailable || !selectedIsNative;$("thermal-benchmark").disabled=creating || serviceBusy || !thermalAvailable; updateServiceButtons();for(const id of ["question-displacement","question-stress","question-refinement"])$(id).disabled=assistantBusy || !currentStudy;$("ask-assistant").disabled=!assistantAvailable || assistantBusy || serviceBusy || !currentStudy;$("prepare-voice").disabled=!voiceAvailable || voiceBusy || serviceBusy || !currentStudy; $("remove-run").disabled=(creating || serviceBusy) || removing || !selectedVerified; $("fea").disabled=(creating || serviceBusy) || !structuralAvailable; $("analyze").disabled=(creating || serviceBusy) || !structuralAvailable || !selectedIsNative; $("create").disabled=(creating || serviceBusy) || ($("backend").value==="picogk" && !nativeAvailable); }
$("backend").onchange=updateCreation;
function badge(id,text,kind=''){ $(id).textContent=text; $(id).className='badge '+kind; }
function clearModel(){if(flowCloud){scene.remove(flowCloud);flowCloud.geometry.dispose();flowCloud.material.dispose();flowCloud=null;}if(boundaryMarkers){scene.remove(boundaryMarkers);boundaryMarkers.traverse(object=>{object.geometry?.dispose();if(Array.isArray(object.material))object.material.forEach(m=>m.dispose());else object.material?.dispose();});boundaryMarkers=null;} if(mesh){scene.remove(mesh);mesh.geometry.dispose();mesh.material.dispose();mesh=null;} $('empty').hidden=false; $('fit').disabled=true; $('wireframe').disabled=true; }
function configureAssistantQuestions(thermal){$("question-displacement").textContent=thermal?"Temperatures":"Displacement";$("question-stress").textContent=thermal?"Heat balance":"Stress convergence";$("question-refinement").textContent="Refinement";}
function clearDetails(){$('flow-sampling-note').hidden=true;$('flow-sampling-note').textContent='';$('flow-pressure-results').hidden=true;$('pressure-sampling').onchange=null;$('pressure-sampling').value='production';$('pressure-probe').onchange=null;$('pressure-probe').replaceChildren();$('pressure-probes').replaceChildren();for(const id of ['pressure-mesh-chart','pressure-bore-chart','pressure-cases','pressure-checks'])$(id).replaceChildren();for(const id of ['pressure-csv','pressure-json'])$(id).removeAttribute('href');$('flow-combined-results').hidden=true;for(const id of ['combined-mesh-chart','combined-domain-chart','combined-meshes','combined-checks','combined-probe','combined-probes'])$(id).replaceChildren();$('combined-probe').onchange=null;$('combined-open-domain').onclick=null;for(const id of ['combined-csv','combined-json'])$(id).removeAttribute('href');$('flow-domain-results').hidden=true;for(const id of ['domain-cases','domain-checks','domain-probes','domain-probe'])$(id).replaceChildren();$('domain-probe').onchange=null;for(const id of ['domain-csv','domain-json'])$(id).removeAttribute('href');$('flow-position-audit').hidden=true;$('flow-position-audit-values').replaceChildren();flowSourceId=null;$('flow-refinement-results').hidden=true;for(const id of ['flow-refinement-meshes','flow-refinement-bores','flow-refinement-changes','flow-refinement-probe','flow-refinement-probes','flow-bore-rows'])$(id).replaceChildren();$('flow-refinement-probe').onchange=null;$('flow-bore-note').textContent='';for(const id of ['flow-refinement-csv','flow-refinement-json'])$(id).removeAttribute('href');$('bracket-flow-results').hidden=true;$('bracket-flow-checks').replaceChildren();$('bracket-flow-legend').textContent='';for(const id of ['bracket-flow-csv','bracket-flow-json','bracket-flow-archive'])$(id).removeAttribute('href');$('bracket-flow-quantity').onchange=null;$('bracket-flow-window').onchange=null;$('vortex-results').hidden=true;$('vortex-view').replaceChildren();$('vortex-rows').replaceChildren();$('vortex-checks').replaceChildren();$('vortex-grid').replaceChildren();for(const id of ['vortex-spatial-chart','vortex-time-chart','vortex-time-summary','vortex-time-rows'])$(id).replaceChildren();$('vortex-verification-csv').hidden=true;for(const id of ['vortex-study','vortex-grid','vortex-quantity','vortex-mesh'])$(id).onchange=null;for(const id of ['vortex-csv','vortex-archive','vortex-verification-csv','vortex-json'])$(id).removeAttribute('href');$('cfd-results').hidden=true;$('cfd-chart').replaceChildren();$('cfd-mesh-select').replaceChildren();$('cfd-mesh-select').onchange=null;$('cfd-mesh-rows').replaceChildren();$('cfd-check-values').replaceChildren();$('cfd-profile').removeAttribute('href');$('cfd-json').removeAttribute('href');workflowStudy=null;document.dispatchEvent(new Event('kcee-study-change'));resetAssistantScope();$("assistant-documents").checked=false;configureAssistantQuestions(false);$("boundary-toggle-label").textContent="Load & support";$("boundary-legend").textContent=structuralBoundaryLegend;selectedIsThermal=false;$("bracket-thermal-results").hidden=true;$("bracket-thermal-checks").replaceChildren();$("bracket-thermal-rows").replaceChildren();$("bracket-thermal-csv").removeAttribute("href");$("thermal-checks").replaceChildren();$("thermal-charts").replaceChildren();$("thermal-mesh").replaceChildren();$("thermal-mesh").onchange=null;$("thermal-results").hidden=true;$("thermal-rows").replaceChildren();$("thermal-profile").removeAttribute("href");clearAssistantExport();assistantRequest?.abort();assistantRequest=null;assistantBusy=false;assistantStatusPinned=false;$("study-assistant").hidden=true;$("assistant-answer").textContent="";$("assistant-sources").textContent="";$("assistant-question").value="";if(voiceEvidenceUrl)URL.revokeObjectURL(voiceEvidenceUrl);voiceEvidenceUrl=null;$("download-voice-evidence").removeAttribute("href");$("voice-evidence-text").value="";$("voice-evidence-view").open=false;$("voice-downloads").hidden=true;$("download-voice").removeAttribute("href");voiceRequest?.abort();voiceRequest=null;voiceBusy=false;$("voice-audio").pause();$("voice-audio").removeAttribute("src");$("voice-audio").load();$("voice-audio").hidden=true;if(voiceUrl)URL.revokeObjectURL(voiceUrl);voiceUrl=null;$("prepare-voice").disabled=true;$("refinement-explorations").hidden=true;$("exploration-rows").replaceChildren();$("exploration-evidence").value="";if(studyReportUrl)URL.revokeObjectURL(studyReportUrl);studyReportUrl=null;$("readable-study").hidden=true;$("study-report-text").value="";$("study-report-view").open=false;$("download-study-report").removeAttribute("href");clearComparisonExport();currentStudy=null;$('pin-comparison').disabled=true;$('comparison').hidden=true;$('comparison-rows').replaceChildren();$('stress-diagnostics').hidden=true;$('hotspot-values').replaceChildren();$('geometry-measurements').hidden=true;$('hole-values').replaceChildren();selectedVerified=false;$('remove-run').disabled=true;isBracketStudy=false;$("boundaries").checked=false;$("boundaries").disabled=true;$("boundary-legend").hidden=true;fieldData=null;sourceStl=null;archiveDigest=null;$('field').checked=false;$('field').disabled=true;$('scale-label').hidden=true;$('quantity-label').hidden=true;$('field-legend').hidden=true; selectedIsNative=false;$("analyze").disabled=true; $('result-title').textContent='Screening result';$('mesh-study').hidden=true;$('mesh-rows').replaceChildren();$('validation-checks').hidden=true;$('check-values').replaceChildren(); $('result').hidden=true;$('result-empty').hidden=false;$('metrics').replaceChildren();$('provenance').replaceChildren();$('assumptions').replaceChildren();$('solver-files').hidden=true;$('solver-files').removeAttribute('href');for(const id of ['report','manifest'])$(id).removeAttribute('href'); }
function beginSelection(){ selection++;activeRequest?.abort();activeRequest=new AbortController();clearModel();clearDetails();return {ticket:selection,signal:activeRequest.signal}; }
function addMetric(list,label,value){ const dt=document.createElement('dt'), dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;$(list).append(dt,dd); }
function fitModel(){
  if(!mesh)return;const r=Math.max(mesh.geometry.boundingSphere.radius,flowCloud?flowCloud.geometry.boundingSphere.radius+flowCloud.geometry.boundingSphere.center.length():0);
  camera.near=Math.max(r/1000,.001);camera.far=r*100;
  const halfAngle=Math.min(camera.fov*Math.PI/360,Math.atan(Math.tan(camera.fov*Math.PI/360)*camera.aspect));
  camera.position.copy(new THREE.Vector3(1,.8,1).normalize().multiplyScalar(r/Math.sin(halfAngle)*1.15));
  camera.updateProjectionMatrix();controls.target.set(0,0,0);controls.update();
}
$('fit').onclick=fitModel;
$('wireframe').onchange=()=>{if(mesh)mesh.material.wireframe=$('wireframe').checked;};
function displayGeometry(bytes){
  if(!renderer) throw new Error('3D rendering unavailable on this browser.');
  const geometry=new STLLoader().parse(bytes);const positions=geometry.attributes.position?.array;
  if(!positions?.length || positions.length%9 || !positions.every(Number.isFinite)){geometry.dispose();throw new Error('STL contains invalid geometry');}
  geometry.computeVertexNormals();geometry.computeBoundingBox();geometry.boundingBox.getCenter(modelCenter);geometry.center();geometry.computeBoundingSphere();const r=geometry.boundingSphere.radius;
  if(!Number.isFinite(r)||r<=0){geometry.dispose();throw new Error('STL has no usable extent');}
  mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:0x69cabc,roughness:.5,wireframe:$('wireframe').checked}));scene.add(mesh);
  fitModel();$('fit').disabled=false;$('wireframe').disabled=false;$('empty').hidden=true;updateBoundaries();
}
try {
  scene=new THREE.Scene();scene.add(new THREE.HemisphereLight(0xffffff,0x446079,3));
  const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(100,150,100);scene.add(light);
  camera=new THREE.PerspectiveCamera(45,1,.1,10000);camera.up.set(0,0,1);camera.position.set(100,100,100);
  renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));$('viewport').appendChild(renderer.domElement);
  controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
  new ResizeObserver(()=>{const width=$('viewport').clientWidth,height=$('viewport').clientHeight;if(width<=0||height<=0)return;renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();}).observe($('viewport'));
  renderer.setAnimationLoop(()=>{if($('design-workspace').hidden)return;controls.update();renderer.render(scene,camera);});
} catch {renderer=null;$('empty').textContent='3D rendering unavailable. Run history and reports remain accessible.';}
function highlight(){for(const button of $('runs').querySelectorAll('button'))button.setAttribute('aria-current',String(button.dataset.id===selectedId));}
async function selectRun(id){
  let sourceLoadWarning=false,verifiedDiagnostic=null,verifiedExploration=null;
  const {ticket,signal}=beginSelection();selectedId=id;highlight();$('model-title').textContent='Bracket '+id.slice(0,8);badge('integrity','Verifying…');$('status').textContent='Checking provenance and downloading geometry…';
  try {
    const {record,result,stl}=await loadRun(id,signal);if(ticket!==selection)return;
    $('model-title').textContent=(result.kind==='bracket_flow_pressure'?'Bore pressure ':result.kind==='bracket_flow_combined'?'CFD verification ':result.kind==='bracket_flow_domain'?'Flow domain ':result.kind==='bracket_flow_refinement'?'Flow verification ':result.kind==='bracket_flow'?'Bracket flow ':result.kind==='cfd_vortex'?'OpenFOAM vortex ':result.kind==='cfd_benchmark'?'CFD channel ':result.kind==='bracket_thermal'?'Bracket thermal ':result.kind==='thermal_benchmark'?'Thermal benchmark ':result.kind==='structural_benchmark'?'Cantilever benchmark ':result.kind==='bracket_structural'?'Bracket FEA ':'Bracket ')+id.slice(0,8);
    const samplingText=samplingLabel(result);$('flow-sampling-note').textContent=samplingText;$('flow-sampling-note').hidden=!samplingText;
    workflowStudy={id,record,result};document.dispatchEvent(new Event('kcee-study-change'));selectedVerified=true;$('remove-run').disabled=(creating || serviceBusy) || removing;$('remove-run').textContent=$('show-removed').checked?'Restore to list':'Remove from list';
    if(result.kind==='bracket_flow_pressure'){
      const data=result.pressure_study;flowSourceId=record.parent_id;$('result-title').textContent='Bore pressure sensitivity verification';$('flow-pressure-results').hidden=false;if(renderer)displayGeometry(stl);mountPressure(data,selectRun);
      for(const text of data.limits){const li=document.createElement('li');li.textContent=text;$('assumptions').append(li);}for(const [label,value] of [['Run ID',id],['Source parent',record.parent_id],['Source STL SHA-256',data.source_stl_sha256],['Manifest SHA-256',record.manifest_sha256]])addMetric('provenance',label,value);
      $('pressure-csv').href=artifactUrl(id,'verification.csv');$('pressure-json').href=artifactUrl(id,'result.json');$('report').href=artifactUrl(id,'report.md');$('manifest').href=artifactUrl(id,'manifest.json');$('result').hidden=false;$('result-empty').hidden=true;badge('integrity','Artifacts verified','good');$('status').textContent='Matched bore-refinement evidence recorded. Review pressure changes and partial native audit coverage; mesh independence is unestablished.';updateCreation();return;
    }
    if(result.kind==='bracket_flow_combined'){
      const data=result.combined_flow;flowSourceId=record.parent_id;$('result-title').textContent='Combined CFD mesh and domain verification';$('flow-combined-results').hidden=false;if(renderer)displayGeometry(stl);mountCombined(data,selectRun);
      for(const text of data.limits){const li=document.createElement('li');li.textContent=text;$('assumptions').append(li);}for(const [label,value] of [['Run ID',id],['Source parent',record.parent_id],['Source STL SHA-256',data.source_stl_sha256],['Domain report manifest SHA-256',data.domain_comparison.manifest_sha256],['Manifest SHA-256',record.manifest_sha256]])addMetric('provenance',label,value);
      $('combined-csv').href=artifactUrl(id,'verification.csv');$('combined-json').href=artifactUrl(id,'result.json');$('report').href=artifactUrl(id,'report.md');$('manifest').href=artifactUrl(id,'manifest.json');$('result').hidden=false;$('result-empty').hidden=true;badge('integrity','Artifacts verified','good');$('status').textContent='Combined far-domain mesh and medium-resolution boundary evidence recorded. Joint independence remains unestablished.';updateCreation();return;
    }
    if(result.kind==='bracket_flow_domain'){
      const data=result.domain_study;flowSourceId=record.parent_id;$('result-title').textContent='Bracket-flow boundary-distance study';$('flow-domain-results').hidden=false;if(renderer)displayGeometry(stl);mountDomainView(data,selectRun);
      for(const text of data.limits){const li=document.createElement('li');li.textContent=text;$('assumptions').append(li);}for(const [label,value] of [['Run ID',id],['Source parent',record.parent_id],['Source STL SHA-256',data.source_stl_sha256],['Manifest SHA-256',record.manifest_sha256]])addMetric('provenance',label,value);
      $('domain-csv').href=artifactUrl(id,'verification.csv');$('domain-json').href=artifactUrl(id,'result.json');$('domain-json').download='kcee-domain-'+id.slice(0,8)+'.json';$('report').href=artifactUrl(id,'report.md');$('manifest').href=artifactUrl(id,'manifest.json');$('result').hidden=false;$('result-empty').hidden=true;badge('integrity','Artifacts verified','good');$('status').textContent='Three boundary distances compared at fixed medium background spacing. Review referenced pressure changes; domain independence is not established.';updateCreation();return;
    }
    if(result.kind==='bracket_flow_refinement'){
      const summary=result.flow_refinement;$('flow-refinement-pressure-label').textContent=summary.schema==='kcee.bracket-flow-refinement.v4'?'(p−p upstream)/ρ (m²/s²)':'p/ρ (m²/s²)';$('flow-interpolation-note').textContent=['kcee.bracket-flow-refinement.v2','kcee.bracket-flow-refinement.v3'].includes(summary.schema)?'Values are interpolated at identical requested coordinates using positive weights from four wall-visible cells. Support radius is the furthest supporting cell location. These locations are mesh-vertex averages, not exact volume centroids. Velocity changes use the 0.01 m/s inlet; pressure changes use 0.5 U² = 0.00005 m²/s². Changes are sensitivity measures, not analytical errors.':'Historical comparison: nearest-cell values at different sample locations. The last column shows the sample offset. Velocity and pressure changes also reflect those offsets.';if(['kcee.bracket-flow-refinement.v3','kcee.bracket-flow-refinement.v4'].includes(summary.schema)){$('flow-interpolation-note').textContent='Values are interpolated at identical coordinates from independently reconstructed volume centroids of triangulated saved cells. Four wall-visible supports use positive weights. Support radius is the furthest support. These are custom interpolation and cell-center reconstructions, not OpenFOAM native sampling. Velocity changes use the 0.01 m/s inlet; pressure changes use 0.5 U² = 0.00005 m²/s². Changes are sensitivity measures, not analytical errors.';$('flow-position-audit').hidden=false;for(const row of summary.studies){const a=row.cell_position_audit,changes=row.sampling_audit?.probe_changes??[];if(a){addMetric('flow-position-audit-values',row.mesh_name+' · max cell-center shift',(a.maximum_vertex_mean_to_volume_centroid_m*1000).toFixed(4)+' mm');addMetric('flow-position-audit-values',row.mesh_name+' · RMS cell-center shift',(a.rms_vertex_mean_to_volume_centroid_m*1000).toFixed(4)+' mm');}const valid=changes.filter(p=>p.available);if(valid.length)addMetric('flow-position-audit-values',row.mesh_name+' · max pressure change from position basis',(Math.max(...valid.map(p=>p.pressure_change_normalized_by_inlet_dynamic_scale))*100).toFixed(4)+'% of inlet dynamic scale');addMetric('flow-position-audit-values',row.mesh_name+' · auditable probes',valid.length+' / '+changes.length);}}if(summary.schema==='kcee.bracket-flow-refinement.v4')$('flow-interpolation-note').textContent+=' Compact v1 selects the minimum support radius in its candidate pool. New pressure changes subtract the fixed upstream probe within each case.';flowSourceId=record.parent_id;$('result-title').textContent='Bracket-flow mesh and bore verification';$('flow-refinement-results').hidden=false;if(renderer)displayGeometry(stl);
      for(const row of summary.studies){const tr=document.createElement('tr');for(const value of [row.mesh_name,row.cells,(row.nominal_near_surface_cell_m*1000).toFixed(4),(Object.values(row.solver_checks).every(Boolean)?'Pass':'Attention')+' / '+(row.bore_verification.all_pass?'Pass':'Attention')]){const td=document.createElement('td');td.textContent=value;tr.append(td);}const td=document.createElement('td'),button=document.createElement('button');button.textContent='Open';button.onclick=()=>selectRun(row.run_id);td.append(button);tr.append(td);$('flow-refinement-meshes').append(tr);
      for(const h of row.bore_verification.rows){const tr=document.createElement('tr');for(const value of [row.mesh_name+' / '+h.hole,h.source_open_rays+' / '+h.mesh_open_rays+' of '+h.sample_count,h.source_open_rays_blocked_by_mesh+' / '+h.unexpected_open_rays,h.passes_sampling_gate?'Pass':'Attention']){const td=document.createElement('td');td.textContent=value;tr.append(td);}$('flow-refinement-bores').append(tr);}}
      for(const pair of summary.successive_changes){addMetric('flow-refinement-changes',pair.from_mesh+' → '+pair.to_mesh+' · max velocity change / inlet',(pair.maximum_velocity_change_normalized_by_inlet*100).toFixed(3)+'%');addMetric('flow-refinement-changes',pair.from_mesh+' → '+pair.to_mesh+' · max pressure change / inlet dynamic scale',(pair.maximum_pressure_change_normalized_by_inlet_dynamic_scale*100).toFixed(3)+'%');}
      for(const p of summary.studies[0].probes){const option=document.createElement('option');option.value=p.name;option.textContent=p.name;$('flow-refinement-probe').append(option);}const show=()=>{$('flow-refinement-probes').replaceChildren();for(const row of summary.studies){const p=row.probes.find(p=>p.name===$('flow-refinement-probe').value);const tr=document.createElement('tr');for(const value of [row.mesh_name,p.speed_m_s.toExponential(5),(p.pressure_minus_upstream_m2_s2??p.kinematic_pressure_m2_s2).toExponential(5),((p.maximum_support_distance_m??p.distance_m)*1000).toFixed(3)]){const td=document.createElement('td');td.textContent=value;tr.append(td);}$('flow-refinement-probes').append(tr);}};$('flow-refinement-probe').onchange=show;show();
      for(const [label,value] of [['All solver execution checks',summary.checks.all_solver_execution_checks?'Pass':'Attention'],['All bore sampling gates',summary.checks.all_bore_sampling_gates?'Pass':'Attention'],['Cell counts increase',summary.checks.cell_counts_increase?'Yes':'No'],['Mesh independence','Not established'],['Domain convergence','Not established']])addMetric('metrics',label,value);
      for(const text of summary.limits){const li=document.createElement('li');li.textContent=text;$('assumptions').append(li);}for(const [label,value] of [['Run ID',id],['Source parent',record.parent_id],['Source STL SHA-256',summary.source_stl_sha256],['Parent manifest SHA-256',record.manifest.source_parent_manifest_sha256],['Manifest SHA-256',record.manifest_sha256]])addMetric('provenance',label,value);
      $('flow-refinement-csv').href=artifactUrl(id,'verification.csv');$('flow-refinement-json').href=artifactUrl(id,'result.json');$('flow-refinement-json').download='kcee-flow-refinement-'+id.slice(0,8)+'.json';$('report').href=artifactUrl(id,'report.md');$('manifest').href=artifactUrl(id,'manifest.json');$('result').hidden=false;$('result-empty').hidden=true;badge('integrity','Artifacts verified','good');$('status').textContent='Three saved meshes compared. Review bore sampling and field sensitivity; mesh independence is not established.';updateCreation();return;
    }
    if(result.kind==='bracket_flow'){
      flowSourceId=record.parent_id;const flow=result.flow;addMetric('metrics','Domain',flow.domain_name??'base');$('result-title').textContent='Exploratory external bracket flow';$('bracket-flow-results').hidden=false;if(renderer){displayGeometry(stl);mesh.material.color.set('#b9c3ca');}
      $('bracket-flow-quantity').value='speed';$('bracket-flow-window').value='slice';
      const show=()=>{const data=flowPoints(flow,$('bracket-flow-quantity').value,$('bracket-flow-window').value);$('bracket-flow-legend').textContent='Blue '+data.min.toExponential(4)+' → red '+data.max.toExponential(4)+' '+data.units+' · '+data.count+' fluid points · view-specific scale. Inlet +x: 0.01 m/s; no-slip bracket; slip sides; p/ρ=0 at outlet.';if(!renderer)return;if(flowCloud){scene.remove(flowCloud);flowCloud.geometry.dispose();flowCloud.material.dispose();}const positions=new Float32Array(data.positions);for(let i=0;i<positions.length;i+=3){positions[i]-=modelCenter.x;positions[i+1]-=modelCenter.y;positions[i+2]-=modelCenter.z;}const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(positions,3));geometry.setAttribute('color',new THREE.Float32BufferAttribute(data.colors,3));geometry.computeBoundingSphere();flowCloud=new THREE.Points(geometry,new THREE.PointsMaterial({size:2.5,sizeAttenuation:false,vertexColors:true,transparent:true,opacity:.7,depthWrite:false}));scene.add(flowCloud);fitModel();};for(const id of ['bracket-flow-quantity','bracket-flow-window'])$(id).onchange=show;show();
      for(const [label,value] of [['Fluid cells',flow.cells],['Reynolds number · 60 mm length',flow.reynolds_length_60mm],['Nominal near-surface cell',flow.mesh.near_surface_nominal_cell_m*1000+' mm · no prism layers'],['Max non-orthogonality',flow.mesh.maximum_nonorthogonality_degrees.toFixed(3)+'°'],['Max skewness',flow.mesh.maximum_skewness.toFixed(4)],['Last initial velocity residual',Math.max(flow.residuals.Ux,flow.residuals.Uy,flow.residuals.Uz).toExponential(4)],['Last initial pressure residual',flow.residuals.p.toExponential(4)],['Boundary mass imbalance',flow.relative_boundary_mass_imbalance.toExponential(4)],['Inlet volume flux',flow.boundary_flux_m3_s.inlet.toExponential(5)+' m³/s'],['Outlet volume flux',flow.boundary_flux_m3_s.outlet.toExponential(5)+' m³/s']])addMetric('metrics',label,value);
      $('flow-bore-note').textContent=flow.bore_verification?'Finite source/mesh axial ray samples; no exact diameter or hydraulic-area acceptance. See the three-mesh report for sampling settings.':'Not recorded in this historical run. Create a new flow or three-mesh verification study.';
      if(flow.bore_verification)for(const h of flow.bore_verification.rows){const tr=document.createElement('tr');for(const value of [h.hole,h.source_open_rays+' / '+h.mesh_open_rays+' of '+h.sample_count,h.source_open_rays_blocked_by_mesh+' / '+h.unexpected_open_rays,h.passes_sampling_gate?'Pass':'Attention']){const td=document.createElement('td');td.textContent=value;tr.append(td);}$('flow-bore-rows').append(tr);}
      for(const [key,label] of Object.entries({surface_closed:'Source surface closed',mesh_quality:'OpenFOAM mesh quality',finite_fields:'Finite velocity and pressure fields',velocity_residual:'Velocity residual < 1e-5',pressure_residual:'Pressure residual < 1e-4',boundary_mass_balance:'Boundary relative imbalance < 1e-5',final_local_continuity:'Final local continuity < 1e-6'}))addMetric('bracket-flow-checks',label,flow.checks[key]?'Pass':'Needs attention');
      for(const text of flow.limits){const li=document.createElement('li');li.textContent=text;$('assumptions').append(li);}
      for(const [label,value] of [['Run ID',id],['Parent design',record.parent_id],['Source STL SHA-256',flow.source.source_stl_sha256],['Surface preparation',flow.source.unit_conversion],['Backend',flow.backend],['Inputs (SI)',JSON.stringify(flow.inputs)],['Recorded status',record.validation_status],['Solver archive SHA-256',record.manifest.artifacts['cfd-artifacts.zip']],['Parent manifest SHA-256',record.manifest.source_parent_manifest_sha256],['Manifest SHA-256',record.manifest_sha256]])addMetric('provenance',label,value);
      $('bracket-flow-csv').href=artifactUrl(id,'field.csv');$('bracket-flow-json').href=artifactUrl(id,'result.json');$('bracket-flow-json').download='kcee-bracket-flow-'+id.slice(0,8)+'.json';$('bracket-flow-archive').href=artifactUrl(id,'cfd-artifacts.zip');$('report').href=artifactUrl(id,'report.md');$('manifest').href=artifactUrl(id,'manifest.json');$('result').hidden=false;$('result-empty').hidden=true;badge('integrity','Artifacts verified','good');$('status').textContent=Object.values(flow.checks).every(v=>v===true)?'Exploratory bracket flow checks passed. Single coarse mesh; no force or engineering acceptance.':'Exploratory bracket flow checks need attention. Inspect the recorded diagnostics; no engineering acceptance.';updateCreation();return;
    }
    if(result.kind==='cfd_vortex'){
      const flow=result.vortex,fine=flow.mesh_study.at(-1);if(!Object.values(flow.checks).every(v=>v===true))throw Error('Vortex verification failed');if(renderer)displayGeometry(stl);
      $('result-title').textContent='OpenFOAM Taylor–Green verification';$('vortex-results').hidden=false;
      for(const m of flow.mesh_study){const option=document.createElement('option');option.value=m.cells_per_axis;option.textContent=m.cells_per_axis+' × '+m.cells_per_axis;$('vortex-grid').append(option);const tr=document.createElement('tr');for(const value of [m.cells_per_axis+'²',(m.relative_velocity_l2_error*100).toFixed(5)+'%',(m.relative_pressure_l2_error*100).toFixed(5)+'%',(m.relative_energy_error*100).toFixed(5)+'%']){const td=document.createElement('td');td.textContent=value;tr.append(td);}$('vortex-rows').append(tr);}
      $('vortex-study').value='mesh';$('vortex-study').querySelector('option[value="time"]').disabled=!flow.time_study;$('vortex-quantity').value='speed';$('vortex-mesh').checked=false;
      const studyRows=()=>$('vortex-study').value==='time'?flow.time_study:flow.mesh_study;
      const selectionKey=m=>$('vortex-study').value==='time'?m.time_step_s:m.cells_per_axis;
      const show=()=>drawVortex($('vortex-view'),studyRows().find(m=>String(selectionKey(m))===$('vortex-grid').value),$('vortex-quantity').value,$('vortex-mesh').checked);
      const scope=()=>{$('vortex-grid').replaceChildren();$('vortex-grid-label').textContent=$('vortex-study').value==='time'?'Saved time step (64 × 64 grid)':'Saved mesh (Δt = 0.005 s)';for(const m of studyRows()){const option=document.createElement('option');option.value=selectionKey(m);option.textContent=$('vortex-study').value==='time'?'Δt = '+m.time_step_s+' s':m.cells_per_axis+' × '+m.cells_per_axis;$('vortex-grid').append(option);}$('vortex-grid').value=selectionKey(studyRows().at(-1));show();};
      $('vortex-study').onchange=scope;for(const id of ['vortex-grid','vortex-quantity','vortex-mesh'])$(id).onchange=show;scope();
      const series=convergenceSeries(flow);drawConvergence($('vortex-spatial-chart'),series.spatial,'Mesh errors vs analytical solution','Cell size (m)','Relative L2 error · log scale');drawConvergence($('vortex-time-chart'),series.temporal,'Time-step field differences','Coarse Δt (s)','Relative L2 difference · log scale');
      if(flow.time_refinement){const t=flow.time_refinement,last=t.successive_differences.at(-1);for(const [label,value] of [['Fixed temporal-study grid','64 × 64 cells'],['Last Δt pair',last.coarse_time_step_s+' → '+last.fine_time_step_s+' s'],['Last velocity difference',(last.relative_velocity_difference*100).toExponential(4)+'% · gate < '+t.tolerances.last_relative_velocity_difference*100+'%'],['Last pressure difference',(last.relative_pressure_difference*100).toFixed(5)+'% · gate < '+t.tolerances.last_relative_pressure_difference*100+'%'],['Velocity difference orders',t.observed_difference_orders.relative_velocity_difference.map(v=>v===null?'Unavailable':v.toFixed(3)).join(', ')],['Pressure difference orders',t.observed_difference_orders.relative_pressure_difference.map(v=>v===null?'Unavailable':v.toFixed(3)).join(', ')],['Joint space-time limit','Not established']])addMetric('vortex-time-summary',label,value);
      for(const m of flow.time_study){const tr=document.createElement('tr');for(const value of [m.time_step_s,(m.relative_velocity_l2_error*100).toFixed(5)+'%',(m.relative_pressure_l2_error*100).toFixed(5)+'%',(m.relative_energy_error*100).toFixed(5)+'%']){const td=document.createElement('td');td.textContent=value;tr.append(td);}$('vortex-time-rows').append(tr);}}
      for(const [label,value] of [['Solver',flow.backend],['Final time','0.5 s'],['Mesh-study summary','64² cells · Δt = 0.005 s'],['Fine cells',fine.cells],['Velocity L2 relative error',(fine.relative_velocity_l2_error*100).toFixed(5)+'%'],['Pressure L2 relative error · mean removed',(fine.relative_pressure_l2_error*100).toFixed(5)+'%'],['Mean kinetic energy',fine.kinetic_energy_m2_s2.toFixed(7)+' m²/s²'],['Exact mean kinetic energy',fine.analytical_kinetic_energy_m2_s2.toFixed(7)+' m²/s²'],['Fine cell-centre divergence diagnostic',fine.maximum_cell_central_divergence_s_inv.toExponential(3)+' s⁻¹']])addMetric('metrics',label,value);
      const labels={velocity_accuracy:'Fine velocity error < 2%',pressure_accuracy:'Fine pressure error < 5%',energy_accuracy:'Fine energy error < 4%',velocity_refinement:'Velocity error decreases across meshes',pressure_refinement:'Pressure error decreases across meshes',face_flux_continuity:'Worst solver local continuity error < 1e-7',mesh_quality:'OpenFOAM checkMesh',time_velocity_decreasing:'Time-step velocity differences decrease',time_pressure_decreasing:'Time-step pressure differences decrease',time_velocity_change:'Last time-step velocity difference < 0.1%',time_pressure_change:'Last time-step pressure difference < 0.5%',time_mesh_quality:'All time-study meshes pass checkMesh',time_face_flux_continuity:'All time-study local continuity errors < 1e-7'};
      for(const [key,label] of Object.entries(labels).filter(([key])=>Object.hasOwn(flow.checks,key)))addMetric('vortex-checks',label,(flow.checks[key]?'Pass':'Needs attention')+(key==='face_flux_continuity'?' · '+Math.max(...flow.mesh_study.map(m=>m.maximum_local_continuity_error)).toExponential(3):''));
      for(const text of flow.limits){const li=document.createElement('li');li.textContent=text;$('assumptions').append(li);}
      for(const [label,value] of [['Run ID',id],['Method',flow.method],['Fixed inputs (SI)',JSON.stringify(flow.inputs)],['Validation status',record.validation_status],['Solver archive SHA-256',record.manifest.artifacts['cfd-artifacts.zip']],['Adapter source SHA-256',record.manifest.solver_source_sha256],['Manifest SHA-256',record.manifest_sha256]])addMetric('provenance',label,value);
      if(record.manifest.artifacts['verification.csv']){$('vortex-verification-csv').href=artifactUrl(id,'verification.csv');$('vortex-verification-csv').hidden=false;}$('vortex-json').href=artifactUrl(id,'result.json');$('vortex-json').download='kcee-vortex-'+id.slice(0,8)+'.json';$('vortex-csv').href=artifactUrl(id,'field.csv');$('vortex-archive').href=artifactUrl(id,'cfd-artifacts.zip');$('report').href=artifactUrl(id,'report.md');$('manifest').href=artifactUrl(id,'manifest.json');$('result').hidden=false;$('result-empty').hidden=true;badge('integrity','Artifacts verified','good');$('status').textContent='OpenFOAM velocity, pressure, energy, continuity and mesh checks passed. Engineering validation remains pending.';updateCreation();return;
    }
    if(result.kind==='cfd_benchmark'){
      const flow=result.cfd,fine=flow.mesh_study.at(-1);if(!Object.values(flow.checks).every(v=>v===true))throw new Error('CFD numerical checks failed');if(renderer)displayGeometry(stl);
      $('result-title').textContent='Plane Poiseuille CFD benchmark';$('cfd-results').hidden=false;
      for(const row of flow.mesh_study){const option=document.createElement('option');option.value=String(row.cells);option.textContent=row.cells+' cells';$('cfd-mesh-select').append(option);const tr=document.createElement('tr');for(const value of [row.cells,row.relative_profile_error.toExponential(3),row.relative_flow_error.toExponential(3),row.relative_momentum_balance_error.toExponential(2)]){const td=document.createElement('td');td.textContent=value;tr.append(td);}$('cfd-mesh-rows').append(tr);}
      $('cfd-mesh-select').value=String(fine.cells);const chart=()=>drawCFDChart($('cfd-chart'),flow.mesh_study.find(m=>String(m.cells)===$('cfd-mesh-select').value));$('cfd-mesh-select').onchange=chart;chart();
      for(const [label,value] of [['Mean velocity · finest grid',fine.mean_velocity_m_s.toExponential(6)+' m/s'],['Flow per unit span · finest grid',fine.flow_per_span_m2_s.toExponential(6)+' m²/s'],['Analytical flow per unit span',fine.analytical_flow_per_span_m2_s.toExponential(6)+' m²/s'],['Fine relative flow error',(fine.relative_flow_error*100).toFixed(5)+'%'],['Wall shear magnitude',fine.wall_shear_lower_Pa.toExponential(6)+' Pa'],['Reynolds number · hydraulic diameter 2H',fine.reynolds_hydraulic_diameter.toFixed(4)],['Observed profile orders',flow.observed_orders.map(o=>o.toFixed(4)).join(', ')]])addMetric('metrics',label,value);
      const tolerance=flow.tolerances;for(const [key,label,detail] of [['profile_accuracy','Fine profile error',fine.relative_profile_error.toExponential(3)+' < '+tolerance.relative_profile_error],['flow_accuracy','Fine flow error',fine.relative_flow_error.toExponential(3)+' < '+tolerance.relative_flow_error],['momentum_balance','Worst momentum imbalance',Math.max(...flow.mesh_study.map(m=>m.relative_momentum_balance_error)).toExponential(3)+' < '+tolerance.relative_momentum_balance_error],['equation_residual','Worst equation residual',Math.max(...flow.mesh_study.map(m=>m.maximum_momentum_residual_Pa_m)).toExponential(3)+' Pa/m < '+tolerance.maximum_momentum_residual_Pa_m+' Pa/m'],['symmetry','Worst profile asymmetry',Math.max(...flow.mesh_study.map(m=>m.relative_symmetry_error)).toExponential(3)+' < '+tolerance.relative_symmetry_error],['second_order_refinement','Observed convergence orders',flow.observed_orders.map(o=>o.toFixed(4)).join(', ')+'; required '+tolerance.observed_order_minimum+'–'+tolerance.observed_order_maximum]])addMetric('cfd-check-values',label,(flow.checks[key]?'Pass':'Needs attention')+' · '+detail);
      for(const text of flow.limits){const li=document.createElement('li');li.textContent=text;$('assumptions').append(li);}
      for(const [label,value] of [['Run ID',record.id],['Method',flow.method],['Gap',flow.inputs.gap_m+' m'],['Driving pressure gradient',flow.inputs.pressure_gradient_Pa_m+' Pa/m'],['Viscosity',flow.inputs.dynamic_viscosity_Pa_s+' Pa·s'],['Density',flow.inputs.density_kg_m3+' kg/m³'],['Illustrative length',flow.inputs.display_length_m+' m · envelope only'],['Validation status',record.validation_status],['Solver source SHA-256',record.manifest.solver_source_sha256],['Manifest SHA-256',record.manifest_sha256]])addMetric('provenance',label,value);
      currentStudy={id,result,record};$('study-assistant').hidden=false;$('question-displacement').textContent='Flow & shear';$('question-stress').textContent='Model limits';$('question-refinement').textContent='Refinement';$('pin-comparison').disabled=false;await showComparison(ticket,signal);if(ticket!==selection)return;$('cfd-profile').href=artifactUrl(id,'velocity.csv');$('cfd-json').href=artifactUrl(id,'result.json');$('cfd-json').download='kcee-cfd-'+id.slice(0,8)+'.json';$('report').href=artifactUrl(id,'report.md');$('manifest').href=artifactUrl(id,'manifest.json');$('result').hidden=false;$('result-empty').hidden=true;badge('integrity','Artifacts verified','good');$('status').textContent='Channel-flow numerical verification passed. The 3D shape is an illustrative envelope; this is not a bracket-flow simulation.';updateCreation();return;
    }
    if(result.kind==='bracket_thermal'){
      const thermal=result.thermal,fine=thermal.mesh_study.at(-1);selectedIsThermal=true;$('boundaries').disabled=!renderer;$('boundary-toggle-label').textContent='Thermal boundaries';sourceStl=stl;archiveDigest=record.manifest.artifacts['thermal-artifacts.zip'];if(renderer)displayGeometry(stl);$('field').disabled=!renderer;
      $('result-title').textContent='Bracket steady thermal study';$('bracket-thermal-results').hidden=false;
      for(const [label,value] of [['Minimum nodal temperature',fine.minimum_temperature_C.toFixed(3)+' °C'],['Maximum nodal temperature',fine.maximum_temperature_C.toFixed(3)+' °C'],['Volume-mean temperature',fine.volume_mean_temperature_C.toFixed(4)+' °C'],['Heat supplied at hot boundary',fine.hot_reaction_heat_W.toFixed(6)+' W'],['Heat removed at cold boundary',(-fine.cold_reaction_heat_W).toFixed(6)+' W'],['Last heat-flow change',(thermal.last_relative_heat_flow_change*100).toFixed(3)+'%'],['Last mean-temperature change',thermal.last_mean_temperature_change_C.toFixed(4)+' °C']])addMetric('metrics',label,value);
      const labels={solver_bar_verification:'Exact 3D bar reference',heat_balance:'Hot/cold heat balance',prescribed_temperatures:'Prescribed temperatures',temperature_bounds:'Nodal temperature bounds',last_heat_flow_change:'Last heat-flow change',last_mean_temperature_change:'Last mean-temperature change',source_volume_agreement:'STL volume agreement'};
      for(const [key,label] of Object.entries(labels))addMetric('bracket-thermal-checks',label,thermal.checks[key]===true?'Pass':thermal.checks[key]===false?'Needs attention':'Not recorded');
      for(const row of thermal.mesh_study){const tr=document.createElement('tr');for(const value of [row.target_size_mm,row.volume_mean_temperature_C.toFixed(4),row.hot_reaction_heat_W.toFixed(6)]){const td=document.createElement('td');td.textContent=value;tr.appendChild(td);}$('bracket-thermal-rows').appendChild(tr);}
      for(const text of [thermal.boundary,...result.assumptions]){const li=document.createElement('li');li.textContent=text;$('assumptions').appendChild(li);}
      for(const [label,value] of [['Run ID',record.id],['Parent design',record.parent_id],['Backend',thermal.backend],['Conductivity',thermal.conductivity_W_m_K+' W/(m·K) · illustrative'],['Element',thermal.element_type],['Validation status',record.validation_status],['Source STL SHA-256',thermal.source_stl_sha256],['Manifest SHA-256',record.manifest_sha256]])addMetric('provenance',label,value);
      currentStudy={id,result,record};$('study-assistant').hidden=false;configureAssistantQuestions(true);$('bracket-thermal-csv').href=artifactUrl(id,'temperature.csv');$('solver-files').href=artifactUrl(id,'thermal-artifacts.zip');$('solver-files').hidden=false;$('report').href=artifactUrl(id,'report.md');$('manifest').href=artifactUrl(id,'manifest.json');$('result').hidden=false;$('result-empty').hidden=true;badge('integrity','Artifacts verified','good');$('status').textContent=Object.values(thermal.checks).every(value=>value===true)?'Thermal numerical checks passed. Engineering validation remains pending.':'Thermal numerical checks need attention. No engineering acceptance.';updateCreation();return;
    }
    if(result.kind==='thermal_benchmark'){
      const thermal=result.thermal,fine=thermal.mesh_study.at(-1);if(!Object.values(thermal.checks).every(value=>value===true))throw new Error('Thermal checks did not pass');
      if(renderer)displayGeometry(stl);$('result-title').textContent='Thermal implementation benchmark';$('thermal-results').hidden=false;
      for(const mesh of thermal.mesh_study){const option=document.createElement('option');option.value=String(mesh.cells);option.textContent=mesh.cells+' cells';$('thermal-mesh').appendChild(option);}$('thermal-mesh').value=String(fine.cells);const showThermalMesh=()=>drawThermalChart($('thermal-charts'),thermal.mesh_study.find(mesh=>String(mesh.cells)===$('thermal-mesh').value));$('thermal-mesh').onchange=showThermalMesh;showThermalMesh();
      addMetric('metrics','Peak nodal temperature',fine.peak_temperature_C.toFixed(4)+' °C');addMetric('metrics','Maximum analytical temperature error',fine.maximum_temperature_error_C.toExponential(3)+' °C');addMetric('metrics','Generated heat',fine.generated_heat_W.toFixed(6)+' W');addMetric('metrics','Outward heat · left',fine.outward_left_heat_W.toFixed(6)+' W');addMetric('metrics','Outward heat · right',fine.outward_right_heat_W.toFixed(6)+' W');addMetric('metrics','Observed temperature convergence order',thermal.observed_orders.at(-1).toFixed(4));
      const tolerances=thermal.tolerances||{},bound=(value,units='')=>Number.isFinite(value)?value.toExponential(2)+units:'not recorded',verdict=key=>thermal.checks[key]===true?'Pass':thermal.checks[key]===false?'Needs attention':'Not recorded';
      for(const [key,label,value,threshold] of [
        ['temperature_accuracy','Fine-grid temperature error',fine.maximum_temperature_error_C.toExponential(3)+' °C','< '+bound(tolerances.temperature_error_C,' °C')],
        ['second_order_refinement','Observed refinement orders',thermal.observed_orders.map(order=>order.toFixed(4)).join(', '),Number.isFinite(tolerances.observed_order_minimum)&&Number.isFinite(tolerances.observed_order_maximum)?tolerances.observed_order_minimum+' < order < '+tolerances.observed_order_maximum:'not recorded'],
        ['heat_balance','Worst relative heat imbalance',Math.max(...thermal.mesh_study.map(mesh=>mesh.relative_heat_balance_error)).toExponential(3),'< '+bound(tolerances.relative_heat_balance_error)],
        ['integrated_source_accuracy','Fine-grid generated-heat error',fine.relative_generated_heat_error.toExponential(3),'< '+bound(tolerances.relative_generated_heat_error)],
        ['equation_residual','Worst equation residual',Math.max(...thermal.mesh_study.map(mesh=>mesh.maximum_equation_residual_W_m3)).toExponential(3)+' W/m³','< '+bound(tolerances.equation_residual_W_m3,' W/m³')]
      ])addMetric('thermal-checks',label,verdict(key)+' · '+value+' · threshold '+threshold);
      for(const mesh of thermal.mesh_study){const tr=document.createElement('tr');for(const value of [mesh.cells,mesh.maximum_temperature_error_C.toExponential(3),mesh.relative_heat_balance_error.toExponential(2)]){const td=document.createElement('td');td.textContent=value;tr.appendChild(td);}$('thermal-rows').appendChild(tr);}
      for(const text of result.assumptions){const li=document.createElement('li');li.textContent=text;$('assumptions').appendChild(li);}
      for(const [label,value] of [['Run ID',record.id],['Method',thermal.method],['Conductivity',thermal.inputs.conductivity_W_m_K+' W/(m·K) · illustrative'],['End temperatures',thermal.inputs.left_temperature_C+' / '+thermal.inputs.right_temperature_C+' °C'],['Analytical solution',thermal.analytical_temperature],['Validation status',record.validation_status],['Solver source SHA-256',record.manifest.solver_source_sha256],['Manifest SHA-256',record.manifest_sha256]])addMetric('provenance',label,value);
      currentStudy={id,result,record};$('study-assistant').hidden=false;configureAssistantQuestions(true);$('thermal-profile').href=artifactUrl(id,'temperature.csv');$('report').href=artifactUrl(id,'report.md');$('manifest').href=artifactUrl(id,'manifest.json');$('result').hidden=false;$('result-empty').hidden=true;badge('integrity','Artifacts verified','good');$('status').textContent='Thermal benchmark checks passed. Bracket thermal validation remains pending.';updateCreation();return;
    }
    if(result.geometry_backend.startsWith('PicoGK')){
      $('geometry-measurements').hidden=false;
      try{
        const measured=await request(`/runs/${id}/geometry-measurements`,{signal});if(ticket!==selection)return;
        if(measured.run_id!==id || measured.source_stl_sha256!==record.manifest.artifacts['bracket.stl'])throw new Error('Geometry measurement identity mismatch');
        addMetric('hole-values','Nominal bore',measured.nominal_diameter_mm.toFixed(2)+' mm');
        for(const name of ['base-1','base-2','upright-1','upright-2']){
          const rows=measured.holes.filter(h=>h.hole===name);
          addMetric('hole-values',name.replace('-', ' hole '),Math.min(...rows.map(h=>h.minimum_radial_diameter_mm)).toFixed(3)+'–'+Math.max(...rows.map(h=>h.maximum_radial_diameter_mm)).toFixed(3)+' mm');
        }
        addMetric('hole-values','Section depths',measured.sections_mm.join(', ')+' mm');
      }catch(error){if(ticket!==selection || error.name==='AbortError')return;addMetric('hole-values','Measurements unavailable',error.message);}
    }
    if(result.kind==='bracket_structural'){
      $('stress-diagnostics').hidden=false;
      try{
        const diagnostic=await request(`/runs/${id}/stress-diagnostics`,{signal});if(ticket!==selection)return;
        if(diagnostic.run_id!==id || diagnostic.source_archive_sha256!==record.manifest.artifacts['fea-artifacts.zip'])throw new Error('Stress archive identity mismatch');
        verifiedDiagnostic=diagnostic;const energy=diagnostic.energy_consistency;
        if(energy){addMetric('hotspot-values','Energy vs half load work',`${energy.passes_demo_tolerance?'Pass':'Needs attention'} · ${(energy.relative_error*100).toExponential(2)}% error`);addMetric('hotspot-values','Strain energy',energy.strain_energy_N_mm.toFixed(4)+' N·mm');}
        const energyChange=diagnostic.regional_refinement?.last_energy_change;
        if(Number.isFinite(energyChange))addMetric('hotspot-values','Last strain-energy change',(energyChange*100).toFixed(3)+'% · informational');
        const peak=diagnostic.top_integration_point_stresses[0];sourceLoadWarning=!diagnostic.source_load_patch_agreement;
        addMetric('hotspot-values','Load strip vs original STL',`${diagnostic.source_load_patch_agreement?'Pass':'Needs attention'} · ${(diagnostic.relative_source_load_patch_area_error*100).toFixed(3)}% area error`);
        addMetric('hotspot-values','Original STL load-strip area',diagnostic.source_load_patch_area_mm2.toFixed(3)+' mm²');
        addMetric('hotspot-values','Peak element / integration point',peak.element_id+' / '+peak.integration_point);
        addMetric('hotspot-values','Peak element centroid · x, y, z',peak.element_corner_centroid_mm.map(v=>v.toFixed(3)).join(', ')+' mm');
        addMetric('hotspot-values','Peak element corner quality',peak.corner_mean_ratio_quality.toFixed(3));
        addMetric('hotspot-values','Minimum mesh corner quality',diagnostic.minimum_corner_quality.toExponential(3));
        addMetric('hotspot-values','Median mesh corner quality',diagnostic.median_corner_quality.toFixed(3));
        for(const change of diagnostic.regional_refinement?.last_changes || [])addMetric('hotspot-values',`Last regional stress change · ≥${change.centroid_exclusion_distance_mm} mm`,change.relative_last_peak_change===null?'Not available':(change.relative_last_peak_change*100).toFixed(2)+'% · informational');
        for(const region of diagnostic.regional_peaks || [])addMetric('hotspot-values',`Regional peak · centroids ≥${region.centroid_exclusion_distance_mm} mm from clamp/load`,region.maximum_von_mises_MPa===null?'No elements':region.maximum_von_mises_MPa.toFixed(2)+' MPa · not an allowable');
      }catch(error){if(ticket!==selection || error.name==='AbortError')return;addMetric('hotspot-values','Diagnostics unavailable',error.message);}
    }
    if(result.kind==='bracket_structural'){
      try{
        const evidence=await request(`/runs/${id}/refinement-explorations`,{signal});if(ticket!==selection)return;
        if(evidence.run_id!==id || evidence.manifest_sha256!==record.manifest_sha256 || evidence.source_stl_sha256!==record.manifest.artifacts['bracket.stl'])throw new Error('Exploration source identity mismatch');
        verifiedExploration=evidence;
        if(evidence.items.length){
          $('refinement-explorations').hidden=false;
          for(const item of evidence.items)for(const row of item.rows){
            const tr=document.createElement('tr');
            for(const value of [row.global_target_mm+' / '+(row.root_target_mm??'—'),row.nodes,row.displacement_mm.toFixed(6),row.peak_stress_MPa.toFixed(2)]){const td=document.createElement('td');td.textContent=value;tr.appendChild(td);}
            const archiveCell=document.createElement('td');
            if(row.archive_integrity==='verified' && ['global-1.3','root-0.9','root-0.75'].includes(row.download_key)){const link=document.createElement('a');link.href=`/api/runs/${id}/refinement-explorations/${row.download_key}/archive`;link.download='';link.textContent='ZIP';link.setAttribute('aria-label',`Download ${row.download_key} exploratory solver archive`);archiveCell.appendChild(link);}else archiveCell.textContent='Unavailable';
            tr.appendChild(archiveCell);$('exploration-rows').appendChild(tr);
          }
          $('exploration-evidence').value=JSON.stringify(evidence,null,2);
          const rows=evidence.items.flatMap(item=>item.rows),verified=rows.filter(row=>row.archive_integrity==='verified').length;
          $('exploration-note').textContent=`Source hashes match this verified study. ${verified} of ${rows.length} exploratory archives checked by the local API. Unavailable archives remain recorded evidence only; verification does not establish engineering acceptance.`;
        }
      }catch(error){if(ticket!==selection || error.name==='AbortError')return;$('refinement-explorations').hidden=false;$('exploration-note').textContent='Exploration evidence unavailable: '+error.message;}
    }
    const chosen=result.selected;
    for(const key of ['thickness_mm','stress_MPa','tip_deflection_mm','factor_of_safety'])if(!Number.isFinite(chosen?.[key]))throw new Error('Screening result contains invalid values');
    if(!Number.isFinite(result.mass_kg)||!Array.isArray(result.assumptions))throw new Error('Screening result is incomplete');
    isBracketStudy=result.kind==='bracket_structural';$('boundaries').disabled=!renderer || !isBracketStudy;archiveDigest=record.manifest.artifacts['fea-artifacts.zip'];sourceStl=stl;if(renderer)displayGeometry(stl);$('field').disabled=!renderer || result.kind!=='bracket_structural';
    addMetric('metrics','Selected thickness',chosen.thickness_mm.toFixed(1)+' mm');addMetric('metrics','Mass', (result.mass_kg*1000).toFixed(1)+' g');
    addMetric('metrics',result.kind==='bracket_structural'?'Ideal-cantilever stress':'Analytical stress',chosen.stress_MPa.toFixed(2)+' MPa');addMetric('metrics',result.kind==='bracket_structural'?'Ideal-cantilever estimate':'Estimated deflection',chosen.tip_deflection_mm.toFixed(3)+' mm');if(result.fea){const fine=result.fea.mesh_study.at(-1);addMetric('metrics',result.kind==='bracket_structural'?'FEA loaded-patch displacement':'FEA tip deflection',fine.tip_deflection_mm.toFixed(3)+' mm');if(result.kind==='bracket_structural'){addMetric('metrics','Source volume agreement error',(result.fea.relative_source_volume_error*100).toFixed(2)+'%');addMetric('metrics','Mesh peak stress · not converged',fine.maximum_von_mises_MPa.toFixed(2)+' MPa');}else addMetric('metrics','Analytical comparison error',(result.fea.relative_displacement_error*100).toFixed(2)+'%');addMetric('metrics','Last mesh displacement change',(result.fea.last_mesh_displacement_change*100).toFixed(2)+'%');addMetric('metrics','Support reaction',fine.reaction_z_N.toFixed(3)+' N');}else addMetric('metrics','Analytical factor of safety',chosen.factor_of_safety.toFixed(2));
    if(result.kind==='bracket_structural'){
      $('validation-checks').hidden=false;const fea=result.fea,fine=fea.mesh_study.at(-1);
      for(const {label,value,verdict} of numericalCheckRows(fea))addMetric('check-values',label,verdict+(Number.isFinite(value)?' · '+(value*100).toFixed(3)+'%':''));
      const previous=fea.mesh_study.at(-2);if(previous?.maximum_von_mises_MPa>0)addMetric('check-values','Last peak-stress change · informational',(Math.abs(fine.maximum_von_mises_MPa/previous.maximum_von_mises_MPa-1)*100).toFixed(2)+'% · convergence not established');
    }
    const displayedAssumptions=result.kind==='bracket_structural'?['Actual native PicoGK STL, including mounting holes and root transition',result.fea.boundary,result.fea.load,'Linear isotropic elasticity and small displacement; illustrative material properties',result.fea.stress_note,'Numerical checks do not establish engineering validation','Analytical estimates are separate ideal-cantilever references']:result.assumptions;
    for(const text of displayedAssumptions){const li=document.createElement('li');li.textContent=text;$('assumptions').appendChild(li);}
    addMetric('provenance','Run ID',record.id);if(record.parent_id)addMetric('provenance','Parent design',record.parent_id);addMetric('provenance','Created',new Date(record.created_at).toLocaleString());addMetric('provenance','Geometry',result.geometry_backend);addMetric('provenance','Structural model',result.structural_backend);addMetric('provenance','Validation status',record.validation_status);addMetric('provenance','Manifest SHA-256',record.manifest_sha256);
    selectedIsNative=result.geometry_backend.startsWith('PicoGK');flowSourceId=selectedIsNative?id:null;updateCreation();
    if(result.fea){$('result-title').textContent=result.kind==='bracket_structural'?'Bracket structural study':'Cantilever verification';$('mesh-study').hidden=false;$('displacement-heading').textContent=result.kind==='bracket_structural'?'Loaded patch (mm)':'Tip (mm)';$('stress-heading').hidden=result.kind!=='bracket_structural';$('mesh-note').hidden=result.kind!=='bracket_structural';for(const mesh of result.fea.mesh_study){const row=document.createElement('tr');for(const value of [mesh.elements,mesh.tip_deflection_mm.toFixed(6),mesh.reaction_z_N.toFixed(4),...(result.kind==='bracket_structural'?[mesh.maximum_von_mises_MPa.toFixed(2)]:[])]){const cell=document.createElement('td');cell.textContent=value;row.appendChild(cell);}$('mesh-rows').appendChild(row);}$('solver-files').href=artifactUrl(id,'fea-artifacts.zip');$('solver-files').hidden=false;}
    currentStudy=result.kind==='bracket_structural'?{id,result,record}:null;$('study-assistant').hidden=!currentStudy;updateCreation();$('pin-comparison').disabled=!currentStudy;if(currentStudy){$('study-report-text').value=studyMarkdown(currentStudy,verifiedDiagnostic,verifiedExploration);studyReportUrl=URL.createObjectURL(new Blob([$('study-report-text').value],{type:'text/markdown'}));$('download-study-report').href=studyReportUrl;$('download-study-report').download=`kcee-study-${id.slice(0,8)}.md`;$('readable-study').hidden=false;}await showComparison(ticket,signal);if(ticket!==selection)return;
    $('report').href=artifactUrl(id,'report.md');$('manifest').href=artifactUrl(id,'manifest.json');$('result').hidden=false;$('result-empty').hidden=true;badge('integrity','Artifacts verified','good');$('status').textContent=(result.kind==='bracket_structural'?(Object.values(result.fea.checks).every(Boolean)?'Recorded numerical checks passed. Engineering validation remains pending.':'Bracket numerical checks need attention. No engineering acceptance.'):(result.fea?'Cantilever benchmark checks passed. Bracket validation remains pending.':'Artifact integrity verified. Analytical screening remains unvalidated.'))+(sourceLoadWarning?' Retrospective check: load-strip area differs from the original STL by more than 5%; study needs attention.':'')+(renderer?'':' 3D rendering is unavailable; reports are accessible.');
  } catch(error){if(ticket!==selection||error.name==='AbortError')return;clearModel();clearDetails();badge('integrity','Unable to verify','error');$('status').textContent=error.message;}
}
let servicePoll=null;
function refreshServiceStatus(){
  if(servicePoll)return servicePoll;
  servicePoll=(async()=>{
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),8000);
    try{
      const [capabilities,control,voice,assistant]=await Promise.all([request('/capabilities',{signal:controller.signal}),request('/services/control',{signal:controller.signal}).catch(()=>({available:false})),request('/voice/status',{signal:controller.signal}).catch(()=>({available:false})),request('/assistant/status',{signal:controller.signal}).catch(()=>({available:false}))]);
      assistantAvailable=assistant.available;badge('assistant-health',assistantAvailable?'On':'Off',assistantAvailable?'good':'');if(!assistantBusy && !assistantStatusPinned)$('assistant-status').textContent=assistantAvailable?'Local AI ready.':'Local AI is off or unavailable. Use Start above.';
      voiceAvailable=voice.available;badge('voice-health',voiceAvailable?'On':'Off',voiceAvailable?'good':'');if(!voiceBusy)$('voice-status').textContent=voiceAvailable?'Local Kokoro ready. Prepare audio, then press Play.':'Local voice is off or unavailable. Use Start above.';
      cfdAvailable=Boolean(capabilities.cfd?.plane_poiseuille);vortexAvailable=Boolean(capabilities.cfd?.openfoam_vortex);bracketFlowAvailable=Boolean(capabilities.cfd?.bracket_flow);$('cfd-status').textContent=cfdAvailable?'CFD worker ready · channel verification':'CFD worker stopped or unavailable.';thermalAvailable=Boolean(capabilities.thermal?.steady_1d);$('thermal-status').textContent=thermalAvailable?'Thermal worker ready · 1D verification':'Thermal worker stopped or unavailable.';
      controlAvailable=control.available;
      nativeAvailable=Boolean(capabilities.geometry?.picogk);structuralAvailable=Boolean(capabilities.structural?.calculix);
      badge('service-health',nativeAvailable || structuralAvailable || thermalAvailable || cfdAvailable?'On':'Off',nativeAvailable && structuralAvailable && thermalAvailable && cfdAvailable?'good':'');
      $('service-health').title=[nativeAvailable?'PicoGK On':'PicoGK Off',structuralAvailable?'Structural On':'Structural Off',thermalAvailable?'Thermal On':'Thermal Off',cfdAvailable?'CFD On':'CFD Off'].join(' · ');
      $('native-status').textContent=nativeAvailable?'Native PicoGK ready':'Native PicoGK stopped or unavailable.';
      $('fea-status').textContent=structuralAvailable?'CalculiX ready':'Structural worker stopped or unavailable.';
      if(control.operation?.status==='pending' && !serviceBusy)watchServiceOperation(control.operation);
      else if(control.operation && control.operation.status!=='pending'){
        controlAvailable=false;$('service-status').textContent='Service operation needs inspection on this Mac. Refresh after resolving it.';
      }else if(!serviceBusy)$('service-status').textContent=controlAvailable?'Service controls ready':'Local controls unavailable. Run the KCEE startup command on this Mac.';
    }catch{
      nativeAvailable=false;structuralAvailable=false;thermalAvailable=false;cfdAvailable=false;vortexAvailable=false;bracketFlowAvailable=false;controlAvailable=false;voiceAvailable=false;assistantAvailable=false;
      badge('assistant-health','Unknown','error');badge('voice-health','Unknown','error');badge('service-health','Unknown','error');$('service-health').title='Service status is unavailable';
      $('native-status').textContent='Native status unavailable.';$('fea-status').textContent='Structural status unavailable.';
      if(!serviceBusy)$('service-status').textContent='Unable to check services. Status will retry automatically.';
    }finally{clearTimeout(timer);updateCreation();}
  })().finally(()=>{servicePoll=null;});
  return servicePoll;
}
async function refresh(){
  listRequest?.abort();const controller=new AbortController();listRequest=controller;$('refresh').disabled=true;
  try {
    const [data]=await Promise.all([request(`/runs?limit=${PAGE_SIZE+1}&offset=${offset}&hidden=${$('show-removed').checked}`,{signal:controller.signal}),refreshServiceStatus()]);
    if(listRequest!==controller)return;
    $('runs').replaceChildren();const items=data.items.slice(0,PAGE_SIZE);
    for(const item of items){const button=document.createElement('button');button.className='run';button.dataset.id=item.id;button.textContent=(item.kind==='bracket_flow_pressure'?'Bore pressure ':item.kind==='bracket_flow_combined'?'CFD verification ':item.kind==='bracket_flow_domain'?'Flow domain ':item.kind==='bracket_flow_refinement'?'Flow verification ':item.kind==='bracket_flow'?'Bracket flow ':item.kind==='cfd_vortex'?'OpenFOAM vortex ':item.kind==='cfd_benchmark'?'CFD channel ':item.kind==='bracket_thermal'?'Bracket thermal ':item.kind==='thermal_benchmark'?'Thermal ':item.kind==='structural_benchmark'?'Cantilever ':item.kind==='bracket_structural'?'Bracket FEA ':'Bracket ')+item.id.slice(0,8);const small=document.createElement('small');small.textContent=new Date(item.created_at).toLocaleString();button.appendChild(small);button.onclick=()=>selectRun(item.id);$('runs').appendChild(button);}
    if(!items.length){const empty=document.createElement('p');empty.className='hint';empty.textContent='No saved runs on this page.';$('runs').appendChild(empty);}
    $('previous').disabled=offset===0;$('next').disabled=data.items.length<=PAGE_SIZE;$('page').textContent='Page '+(offset/PAGE_SIZE+1);highlight();badge('connection','API connected','good');
    if(!selectedId)$('status').textContent=items.length?'Select a run to load verified artifacts.':'Create a bracket demo to get started.';
  }catch(error){if(error.name==='AbortError')return;badge('connection','API unavailable','error');$('status').textContent=error.message;}finally{if(listRequest===controller)$('refresh').disabled=false;}
}
$('refresh').onclick=refresh;$('previous').onclick=()=>{offset=Math.max(0,offset-PAGE_SIZE);refresh();};$('next').onclick=()=>{offset+=PAGE_SIZE;refresh();};
$('create').onclick=async()=>{
  creating=true;updateCreation();beginSelection();selectedId=null;badge('integrity','Generating…');$('status').textContent='Generating and registering bracket demo…';
  try{const data=await request('/runs/bracket',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({geometry_backend:$('backend').value})});offset=0;await refresh();await selectRun(data.run_id);}
  catch(error){badge('integrity','Generation failed','error');$('status').textContent=error.message+(error.detail?.run_id?' Retained run: '+error.detail.run_id:'');}
  finally{creating=false;updateCreation();}
};
$('file').onchange=async event=>{
  const file=event.target.files[0];if(!file)return;const {ticket}=beginSelection();selectedId=null;highlight();badge('integrity','Local file · unverified');$('model-title').textContent=file.name;$('status').textContent='Loading local file…';
  try{if(file.size>50*1024*1024)throw new Error('Local STL exceeds the 50 MB preview limit');const bytes=await file.arrayBuffer();if(ticket!==selection)return;displayGeometry(bytes);$('status').textContent='Local geometry only. No registered provenance or screening results.';}catch(error){if(ticket===selection){clearModel();$('status').textContent=error.message;}}
};
refresh();

$('fea').onclick=async()=>{ creating=true;updateCreation();beginSelection();selectedId=null;badge('integrity','Solving benchmark…');$('status').textContent='Solving three cantilever meshes and checking convergence…';try{const data=await request('/runs/structural-benchmark',{method:'POST'});offset=0;await refresh();await selectRun(data.run_id);}catch(error){badge('integrity','Benchmark failed','error');$('status').textContent=error.message;}finally{creating=false;await refresh();updateCreation();}};

$('analyze').onclick=async()=>{const parent=selectedId;creating=true;beginSelection();updateCreation();badge('integrity','Analyzing bracket…');$('status').textContent='Meshing the selected bracket and solving three refinement levels…';try{const data=await request(`/runs/${parent}/structural`,{method:'POST'});offset=0;await refresh();await selectRun(data.run_id);}catch(error){badge('integrity','Bracket analysis failed','error');$('status').textContent=error.message+(error.detail?.run_id?' Diagnostics run: '+error.detail.run_id:'');}finally{creating=false;await refresh();updateCreation();}};

function renderField(){
  if(!fieldData)return;
  clearModel();const data=fieldData,scale=Number($('scale').value),geometry=new THREE.BufferGeometry();
  const temperature=selectedIsThermal,stress=!temperature && $('quantity').value==='stress';
  if(stress && !data.von_mises_MPa)throw new Error('Nodal stress field unavailable');
  const maximum=temperature?data.maximum_temperature_C:stress?data.maximum_surface_von_mises_MPa:data.maximum_displacement_mm;
  const points=[],colors=[],color=new THREE.Color();
  for(let i=0;i<data.positions.length;i++){
    const p=data.positions[i],u=temperature?[0,0,0]:data.displacements[i];points.push(...p.map((x,j)=>x+u[j]*scale));
    color.setHSL((1-Math.min(1,temperature?(data.temperatures_C[i]-data.minimum_temperature_C)/(maximum-data.minimum_temperature_C || 1):(stress?data.von_mises_MPa[i]:Math.hypot(...u))/(maximum || 1)))*.66,1,.5);colors.push(color.r,color.g,color.b);
  }
  geometry.setAttribute('position',new THREE.Float32BufferAttribute(points,3));geometry.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));geometry.setIndex(data.triangles.flat());geometry.computeVertexNormals();geometry.computeBoundingBox();geometry.boundingBox.getCenter(modelCenter);geometry.center();geometry.computeBoundingSphere();
  mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({vertexColors:true,side:THREE.DoubleSide,wireframe:$('wireframe').checked}));scene.add(mesh);fitModel();$('empty').hidden=true;updateBoundaries();$('fit').disabled=false;$('wireframe').disabled=false;
  $('field-legend').textContent=temperature?`Temperature · blue ${data.minimum_temperature_C.toFixed(2)} → red ${maximum.toFixed(2)} °C · saved fine mesh · no deformation · illustrative boundaries`:`${stress?'Von Mises stress · averaged nodal values':'Displacement magnitude'} · blue 0 → red ${maximum.toFixed(3)} ${stress?'MPa':'mm'} · deformation ${scale}×${stress?' · not converged; not an allowable':''}`;
}
$('scale').onchange=()=>{if($('field').checked)renderField();};
$('quantity').onchange=()=>{if($('field').checked)renderField();};
$('field').onchange=async()=>{
  const ticket=selection,id=selectedId;
  $('scale-label').hidden=!$('field').checked || selectedIsThermal;$('quantity-label').hidden=!$('field').checked || selectedIsThermal;$('field-legend').hidden=!$('field').checked;
  if(!$('field').checked){clearModel();displayGeometry(sourceStl);return;}
  $('field').disabled=true;
  try{
    if(!fieldData){const data=await request(`/runs/${id}/${selectedIsThermal?'temperature-surface':'displacement-surface'}`,{signal:activeRequest.signal});if(ticket!==selection)return;if(data.source_archive_sha256!==archiveDigest)throw new Error('Field archive identity mismatch');fieldData=data;}
    renderField();
  }catch(error){if(ticket!==selection)return;$('field').checked=false;$('scale-label').hidden=true;$('quantity-label').hidden=true;$('field-legend').hidden=true;$('status').textContent='Solver field unavailable: '+error.message;}
  finally{if(ticket===selection)$('field').disabled=false;}
};

function updateBoundaries(){
  if(boundaryMarkers){scene.remove(boundaryMarkers);boundaryMarkers.traverse(o=>{o.geometry?.dispose();o.material?.dispose();});boundaryMarkers=null;}
  $('boundary-legend').hidden=!$('boundaries').checked || !(isBracketStudy || selectedIsThermal);
  if(!$('boundaries').checked || !(isBracketStudy || selectedIsThermal) || !mesh)return;
  boundaryMarkers=new THREE.Group();boundaryMarkers.position.copy(modelCenter).multiplyScalar(-1);
  function outline(points,color){const geometry=new THREE.BufferGeometry().setFromPoints(points.map(p=>new THREE.Vector3(...p)));boundaryMarkers.add(new THREE.LineLoop(geometry,new THREE.LineBasicMaterial({color,depthTest:false,transparent:true,opacity:.9})));}
  if(selectedIsThermal){
    outline([[0,0,3.5],[0,30,3.5],[0,30,40],[0,0,40]],0x7fcfff);
    outline([[60,0,0],[60,30,0],[60,30,3.5],[60,0,3.5]],0xff7188);
    $('boundary-legend').textContent='Blue outline: rear upright at 20 °C · Red outline: free end at 80 °C · All other surfaces insulated. Outlines show nominal regions; the solver applies temperatures to the recorded boundary nodes. Ideal reservoirs, not measured service conditions.';
    scene.add(boundaryMarkers);return;
  }
  $('boundary-legend').textContent=structuralBoundaryLegend;
  outline([[0,0,3.5],[0,30,3.5],[0,30,40],[0,0,40]],0xffa940);
  outline([[55,0,3.5],[60,0,3.5],[60,30,3.5],[55,30,3.5]],0xff6ec7);
  for(const y of [5,15,25])boundaryMarkers.add(new THREE.ArrowHelper(new THREE.Vector3(0,0,-1),new THREE.Vector3(57.5,y,15.5),12,0xff6ec7,3,1.5));
  scene.add(boundaryMarkers);
}
$('boundaries').onchange=updateBoundaries;

$('diagnostics-help-link').onclick=event=>{event.preventDefault();$('diagnostics-help').showModal();};
$('diagnostics-help').addEventListener('close',()=> $('diagnostics-help-link').focus());
$('geometry-help-link').onclick=event=>{event.preventDefault();$('geometry-help').showModal();};
$('geometry-help').addEventListener('close',()=> $('geometry-help-link').focus());

$('show-removed').onchange=()=>{offset=0;selectedId=null;beginSelection();refresh();};
$('remove-run').onclick=()=>{
  if(!selectedId || (creating || serviceBusy) || removing || !selectedVerified)return;
  pendingRemoval={id:selectedId,hidden:!$('show-removed').checked};
  $('remove-title').textContent=pendingRemoval.hidden?'Remove model from list?':'Restore model to list?';
  $('remove-description').textContent=pendingRemoval.hidden?'This model will move to Removed models. Results, files and provenance are retained. You can restore it later.':'This model will return to the saved models list.';
  $('remove-id').textContent=$('model-title').textContent+' · '+pendingRemoval.id;
  $('confirm-remove').textContent=pendingRemoval.hidden?'Remove from list':'Restore to list';$('remove-confirm').showModal();
};
$('cancel-remove').onclick=()=>{$('remove-confirm').close();pendingRemoval=null;};
$('confirm-remove').onclick=async()=>{
  if(!pendingRemoval)return;const action=pendingRemoval;removing=true;updateCreation();$('cancel-remove').disabled=true;$('confirm-remove').disabled=true;
  try{await request(`/runs/${action.id}/visibility`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm_run_id:action.id,hidden:action.hidden})});$('remove-confirm').close();pendingRemoval=null;selectedId=null;beginSelection();offset=0;await refresh();$('status').textContent=action.hidden?'Model removed from list. Files and provenance retained.':'Model restored to list.';}
  catch(error){$('remove-description').textContent=error.message;}
  finally{removing=false;$('cancel-remove').disabled=false;$('confirm-remove').disabled=false;updateCreation();}
};

$('remove-confirm').addEventListener('cancel',event=>{if(removing)event.preventDefault();});
$('remove-confirm').addEventListener('close',()=>{if(!removing)pendingRemoval=null;$('remove-run').focus();});

async function showComparison(ticket,signal){
  clearComparisonExport();
  $('clear-comparison').hidden=!comparisonId;
  $('comparison-status').textContent=comparisonId?'Reference: '+comparisonId:'Select a bracket FEA or CFD channel study as reference, then select another of the same kind.';
  if(!comparisonId || !currentStudy || comparisonId===currentStudy.id)return;
  try{
    const referenceId=comparisonId;const reference=await loadRun(referenceId,signal);if(ticket!==selection || comparisonId!==referenceId)return;
    if(currentStudy.result.kind==='cfd_benchmark'){
      const report=await cfdComparison(reference,currentStudy);if(ticket!==selection || comparisonId!==referenceId)return;
      $('comparison-reference').textContent='Reference '+referenceId.slice(0,8);$('comparison-current').textContent='Selected '+currentStudy.id.slice(0,8);$('comparison-rows').replaceChildren();
      for(const measure of report.measures){const tr=document.createElement('tr');for(const value of [measure.measure,measure.reference,measure.selected]){const td=document.createElement('td');td.textContent=typeof value==='number'?(Number.isInteger(value)?String(value):Math.abs(value)<.001?value.toExponential(5):Number(value.toPrecision(6)).toString()):value;tr.append(td);}$('comparison-rows').append(tr);}
      $('comparison-json').value=JSON.stringify(report,null,2);comparisonUrl=URL.createObjectURL(new Blob([$('comparison-json').value],{type:'application/json'}));$('download-comparison').href=comparisonUrl;$('download-comparison').download='kcee-cfd-comparison.json';
      $('comparison-markdown').value=cfdComparisonMarkdown(report);comparisonMarkdownUrl=URL.createObjectURL(new Blob([$('comparison-markdown').value],{type:'text/markdown'}));$('download-comparison-markdown').href=comparisonMarkdownUrl;$('download-comparison-markdown').download='kcee-cfd-comparison.md';
      $('comparison-status').textContent='Both CFD cases verified. Flow change: '+report.flow_change_percent.toFixed(3)+'%. All changed inputs contribute; compare the recorded assumptions.';$('comparison').hidden=false;return;
    }
    if(currentStudy.result.kind!=='bracket_structural')throw new Error('Select two studies of the same supported kind');
    if(reference.result.kind!=='bracket_structural')throw new Error('Reference must be a bracket FEA study');
    $('comparison-reference').textContent='Reference '+comparisonId.slice(0,8);$('comparison-current').textContent='Selected '+currentStudy.id.slice(0,8);
    const a=reference.result,b=currentStudy.result;
    const measures=[['Voxel size (mm)',r=>r.geometry?.voxel_size_mm],['Surface classification (degrees)',r=>r.fea.surface_classification_angle_degrees],['Load-strip local target (mm)',r=>Object.hasOwn(r.fea,'load_strip_local_target_mm')?(r.fea.load_strip_local_target_mm??'None'):'Not recorded'],['Fine elements',r=>r.fea.mesh_study.at(-1).elements],['Load integration',r=>r.fea.load?.includes('clipped-planar-face')?'Clipped quadratic faces':r.fea.load?.includes('consistent quadratic-face')?'Whole faces by centroid':'Not recorded'],['Source load-area error (%)',r=>Number.isFinite(r.fea.relative_source_load_patch_area_error)?100*r.fea.relative_source_load_patch_area_error:'Not recorded'],['Recorded source-area check',r=>r.fea.checks?.load_patch_source_agreement===true?'Pass':r.fea.checks?.load_patch_source_agreement===false?'Needs attention':'Not recorded'],['Load-patch area (mm²)',r=>r.fea.mesh_study.at(-1).load_patch_area_mm2],['Loaded displacement (mm)',r=>r.fea.mesh_study.at(-1).tip_deflection_mm],['Peak stress (MPa) · unconverged',r=>r.fea.mesh_study.at(-1).maximum_von_mises_MPa],['Validation',r=>r.validation_status]];
    $('comparison-rows').replaceChildren();
    for(const [label,value] of measures){const row=document.createElement('tr');for(const item of [label,value(a),value(b)]){const cell=document.createElement('td');cell.textContent=typeof item==='number'?(Number.isInteger(item)?String(item):item.toFixed(4)):item??'Not recorded';row.appendChild(cell);}$('comparison-rows').appendChild(row);}
    const difference=(b.fea.mesh_study.at(-1).tip_deflection_mm/a.fea.mesh_study.at(-1).tip_deflection_mm-1)*100;
    const evidence=comparisonEvidence(reference,currentStudy,measures.map(([label,value])=>({measure:label,reference:value(a)??null,selected:value(b)??null})),difference);
    $('comparison-markdown').value=comparisonMarkdown(evidence);comparisonMarkdownUrl=URL.createObjectURL(new Blob([$('comparison-markdown').value],{type:'text/markdown'}));$('download-comparison-markdown').href=comparisonMarkdownUrl;$('download-comparison-markdown').download=`kcee-comparison-${comparisonId.slice(0,8)}-${currentStudy.id.slice(0,8)}.md`;
    $('comparison-json').value=JSON.stringify(evidence,null,2);comparisonUrl=URL.createObjectURL(new Blob([$('comparison-json').value],{type:'application/json'}));$('download-comparison').href=comparisonUrl;$('download-comparison').download=`kcee-comparison-${comparisonId.slice(0,8)}-${currentStudy.id.slice(0,8)}.json`;
    $('comparison-status').textContent='Both saved runs verified. Loaded displacement change: '+difference.toFixed(3)+'%. Changes cannot be attributed to geometry alone.';$('comparison').hidden=false;
  }catch(error){if(ticket!==selection || error.name==='AbortError')return;$('comparison-status').textContent='Comparison unavailable: '+error.message;}
}
$('pin-comparison').onclick=()=>{if(!currentStudy)return;comparisonId=currentStudy.id;$('comparison').hidden=true;showComparison(selection,activeRequest.signal);};
$('clear-comparison').onclick=()=>{comparisonId=null;$('comparison').hidden=true;$('comparison-rows').replaceChildren();showComparison(selection,activeRequest.signal);};

$('select-comparison-json').onclick=()=>{$('comparison-json').focus();$('comparison-json').select();};

let failureRequest;
$('failure-dialog').addEventListener('close',()=>failureRequest?.abort());
$('show-failures').onclick=async()=>{
  failureRequest?.abort();const controller=new AbortController();failureRequest=controller;
  $('failure-list').replaceChildren();$('failure-status').textContent='Loading retained failures…';$('failure-dialog').showModal();
  try{
    const data=await request('/failures?limit=50',{signal:controller.signal});if(failureRequest!==controller || !$('failure-dialog').open)return;
    $('failure-status').textContent=data.items.length?`${data.items.length} recent retained failures`:'No retained failure records.';
    for(const failure of data.items){
      const item=document.createElement('section');item.className='failure-item';
      const title=document.createElement('h3');title.textContent=({'bracket_structural':'Bracket analysis','geometry':'Geometry generation'}[failure.stage]||'Failed run')+' · '+failure.run_id.slice(0,8);item.appendChild(title);
      for(const text of [failure.reason,failure.run_id,'Retained '+new Date(failure.retained_at_epoch*1000).toLocaleString(),...(failure.parent_id?['Parent design: '+failure.parent_id]:[])]){const p=document.createElement('p');p.className='hint';p.textContent=text;item.appendChild(p);}
      if(/^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(failure.run_id)){
        for(const [name,label] of [['failure.json','Download failure record'],...(failure.has_solver_archive?[['failed-solver-artifacts.zip','Download solver diagnostics']]:[])]){const link=document.createElement('a');link.href=`/api/artifacts/${failure.run_id}/${name}`;link.download='';link.textContent=label;item.appendChild(link);}
      }
      if(failure.parent_id && /^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(failure.parent_id)){
        const open=document.createElement('button');open.textContent='Open parent design';open.onclick=()=>{$('failure-dialog').close();selectRun(failure.parent_id);};item.appendChild(open);
      }
      $('failure-list').appendChild(item);
    }
  }catch(error){if(error.name!=='AbortError' && failureRequest===controller)$('failure-status').textContent=error.message;}
};

$('select-comparison-markdown').onclick=()=>{$('comparison-markdown').focus();$('comparison-markdown').select();};

$('select-study-report').onclick=()=>{$('study-report-text').focus();$('study-report-text').select();};

async function watchServiceOperation(job){
  serviceBusy=true;updateCreation();$('service-status').textContent=({start:'Starting engineering services…',stop:'Stopping engineering services…',voice_start:'Starting local voice…',voice_stop:'Stopping local voice…',ai_start:'Starting local AI…',ai_stop:'Stopping local AI…'})[job.action];
  try{
    const deadline=Date.now()+510000;
    let result;
    do{
      await new Promise(resolve=>setTimeout(resolve,1000));
      result=await request('/services/control/'+job.job_id);
      if(result.status==='failed')throw new Error(result.message);
      if(Date.now()>deadline)throw new Error('Operation is still pending. Refresh service status before trying again.');
    }while(result.status==='pending');
    await refresh();$('service-status').textContent=({start:'Engineering services started.',stop:'Engineering services stopped. Saved runs remain available.',voice_start:'Local voice started.',voice_stop:'Local voice stopped.',ai_start:'Local AI started.',ai_stop:'Local AI stopped.'})[job.action];
  }catch(error){controlAvailable=false;$('service-status').textContent=error.message+' Refresh to reconnect.';}
  finally{serviceBusy=false;updateCreation();}
}
async function changeServices(action){
  if(serviceBusy || creating)return;
  serviceBusy=true;updateCreation();
  try{
    const job=await request('/services/control',{method:'POST',headers:{'Content-Type':'application/json','X-KCEE-Control':'1'},body:JSON.stringify({action,confirm_stop:action==='stop' || action==='voice_stop' || action==='ai_stop'})});
    await watchServiceOperation({...job,action});
  }catch(error){serviceBusy=false;controlAvailable=false;$('service-status').textContent=error.message+' Refresh service status.';updateCreation();}
}
$('start-services').onclick=()=>changeServices('start');
$('stop-services').onclick=()=>$('stop-services-dialog').showModal();
$('cancel-stop-services').onclick=()=>$('stop-services-dialog').close();
$('confirm-stop-services').onclick=()=>{$('stop-services-dialog').close();changeServices('stop');};
$('stop-services-dialog').addEventListener('close',()=>$('stop-services').focus());

setInterval(()=>{if(!document.hidden)refreshServiceStatus();},10000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshServiceStatus();});

$('prepare-voice').onclick=async()=>{
  if(!currentStudy || voiceBusy || serviceBusy || !voiceAvailable)return;
  const study=currentStudy,ticket=selection;voiceRequest?.abort();const controller=new AbortController();voiceRequest=controller;voiceBusy=true;updateCreation();$('voice-status').textContent='Preparing local voice summary…';
  try{
    const job=await request(`/runs/${study.id}/voice`,{method:'POST',headers:{'X-KCEE-Voice':'1'},signal:controller.signal});
    let result;const deadline=Date.now()+150000;
    do{
      await new Promise(resolve=>setTimeout(resolve,1000));if(controller.signal.aborted)return;
      result=await request('/voice/jobs/'+job.job_id,{signal:controller.signal});
      if(result.status==='failed')throw new Error(result.message);
      if(Date.now()>deadline)throw new Error('Voice preparation timed out.');
    }while(result.status==='pending');
    if(result.run_id!==study.id || result.summary_sha256!==study.record.manifest.artifacts['voice-summary.json'])throw new Error('Voice summary source mismatch');
    const response=await fetch('/api/voice/jobs/'+job.job_id+'/audio',{signal:controller.signal});if(!response.ok)throw new Error('Voice audio unavailable');
    const bytes=await response.arrayBuffer();const digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(value=>value.toString(16).padStart(2,'0')).join('');
    if(digest!==result.audio_sha256)throw new Error('Voice audio integrity mismatch');
    if(ticket!==selection)return;
    const evidence=voiceEvidence(study,result,digest);
    if(voiceEvidenceUrl)URL.revokeObjectURL(voiceEvidenceUrl);$('voice-evidence-text').value=JSON.stringify(evidence,null,2);voiceEvidenceUrl=URL.createObjectURL(new Blob([$('voice-evidence-text').value],{type:'application/json'}));$('download-voice-evidence').href=voiceEvidenceUrl;$('download-voice-evidence').download=`kcee-voice-${study.id.slice(0,8)}.json`;
    if(voiceUrl)URL.revokeObjectURL(voiceUrl);voiceUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/wav'}));$('voice-audio').src=voiceUrl;$('voice-audio').hidden=false;$('download-voice').href=voiceUrl;$('download-voice').download=`kcee-voice-${study.id.slice(0,8)}.wav`;$('voice-downloads').hidden=false;$('voice-status').textContent='Verified local Kokoro summary ready. Press Play to listen.';
  }catch(error){if(ticket===selection && error.name!=='AbortError')$('voice-status').textContent=error.message;}
  finally{if(voiceRequest===controller){voiceBusy=false;updateCreation();}}
};

$('toggle-voice').onclick=()=>{if(voiceAvailable)$('stop-voice-dialog').showModal();else changeServices('voice_start');};
$('cancel-stop-voice').onclick=()=>$('stop-voice-dialog').close();
$('confirm-stop-voice').onclick=()=>{$('stop-voice-dialog').close();$('voice-audio').pause();changeServices('voice_stop');};
$('stop-voice-dialog').addEventListener('close',()=>$('toggle-voice').focus());

$('select-voice-evidence').onclick=()=>{$('voice-evidence-text').focus();$('voice-evidence-text').select();};

$('toggle-ai').onclick=()=>{if(assistantAvailable)$('stop-ai-dialog').showModal();else changeServices('ai_start');};
$('cancel-stop-ai').onclick=()=>$('stop-ai-dialog').close();
$('confirm-stop-ai').onclick=()=>{$('stop-ai-dialog').close();changeServices('ai_stop');};
$('stop-ai-dialog').addEventListener('close',()=>$('toggle-ai').focus());
$('ask-assistant').onclick=async()=>{
  if(!currentStudy || assistantBusy || serviceBusy || !assistantAvailable)return;
  const question=$('assistant-question').value.trim();if(!question){$('assistant-status').textContent='Enter a question about this study.';return;}
  clearAssistantExport();const study=currentStudy,ticket=selection,documentScope=$('assistant-documents').checked?[...assistantDocumentScope]:[];assistantRequest?.abort();const controller=new AbortController();assistantRequest=controller;assistantBusy=true;updateCreation();$('assistant-answer').textContent='';$('assistant-sources').textContent='';$('assistant-status').textContent='Reading verified evidence and preparing a local explanation…';
  try{
    const job=await request(`/runs/${study.id}/assistant`,{method:'POST',headers:{'Content-Type':'application/json','X-KCEE-Assistant':'1'},body:JSON.stringify({question,include_documents:$("assistant-documents").checked,...scopeRequest(documentScope)}),signal:controller.signal});
    let result;const deadline=Date.now()+170000;
    do{await new Promise(resolve=>setTimeout(resolve,1000));if(controller.signal.aborted)return;result=await request('/assistant/jobs/'+job.job_id,{signal:controller.signal});if(result.status==='failed')throw new Error(result.message);if(Date.now()>deadline)throw new Error('Local explanation timed out.');}while(result.status==='pending');
    const source=result.evidence.source;if(source.run_id!==study.id || source.manifest_sha256!==study.record.manifest_sha256 || source.result_sha256!==study.record.manifest.artifacts['result.json'] || result.evidence_sha256!==job.evidence_sha256)throw new Error('AI evidence source mismatch');
    await verifyAssistantEvidence(result);
    if(!scopeMatches(documentScope,result.evidence))throw new Error('AI document scope mismatch');
    if(ticket!==selection)return;
    $('assistant-answer').textContent=result.answer.answer;
    const answerRecord={schema:'kcee.local-ai-answer.v1',...result};$('assistant-evidence-text').value=JSON.stringify(answerRecord,null,2);assistantEvidenceUrl=URL.createObjectURL(new Blob([$('assistant-evidence-text').value],{type:'application/json'}));$('download-assistant').href=assistantEvidenceUrl;$('download-assistant').download=`kcee-ai-${study.id.slice(0,8)}-${job.job_id.slice(0,8)}.json`;$('assistant-downloads').hidden=false;
    const readableAnswer=['KCEE local AI answer — draft','Engineering acceptance remains pending. Check this answer against the recorded study evidence.','','Document scope',scopeDescription(result.evidence),'','Question',result.question,'','Answer',result.answer.answer,'','Referenced evidence categories',result.answer.source_keys.join(', '),'','Document references',...(result.evidence.documents||[]).filter(chunk=>(result.answer.document_citations||[]).includes(chunk.citation_id)).map(chunk=>'['+chunk.citation_id+'] '+chunk.name+(chunk.page_number?' page '+chunk.page_number+(chunk.extraction_method==='ocr'?' (OCR)':''):' lines '+chunk.line_start+'-'+chunk.line_end)+'; source SHA-256 '+chunk.source_sha256+'; passage SHA-256 '+chunk.chunk_sha256),'','Study: '+source.run_id,'Study manifest SHA-256: '+source.manifest_sha256,'Result SHA-256: '+source.result_sha256,'Supplied evidence SHA-256: '+result.evidence_sha256,'Job: '+result.job_id,'Model: '+result.model,'Model SHA-256: '+result.model_sha256,'Runtime manifest SHA-256: '+result.runtime_manifest_sha256,'Prompt SHA-256: '+result.system_prompt_sha256,'Generation settings: '+JSON.stringify(result.generation_settings),'','The companion JSON record contains the complete evidence snapshot.',''].join('\n');assistantTextUrl=URL.createObjectURL(new Blob([readableAnswer],{type:'text/plain;charset=utf-8'}));$('download-assistant-text').href=assistantTextUrl;$('download-assistant-text').download=`kcee-ai-${study.id.slice(0,8)}-${job.job_id.slice(0,8)}.txt`;
    if(result.evidence.document_search)$('assistant-documents-note').textContent=result.evidence.document_search.matches?'Retrieved '+result.evidence.document_search.matches+' verified passages by '+(result.evidence.document_search.semantic_embeddings?'local semantic and keyword search':'local keyword search')+'. Model-cited passages appear below.':'No local document passages matched this question.';
    if(answerScopes(result.evidence).length)$('assistant-documents-note').textContent='Selected references: '+answerScopes(result.evidence).map(s=>s.name+(s.page_range?' (physical pages '+s.page_range.start+'–'+s.page_range.end+')':' (all pages)')).join(', ')+'. '+$('assistant-documents-note').textContent+(result.evidence.document_search.sources?' '+result.evidence.document_search.sources.map(s=>s.name+': '+s.included_matches+' included / '+s.available_matches+' matching passages').join('; '):'');
    for(const citation of result.answer.document_citations||[]){const chunk=result.evidence.documents.find(item=>item.citation_id===citation);if(!chunk)throw new Error('Document citation source mismatch');const detail=document.createElement('details'),summary=document.createElement('summary'),excerpt=document.createElement('pre'),hash=document.createElement('p'),download=document.createElement('a');summary.textContent='['+citation+'] '+chunk.name+(chunk.page_number?' · page '+chunk.page_number+(chunk.extraction_method==='ocr'?' · OCR — verify text':''):' · lines '+chunk.line_start+'–'+chunk.line_end);excerpt.textContent=chunk.content;hash.textContent='Source SHA-256: '+chunk.source_sha256+' · Passage SHA-256: '+chunk.chunk_sha256;hash.className='hint';download.textContent='Download original source';download.href='/api/knowledge/documents/'+chunk.document_id+'/source';download.download=chunk.name;detail.append(summary,excerpt,hash,download);appendPdfPageLink(detail,chunk);$('assistant-document-citations').appendChild(detail);}
    const names={validation:'Validation status',assumptions:'Model assumptions',mesh_results:'Saved mesh results',diagnostics:'Numerical diagnostics',explorations:'Separate exploratory investigations',documents:'Local document references'};
    $('assistant-sources').textContent='Referenced evidence: '+(result.answer.source_keys.map(key=>names[key]||key).join(', ')||'No measurement category cited')+'.';assistantStatusPinned=true;$('assistant-status').textContent='Local AI draft. Check it against the recorded results; engineering acceptance remains pending.';
  }catch(error){if(ticket===selection && error.name!=='AbortError'){assistantStatusPinned=true;$('assistant-status').textContent=error.message;}}
  finally{if(assistantRequest===controller){assistantBusy=false;updateCreation();}}
};

$('select-assistant-evidence').onclick=()=>{$('assistant-evidence-text').focus();$('assistant-evidence-text').select();};

const cfdStudyQuestions={'question-displacement':'Explain the finest-grid flow per unit span, mean velocity and wall shear of this selected channel case using its recorded inputs and units.','question-stress':'What do the Reynolds number, fully developed assumptions and numerical checks establish, and what remains unverified for this channel case?','question-refinement':'Compare the saved channel grids using their recorded flow errors and convergence orders. Explain what the analytical comparison verifies.'};
const thermalStudyQuestions={"question-displacement":"What temperatures were computed in this selected thermal study? Distinguish imposed end temperatures from computed values, and explain the limitations.","question-stress":"Explain the heat balance of this selected thermal study using its recorded heat values and checks.","question-refinement":"How do the saved thermal meshes compare? Use their recorded numerical values and explain what the refinement checks do and do not establish."};
const suggestedStudyQuestions={"question-displacement":"What is the loaded-patch displacement in the selected original study’s finest saved mesh? Explain what it means and any limitations.","question-stress":"Why is stress convergence not established for this selected study, even though its numerical checks passed? Use its recorded evidence.","question-refinement":"Compare the separate exploratory refinement investigations with the selected original study. Clearly label which values come from each, and explain what remains unresolved."};
for(const [id,question] of Object.entries(suggestedStudyQuestions))$(id).onclick=()=>{if(assistantBusy || !currentStudy)return;$("assistant-question").value=currentStudy.result.kind==='cfd_benchmark'?cfdStudyQuestions[id]:currentStudy.result.kind==='bracket_structural'?question:thermalStudyQuestions[id];$("assistant-question").focus();};

$('thermal-benchmark').onclick=async()=>{creating=true;updateCreation();beginSelection();selectedId=null;badge('integrity','Solving thermal benchmark…');$('status').textContent='Checking four thermal meshes against the analytical solution…';try{const data=await request('/runs/thermal-benchmark',{method:'POST'});offset=0;await refresh();await selectRun(data.run_id);}catch(error){badge('integrity','Thermal benchmark failed','error');$('status').textContent=error.message;}finally{creating=false;updateCreation();}};

$('analyze-thermal').onclick=async()=>{if(!selectedId)return;const parent=selectedId;creating=true;updateCreation();beginSelection();badge('integrity','Solving bracket temperature…');$('status').textContent='Meshing the actual bracket and solving three steady thermal grids…';try{const data=await request(`/runs/${parent}/thermal`,{method:'POST'});offset=0;await refresh();await selectRun(data.run_id);}catch(error){badge('integrity','Thermal analysis failed','error');$('status').textContent=error.message;}finally{creating=false;updateCreation();}};

document.addEventListener('kcee-study-question',event=>{const question=event.detail?.question;if(!currentStudy||!selectedVerified||assistantBusy||creating||typeof question!=='string'||!question.trim()||question.length>800)return;const sources=handoffSources(event.detail);if(!sources)return;$('assistant-question').value=question;$('assistant-documents').checked=true;assistantDocumentScope=sources;$('assistant-document-scope').textContent=assistantDocumentScope.length?'Reference scope: '+assistantDocumentScope.map(s=>s.name+(s.page_range?' (physical pages '+s.page_range.start+'–'+s.page_range.end+')':' (all pages)')).join(', ')+' only.':'Reference scope: all active documents.';$('assistant-all-documents').hidden=!assistantDocumentScope.length;clearAssistantExport();$('assistant-answer').textContent='';$('assistant-sources').textContent='';$('assistant-status').textContent='Question ready. '+(assistantDocumentScope.length?'Only the selected references will be searched. ':'All active document references are enabled. ')+'Review it and choose Ask local AI.';event.preventDefault();});

installEngineeringWorkflow({getSelected:()=>workflowStudy,getBusy:()=>creating||serviceBusy||assistantBusy,runAction:id=>$(id).onclick(),selectRun});

$('run-cfd-benchmark').onclick=async()=>{if(creating||serviceBusy||!cfdAvailable)return;creating=true;updateCreation();beginSelection();selectedId=null;badge('integrity','Solving channel flow…');$('status').textContent='Verifying four finite-volume grids against plane Poiseuille flow…';try{const inputs={gap_m:Number($('cfd-gap').value),pressure_gradient_Pa_m:Number($('cfd-gradient').value),dynamic_viscosity_Pa_s:Number($('cfd-viscosity').value),density_kg_m3:Number($('cfd-density').value),display_length_m:Number($('cfd-length').value)};for(const id of ['cfd-gap','cfd-gradient','cfd-viscosity','cfd-density','cfd-length'])if(!$(id).value.trim()||!$(id).checkValidity())throw new Error('Check channel inputs and their displayed limits.');const data=await request('/runs/cfd-benchmark',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(inputs)});offset=0;await refresh();await selectRun(data.run_id);}catch(error){badge('integrity','CFD benchmark failed','error');$('status').textContent=error.message;}finally{creating=false;updateCreation();}};

$('cfd-reset').onclick=()=>{for(const [id,value] of [['cfd-gap',.01],['cfd-gradient',.1],['cfd-viscosity',.001],['cfd-density',1000],['cfd-length',.2]])$(id).value=value;};

$('run-cfd-vortex').onclick=async()=>{if(creating||serviceBusy||!vortexAvailable)return;creating=true;updateCreation();beginSelection();selectedId=null;badge('integrity','OpenFOAM solving…');$('status').textContent='Solving three meshes at Δt = 0.005 s and four time steps on the 64² mesh. Six distinct OpenFOAM cases are verified; one case is shared. This may take a minute.';try{const data=await request('/runs/cfd-vortex',{method:'POST'});offset=0;await refresh();await selectRun(data.run_id);}catch(error){badge('integrity','OpenFOAM verification failed','error');$('status').textContent=error.message;}finally{creating=false;updateCreation();}};

$('analyze-flow').onclick=async()=>{if(!selectedId||creating||serviceBusy||!bracketFlowAvailable||!selectedIsNative)return;const parent=selectedId;creating=true;updateCreation();beginSelection();badge('integrity','Meshing bracket flow…');$('status').textContent='Preparing the actual native surface, generating an external fluid mesh and running 1,500 laminar SIMPLE iterations. This may take a minute.';try{const data=await request('/runs/'+parent+'/flow',{method:'POST'});offset=0;await refresh();await selectRun(data.run_id);}catch(error){badge('integrity','Bracket flow failed','error');$('status').textContent=error.message;}finally{creating=false;updateCreation();}};

$('verify-bracket-flow').onclick=async()=>{if(!flowSourceId||creating||serviceBusy||!bracketFlowAvailable)return;const parent=flowSourceId;creating=true;updateCreation();beginSelection();badge('integrity','Verifying three flow meshes…');$('status').textContent='Saving coarse, medium and fine flow studies, checking actual bore wall faces and comparing physical probe samples. This may take several minutes.';try{const data=await request('/runs/'+parent+'/flow-refinement',{method:'POST'});offset=0;await refresh();await selectRun(data.run_id);}catch(error){badge('integrity','Flow refinement incomplete','error');$('status').textContent=error.message;}finally{creating=false;updateCreation();}};

$('verify-flow-domain').onclick=async()=>{if(!flowSourceId||creating||serviceBusy||!bracketFlowAvailable)return;const parent=flowSourceId;creating=true;updateCreation();beginSelection();badge('integrity','Checking boundary distances…');$('status').textContent='Verifying or running the base case, then expanded and far domains at fixed medium spacing. This may take several minutes.';try{const data=await request('/runs/'+parent+'/flow-domains',{method:'POST'});offset=0;await refresh();await selectRun(data.run_id);}catch(error){badge('integrity','Domain study incomplete','error');$('status').textContent=error.message;}finally{creating=false;updateCreation();}};

$('verify-flow-combined').onclick=async()=>{if(!flowSourceId||creating||serviceBusy||!bracketFlowAvailable)return;const parent=flowSourceId;creating=true;updateCreation();beginSelection();badge('integrity','Combined CFD verification…');$('status').textContent='Reusing compatible compact-sampled cases where verified; solving any missing far-domain meshes. This may take several minutes.';try{const data=await request('/runs/'+parent+'/flow-combined',{method:'POST'});offset=0;await refresh();await selectRun(data.run_id);}catch(error){badge('integrity','Combined verification incomplete','error');$('status').textContent=error.message;}finally{creating=false;updateCreation();}};
