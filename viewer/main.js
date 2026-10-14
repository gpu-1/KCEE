import './knowledge-ui.js';
import {drawThermalChart} from './thermal-chart.js';
import * as THREE from 'three';
import {STLLoader} from 'three/addons/loaders/STLLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {request, loadRun, artifactUrl, comparisonEvidence, comparisonMarkdown, studyMarkdown, numericalCheckRows, voiceEvidence} from './client.js';
const $=id=>document.getElementById(id);
const structuralBoundaryLegend=$("boundary-legend").textContent;
let studyReportUrl=null,assistantEvidenceUrl=null,assistantTextUrl=null;
function clearAssistantExport(){$("assistant-documents-note").textContent="";$("assistant-document-citations").replaceChildren();if(assistantTextUrl)URL.revokeObjectURL(assistantTextUrl);assistantTextUrl=null;$("download-assistant-text").removeAttribute("href");if(assistantEvidenceUrl)URL.revokeObjectURL(assistantEvidenceUrl);assistantEvidenceUrl=null;$("assistant-downloads").hidden=true;$("download-assistant").removeAttribute("href");$("assistant-evidence-text").value="";$("assistant-evidence-view").open=false;}
let comparisonId=null,currentStudy=null,comparisonUrl=null,comparisonMarkdownUrl=null;
function clearComparisonExport(){if(comparisonMarkdownUrl)URL.revokeObjectURL(comparisonMarkdownUrl);comparisonMarkdownUrl=null;$("download-comparison-markdown").removeAttribute("href");$("comparison-markdown").value="";$("comparison-markdown-view").open=false;if(comparisonUrl)URL.revokeObjectURL(comparisonUrl);comparisonUrl=null;$("comparison-json").value="";$("comparison-json-view").open=false;$("download-comparison").removeAttribute("href");}
let selectedIsThermal=false;
let fieldData=null, sourceStl=null, archiveDigest=null;
let mesh, renderer, controls, camera, scene, boundaryMarkers;
let modelCenter=new THREE.Vector3(),isBracketStudy=false;
let pendingRemoval=null,removing=false,selectedVerified=false;
let selection=0, activeRequest, listRequest, offset=0, selectedId=null;
const PAGE_SIZE=10;
let assistantAvailable=false,assistantBusy=false,assistantRequest=null,assistantStatusPinned=false;
let serviceBusy=false,controlAvailable=false,voiceAvailable=false,voiceBusy=false,voiceRequest=null,voiceUrl=null,voiceEvidenceUrl=null;
let nativeAvailable=false,creating=false,structuralAvailable=false,thermalAvailable=false,selectedIsNative=false;
function updateServiceButtons(){$("toggle-ai").disabled=!controlAvailable || serviceBusy || assistantBusy || creating;$("toggle-ai").textContent=assistantAvailable?"Stop":"Start";$("toggle-ai").setAttribute("aria-label",assistantAvailable?"Stop local AI":"Start local AI");$("toggle-voice").disabled=!controlAvailable || serviceBusy || voiceBusy || creating;$("toggle-voice").textContent=voiceAvailable?"Stop":"Start";$("toggle-voice").setAttribute("aria-label",voiceAvailable?"Stop local voice":"Start local voice");$("start-services").disabled=!controlAvailable || serviceBusy || creating || (nativeAvailable && structuralAvailable && thermalAvailable);$("stop-services").disabled=!controlAvailable || serviceBusy || creating || (!nativeAvailable && !structuralAvailable && !thermalAvailable);}
function updateCreation(){$("assistant-documents").disabled=assistantBusy || serviceBusy || !currentStudy;$("analyze-thermal").disabled=creating || serviceBusy || !structuralAvailable || !selectedIsNative;$("thermal-benchmark").disabled=creating || serviceBusy || !thermalAvailable; updateServiceButtons();for(const id of ["question-displacement","question-stress","question-refinement"])$(id).disabled=assistantBusy || !currentStudy;$("ask-assistant").disabled=!assistantAvailable || assistantBusy || serviceBusy || !currentStudy;$("prepare-voice").disabled=!voiceAvailable || voiceBusy || serviceBusy || !currentStudy; $("remove-run").disabled=(creating || serviceBusy) || removing || !selectedVerified; $("fea").disabled=(creating || serviceBusy) || !structuralAvailable; $("analyze").disabled=(creating || serviceBusy) || !structuralAvailable || !selectedIsNative; $("create").disabled=(creating || serviceBusy) || ($("backend").value==="picogk" && !nativeAvailable); }
$("backend").onchange=updateCreation;
function badge(id,text,kind=''){ $(id).textContent=text; $(id).className='badge '+kind; }
function clearModel(){if(boundaryMarkers){scene.remove(boundaryMarkers);boundaryMarkers.traverse(object=>{object.geometry?.dispose();if(Array.isArray(object.material))object.material.forEach(m=>m.dispose());else object.material?.dispose();});boundaryMarkers=null;} if(mesh){scene.remove(mesh);mesh.geometry.dispose();mesh.material.dispose();mesh=null;} $('empty').hidden=false; $('fit').disabled=true; $('wireframe').disabled=true; }
function configureAssistantQuestions(thermal){$("question-displacement").textContent=thermal?"Temperatures":"Displacement";$("question-stress").textContent=thermal?"Heat balance":"Stress convergence";$("question-refinement").textContent="Refinement";}
function clearDetails(){$("assistant-documents").checked=false;configureAssistantQuestions(false);$("boundary-toggle-label").textContent="Load & support";$("boundary-legend").textContent=structuralBoundaryLegend;selectedIsThermal=false;$("bracket-thermal-results").hidden=true;$("bracket-thermal-checks").replaceChildren();$("bracket-thermal-rows").replaceChildren();$("bracket-thermal-csv").removeAttribute("href");$("thermal-checks").replaceChildren();$("thermal-charts").replaceChildren();$("thermal-mesh").replaceChildren();$("thermal-mesh").onchange=null;$("thermal-results").hidden=true;$("thermal-rows").replaceChildren();$("thermal-profile").removeAttribute("href");clearAssistantExport();assistantRequest?.abort();assistantRequest=null;assistantBusy=false;assistantStatusPinned=false;$("study-assistant").hidden=true;$("assistant-answer").textContent="";$("assistant-sources").textContent="";$("assistant-question").value="";if(voiceEvidenceUrl)URL.revokeObjectURL(voiceEvidenceUrl);voiceEvidenceUrl=null;$("download-voice-evidence").removeAttribute("href");$("voice-evidence-text").value="";$("voice-evidence-view").open=false;$("voice-downloads").hidden=true;$("download-voice").removeAttribute("href");voiceRequest?.abort();voiceRequest=null;voiceBusy=false;$("voice-audio").pause();$("voice-audio").removeAttribute("src");$("voice-audio").load();$("voice-audio").hidden=true;if(voiceUrl)URL.revokeObjectURL(voiceUrl);voiceUrl=null;$("prepare-voice").disabled=true;$("refinement-explorations").hidden=true;$("exploration-rows").replaceChildren();$("exploration-evidence").value="";if(studyReportUrl)URL.revokeObjectURL(studyReportUrl);studyReportUrl=null;$("readable-study").hidden=true;$("study-report-text").value="";$("study-report-view").open=false;$("download-study-report").removeAttribute("href");clearComparisonExport();currentStudy=null;$('pin-comparison').disabled=true;$('comparison').hidden=true;$('comparison-rows').replaceChildren();$('stress-diagnostics').hidden=true;$('hotspot-values').replaceChildren();$('geometry-measurements').hidden=true;$('hole-values').replaceChildren();selectedVerified=false;$('remove-run').disabled=true;isBracketStudy=false;$("boundaries").checked=false;$("boundaries").disabled=true;$("boundary-legend").hidden=true;fieldData=null;sourceStl=null;archiveDigest=null;$('field').checked=false;$('field').disabled=true;$('scale-label').hidden=true;$('quantity-label').hidden=true;$('field-legend').hidden=true; selectedIsNative=false;$("analyze").disabled=true; $('result-title').textContent='Screening result';$('mesh-study').hidden=true;$('mesh-rows').replaceChildren();$('validation-checks').hidden=true;$('check-values').replaceChildren(); $('result').hidden=true;$('result-empty').hidden=false;$('metrics').replaceChildren();$('provenance').replaceChildren();$('assumptions').replaceChildren();$('solver-files').hidden=true;$('solver-files').removeAttribute('href');for(const id of ['report','manifest'])$(id).removeAttribute('href'); }
function beginSelection(){ selection++;activeRequest?.abort();activeRequest=new AbortController();clearModel();clearDetails();return {ticket:selection,signal:activeRequest.signal}; }
function addMetric(list,label,value){ const dt=document.createElement('dt'), dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;$(list).append(dt,dd); }
function fitModel(){
  if(!mesh)return;const r=mesh.geometry.boundingSphere.radius;
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
  new ResizeObserver(()=>{const width=$('viewport').clientWidth,height=$('viewport').clientHeight;renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();}).observe($('viewport'));
  renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera);});
} catch {renderer=null;$('empty').textContent='3D rendering unavailable. Run history and reports remain accessible.';}
function highlight(){for(const button of $('runs').querySelectorAll('button'))button.setAttribute('aria-current',String(button.dataset.id===selectedId));}
async function selectRun(id){
  let sourceLoadWarning=false,verifiedDiagnostic=null,verifiedExploration=null;
  const {ticket,signal}=beginSelection();selectedId=id;highlight();$('model-title').textContent='Bracket '+id.slice(0,8);badge('integrity','Verifying…');$('status').textContent='Checking provenance and downloading geometry…';
  try {
    const {record,result,stl}=await loadRun(id,signal);if(ticket!==selection)return;
    $('model-title').textContent=(result.kind==='bracket_thermal'?'Bracket thermal ':result.kind==='thermal_benchmark'?'Thermal benchmark ':result.kind==='structural_benchmark'?'Cantilever benchmark ':result.kind==='bracket_structural'?'Bracket FEA ':'Bracket ')+id.slice(0,8);
    selectedVerified=true;$('remove-run').disabled=(creating || serviceBusy) || removing;$('remove-run').textContent=$('show-removed').checked?'Restore to list':'Remove from list';
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
    selectedIsNative=result.geometry_backend.startsWith('PicoGK');updateCreation();
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
      thermalAvailable=Boolean(capabilities.thermal?.steady_1d);$('thermal-status').textContent=thermalAvailable?'Thermal worker ready · 1D verification':'Thermal worker stopped or unavailable.';
      controlAvailable=control.available;
      nativeAvailable=Boolean(capabilities.geometry?.picogk);structuralAvailable=Boolean(capabilities.structural?.calculix);
      badge('service-health',nativeAvailable || structuralAvailable || thermalAvailable?'On':'Off',nativeAvailable && structuralAvailable && thermalAvailable?'good':'');
      $('service-health').title=[nativeAvailable?'PicoGK On':'PicoGK Off',structuralAvailable?'Structural On':'Structural Off',thermalAvailable?'Thermal On':'Thermal Off'].join(' · ');
      $('native-status').textContent=nativeAvailable?'Native PicoGK ready':'Native PicoGK stopped or unavailable.';
      $('fea-status').textContent=structuralAvailable?'CalculiX ready':'Structural worker stopped or unavailable.';
      if(control.operation?.status==='pending' && !serviceBusy)watchServiceOperation(control.operation);
      else if(control.operation && control.operation.status!=='pending'){
        controlAvailable=false;$('service-status').textContent='Service operation needs inspection on this Mac. Refresh after resolving it.';
      }else if(!serviceBusy)$('service-status').textContent=controlAvailable?'Service controls ready':'Local controls unavailable. Run the KCEE startup command on this Mac.';
    }catch{
      nativeAvailable=false;structuralAvailable=false;controlAvailable=false;voiceAvailable=false;assistantAvailable=false;
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
    for(const item of items){const button=document.createElement('button');button.className='run';button.dataset.id=item.id;button.textContent=(item.kind==='bracket_thermal'?'Bracket thermal ':item.kind==='thermal_benchmark'?'Thermal ':item.kind==='structural_benchmark'?'Cantilever ':item.kind==='bracket_structural'?'Bracket FEA ':'Bracket ')+item.id.slice(0,8);const small=document.createElement('small');small.textContent=new Date(item.created_at).toLocaleString();button.appendChild(small);button.onclick=()=>selectRun(item.id);$('runs').appendChild(button);}
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
  $('comparison-status').textContent=comparisonId?'Reference: '+comparisonId:'Select a bracket FEA study and use it as a reference, then select another study.';
  if(!comparisonId || !currentStudy || comparisonId===currentStudy.id)return;
  try{
    const referenceId=comparisonId;const reference=await loadRun(referenceId,signal);if(ticket!==selection || comparisonId!==referenceId)return;
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
  clearAssistantExport();const study=currentStudy,ticket=selection;assistantRequest?.abort();const controller=new AbortController();assistantRequest=controller;assistantBusy=true;updateCreation();$('assistant-answer').textContent='';$('assistant-sources').textContent='';$('assistant-status').textContent='Reading verified evidence and preparing a local explanation…';
  try{
    const job=await request(`/runs/${study.id}/assistant`,{method:'POST',headers:{'Content-Type':'application/json','X-KCEE-Assistant':'1'},body:JSON.stringify({question,include_documents:$("assistant-documents").checked}),signal:controller.signal});
    let result;const deadline=Date.now()+170000;
    do{await new Promise(resolve=>setTimeout(resolve,1000));if(controller.signal.aborted)return;result=await request('/assistant/jobs/'+job.job_id,{signal:controller.signal});if(result.status==='failed')throw new Error(result.message);if(Date.now()>deadline)throw new Error('Local explanation timed out.');}while(result.status==='pending');
    const source=result.evidence.source;if(source.run_id!==study.id || source.manifest_sha256!==study.record.manifest_sha256 || source.result_sha256!==study.record.manifest.artifacts['result.json'] || result.evidence_sha256!==job.evidence_sha256)throw new Error('AI evidence source mismatch');
    if(ticket!==selection)return;
    $('assistant-answer').textContent=result.answer.answer;
    const answerRecord={schema:'kcee.local-ai-answer.v1',...result};$('assistant-evidence-text').value=JSON.stringify(answerRecord,null,2);assistantEvidenceUrl=URL.createObjectURL(new Blob([$('assistant-evidence-text').value],{type:'application/json'}));$('download-assistant').href=assistantEvidenceUrl;$('download-assistant').download=`kcee-ai-${study.id.slice(0,8)}-${job.job_id.slice(0,8)}.json`;$('assistant-downloads').hidden=false;
    const readableAnswer=['KCEE local AI answer — draft','Engineering acceptance remains pending. Check this answer against the recorded study evidence.','','Question',result.question,'','Answer',result.answer.answer,'','Referenced evidence categories',result.answer.source_keys.join(', '),'','Document references',...(result.evidence.documents||[]).filter(chunk=>(result.answer.document_citations||[]).includes(chunk.citation_id)).map(chunk=>'['+chunk.citation_id+'] '+chunk.name+' lines '+chunk.line_start+'-'+chunk.line_end+'; source SHA-256 '+chunk.source_sha256+'; passage SHA-256 '+chunk.chunk_sha256),'','Study: '+source.run_id,'Study manifest SHA-256: '+source.manifest_sha256,'Result SHA-256: '+source.result_sha256,'Supplied evidence SHA-256: '+result.evidence_sha256,'Job: '+result.job_id,'Model: '+result.model,'Model SHA-256: '+result.model_sha256,'Runtime manifest SHA-256: '+result.runtime_manifest_sha256,'Prompt SHA-256: '+result.system_prompt_sha256,'Generation settings: '+JSON.stringify(result.generation_settings),'','The companion JSON record contains the complete evidence snapshot.',''].join('\n');assistantTextUrl=URL.createObjectURL(new Blob([readableAnswer],{type:'text/plain;charset=utf-8'}));$('download-assistant-text').href=assistantTextUrl;$('download-assistant-text').download=`kcee-ai-${study.id.slice(0,8)}-${job.job_id.slice(0,8)}.txt`;
    if(result.evidence.document_search)$('assistant-documents-note').textContent=result.evidence.document_search.matches?'Retrieved '+result.evidence.document_search.matches+' verified passages by '+(result.evidence.document_search.semantic_embeddings?'local semantic and keyword search':'local keyword search')+'. Model-cited passages appear below.':'No local document passages matched this question.';
    for(const citation of result.answer.document_citations||[]){const chunk=result.evidence.documents.find(item=>item.citation_id===citation);if(!chunk)throw new Error('Document citation source mismatch');const detail=document.createElement('details'),summary=document.createElement('summary'),excerpt=document.createElement('pre'),hash=document.createElement('p'),download=document.createElement('a');summary.textContent='['+citation+'] '+chunk.name+' · lines '+chunk.line_start+'–'+chunk.line_end;excerpt.textContent=chunk.content;hash.textContent='Source SHA-256: '+chunk.source_sha256+' · Passage SHA-256: '+chunk.chunk_sha256;hash.className='hint';download.textContent='Download original source';download.href='/api/knowledge/documents/'+chunk.document_id+'/source';download.download=chunk.name;detail.append(summary,excerpt,hash,download);$('assistant-document-citations').appendChild(detail);}
    const names={validation:'Validation status',assumptions:'Model assumptions',mesh_results:'Saved mesh results',diagnostics:'Numerical diagnostics',explorations:'Separate exploratory investigations',documents:'Local document references'};
    $('assistant-sources').textContent='Referenced evidence: '+(result.answer.source_keys.map(key=>names[key]||key).join(', ')||'No measurement category cited')+'.';assistantStatusPinned=true;$('assistant-status').textContent='Local AI draft. Check it against the recorded results; engineering acceptance remains pending.';
  }catch(error){if(ticket===selection && error.name!=='AbortError'){assistantStatusPinned=true;$('assistant-status').textContent=error.message;}}
  finally{if(assistantRequest===controller){assistantBusy=false;updateCreation();}}
};

$('select-assistant-evidence').onclick=()=>{$('assistant-evidence-text').focus();$('assistant-evidence-text').select();};

const thermalStudyQuestions={"question-displacement":"What temperatures were computed in this selected thermal study? Distinguish imposed end temperatures from computed values, and explain the limitations.","question-stress":"Explain the heat balance of this selected thermal study using its recorded heat values and checks.","question-refinement":"How do the saved thermal meshes compare? Use their recorded numerical values and explain what the refinement checks do and do not establish."};
const suggestedStudyQuestions={"question-displacement":"What is the loaded-patch displacement in the selected original study’s finest saved mesh? Explain what it means and any limitations.","question-stress":"Why is stress convergence not established for this selected study, even though its numerical checks passed? Use its recorded evidence.","question-refinement":"Compare the separate exploratory refinement investigations with the selected original study. Clearly label which values come from each, and explain what remains unresolved."};
for(const [id,question] of Object.entries(suggestedStudyQuestions))$(id).onclick=()=>{if(assistantBusy || !currentStudy)return;$("assistant-question").value=currentStudy.result.kind==='bracket_structural'?question:thermalStudyQuestions[id];$("assistant-question").focus();};

$('thermal-benchmark').onclick=async()=>{creating=true;updateCreation();beginSelection();selectedId=null;badge('integrity','Solving thermal benchmark…');$('status').textContent='Checking four thermal meshes against the analytical solution…';try{const data=await request('/runs/thermal-benchmark',{method:'POST'});offset=0;await refresh();await selectRun(data.run_id);}catch(error){badge('integrity','Thermal benchmark failed','error');$('status').textContent=error.message;}finally{creating=false;updateCreation();}};

$('analyze-thermal').onclick=async()=>{if(!selectedId)return;const parent=selectedId;creating=true;updateCreation();beginSelection();badge('integrity','Solving bracket temperature…');$('status').textContent='Meshing the actual bracket and solving three steady thermal grids…';try{const data=await request(`/runs/${parent}/thermal`,{method:'POST'});offset=0;await refresh();await selectRun(data.run_id);}catch(error){badge('integrity','Thermal analysis failed','error');$('status').textContent=error.message;}finally{creating=false;updateCreation();}};
