import * as THREE from 'three';
import {STLLoader} from 'three/addons/loaders/STLLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {request, loadRun, artifactUrl} from './client.js';
const $=id=>document.getElementById(id);
let fieldData=null, sourceStl=null, archiveDigest=null;
let mesh, renderer, controls, camera, scene;
let selection=0, activeRequest, listRequest, offset=0, selectedId=null;
const PAGE_SIZE=10;
let nativeAvailable=false,creating=false,structuralAvailable=false,selectedIsNative=false;
function updateCreation(){ $("fea").disabled=creating || !structuralAvailable; $("analyze").disabled=creating || !structuralAvailable || !selectedIsNative; $("create").disabled=creating || ($("backend").value==="picogk" && !nativeAvailable); }
$("backend").onchange=updateCreation;
function badge(id,text,kind=''){ $(id).textContent=text; $(id).className='badge '+kind; }
function clearModel(){ if(mesh){scene.remove(mesh);mesh.geometry.dispose();mesh.material.dispose();mesh=null;} $('empty').hidden=false; $('fit').disabled=true; $('wireframe').disabled=true; }
function clearDetails(){fieldData=null;sourceStl=null;archiveDigest=null;$('field').checked=false;$('field').disabled=true;$('scale-label').hidden=true;$('field-legend').hidden=true; selectedIsNative=false;$("analyze").disabled=true; $('result-title').textContent='Screening result';$('mesh-study').hidden=true;$('mesh-rows').replaceChildren(); $('result').hidden=true;$('result-empty').hidden=false;$('metrics').replaceChildren();$('provenance').replaceChildren();$('assumptions').replaceChildren();$('solver-files').hidden=true;$('solver-files').removeAttribute('href');for(const id of ['report','manifest'])$(id).removeAttribute('href'); }
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
  geometry.computeVertexNormals();geometry.center();geometry.computeBoundingSphere();const r=geometry.boundingSphere.radius;
  if(!Number.isFinite(r)||r<=0){geometry.dispose();throw new Error('STL has no usable extent');}
  mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:0x69cabc,roughness:.5,wireframe:$('wireframe').checked}));scene.add(mesh);
  fitModel();$('fit').disabled=false;$('wireframe').disabled=false;$('empty').hidden=true;
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
  const {ticket,signal}=beginSelection();selectedId=id;highlight();$('model-title').textContent='Bracket '+id.slice(0,8);badge('integrity','Verifying…');$('status').textContent='Checking provenance and downloading geometry…';
  try {
    const {record,result,stl}=await loadRun(id,signal);if(ticket!==selection)return;
    $('model-title').textContent=(result.kind==='structural_benchmark'?'Cantilever benchmark ':result.kind==='bracket_structural'?'Bracket FEA ':'Bracket ')+id.slice(0,8);
    const chosen=result.selected;
    for(const key of ['thickness_mm','stress_MPa','tip_deflection_mm','factor_of_safety'])if(!Number.isFinite(chosen?.[key]))throw new Error('Screening result contains invalid values');
    if(!Number.isFinite(result.mass_kg)||!Array.isArray(result.assumptions))throw new Error('Screening result is incomplete');
    archiveDigest=record.manifest.artifacts['fea-artifacts.zip'];sourceStl=stl;if(renderer)displayGeometry(stl);$('field').disabled=!renderer || result.kind!=='bracket_structural';
    addMetric('metrics','Selected thickness',chosen.thickness_mm.toFixed(1)+' mm');addMetric('metrics','Mass', (result.mass_kg*1000).toFixed(1)+' g');
    addMetric('metrics',result.kind==='bracket_structural'?'Ideal-cantilever stress':'Analytical stress',chosen.stress_MPa.toFixed(2)+' MPa');addMetric('metrics',result.kind==='bracket_structural'?'Ideal-cantilever estimate':'Estimated deflection',chosen.tip_deflection_mm.toFixed(3)+' mm');if(result.fea){const fine=result.fea.mesh_study.at(-1);addMetric('metrics',result.kind==='bracket_structural'?'FEA loaded-patch displacement':'FEA tip deflection',fine.tip_deflection_mm.toFixed(3)+' mm');if(result.kind==='bracket_structural'){addMetric('metrics','Source volume agreement error',(result.fea.relative_source_volume_error*100).toFixed(2)+'%');addMetric('metrics','Mesh peak stress · not converged',fine.maximum_von_mises_MPa.toFixed(2)+' MPa');}else addMetric('metrics','Analytical comparison error',(result.fea.relative_displacement_error*100).toFixed(2)+'%');addMetric('metrics','Last mesh displacement change',(result.fea.last_mesh_displacement_change*100).toFixed(2)+'%');addMetric('metrics','Support reaction',fine.reaction_z_N.toFixed(3)+' N');}else addMetric('metrics','Analytical factor of safety',chosen.factor_of_safety.toFixed(2));
    const displayedAssumptions=result.kind==='bracket_structural'?['Actual native PicoGK STL, including mounting holes and root transition',result.fea.boundary,result.fea.load,'Linear isotropic elasticity and small displacement; illustrative material properties',result.fea.stress_note,'Numerical checks do not establish engineering validation','Analytical estimates are separate ideal-cantilever references']:result.assumptions;
    for(const text of displayedAssumptions){const li=document.createElement('li');li.textContent=text;$('assumptions').appendChild(li);}
    addMetric('provenance','Run ID',record.id);if(record.parent_id)addMetric('provenance','Parent design',record.parent_id);addMetric('provenance','Created',new Date(record.created_at).toLocaleString());addMetric('provenance','Geometry',result.geometry_backend);addMetric('provenance','Structural model',result.structural_backend);addMetric('provenance','Validation status',record.validation_status);addMetric('provenance','Manifest SHA-256',record.manifest_sha256);
    selectedIsNative=result.geometry_backend.startsWith('PicoGK');updateCreation();
    if(result.fea){$('result-title').textContent=result.kind==='bracket_structural'?'Bracket structural study':'Cantilever verification';$('mesh-study').hidden=false;$('displacement-heading').textContent=result.kind==='bracket_structural'?'Loaded patch (mm)':'Tip (mm)';$('stress-heading').hidden=result.kind!=='bracket_structural';$('mesh-note').hidden=result.kind!=='bracket_structural';for(const mesh of result.fea.mesh_study){const row=document.createElement('tr');for(const value of [mesh.elements,mesh.tip_deflection_mm.toFixed(6),mesh.reaction_z_N.toFixed(4),...(result.kind==='bracket_structural'?[mesh.maximum_von_mises_MPa.toFixed(2)]:[])]){const cell=document.createElement('td');cell.textContent=value;row.appendChild(cell);}$('mesh-rows').appendChild(row);}$('solver-files').href=artifactUrl(id,'fea-artifacts.zip');$('solver-files').hidden=false;}
    $('report').href=artifactUrl(id,'report.md');$('manifest').href=artifactUrl(id,'manifest.json');$('result').hidden=false;$('result-empty').hidden=true;badge('integrity','Artifacts verified','good');$('status').textContent=(result.kind==='bracket_structural'?(Object.values(result.fea.checks).every(Boolean)?'Bracket numerical checks passed. Engineering validation remains pending.':'Bracket numerical checks need attention. No engineering acceptance.'):(result.fea?'Cantilever benchmark checks passed. Bracket validation remains pending.':'Artifact integrity verified. Analytical screening remains unvalidated.'))+(renderer?'':' 3D rendering is unavailable; reports are accessible.');
  } catch(error){if(ticket!==selection||error.name==='AbortError')return;clearModel();clearDetails();badge('integrity','Unable to verify','error');$('status').textContent=error.message;}
}
async function refresh(){
  listRequest?.abort();const controller=new AbortController();listRequest=controller;$('refresh').disabled=true;
  try {
    const [data,capabilities]=await Promise.all([request(`/runs?limit=${PAGE_SIZE+1}&offset=${offset}`,{signal:controller.signal}),request('/capabilities',{signal:controller.signal})]);
    if(listRequest!==controller)return;
    structuralAvailable=Boolean(capabilities.structural?.calculix);$('fea').disabled=creating || !structuralAvailable;$('fea-status').textContent=capabilities.structural?.calculix?'CalculiX benchmark ready':'Structural worker unavailable. Start the fea profile.';
    nativeAvailable=capabilities.geometry.picogk;$('native-status').textContent=nativeAvailable?'Native PicoGK ready':'Native worker unavailable. Start it on this Mac or choose the baseline mesh.';updateCreation();if(listRequest!==controller)return;
    $('runs').replaceChildren();const items=data.items.slice(0,PAGE_SIZE);
    for(const item of items){const button=document.createElement('button');button.className='run';button.dataset.id=item.id;button.textContent=(item.kind==='structural_benchmark'?'Cantilever ':item.kind==='bracket_structural'?'Bracket FEA ':'Bracket ')+item.id.slice(0,8);const small=document.createElement('small');small.textContent=new Date(item.created_at).toLocaleString();button.appendChild(small);button.onclick=()=>selectRun(item.id);$('runs').appendChild(button);}
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
  const points=[],colors=[],color=new THREE.Color();
  for(let i=0;i<data.positions.length;i++){
    const p=data.positions[i],u=data.displacements[i];points.push(...p.map((x,j)=>x+u[j]*scale));
    color.setHSL((1-Math.hypot(...u)/data.maximum_displacement_mm)*.66,1,.5);colors.push(color.r,color.g,color.b);
  }
  geometry.setAttribute('position',new THREE.Float32BufferAttribute(points,3));geometry.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));geometry.setIndex(data.triangles.flat());geometry.computeVertexNormals();geometry.center();geometry.computeBoundingSphere();
  mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({vertexColors:true,side:THREE.DoubleSide,wireframe:$('wireframe').checked}));scene.add(mesh);fitModel();$('empty').hidden=true;$('fit').disabled=false;$('wireframe').disabled=false;
  $('field-legend').textContent=`Displacement magnitude · blue 0 → red ${data.maximum_displacement_mm.toFixed(3)} mm · deformation ${scale}× · fine solver mesh surface`;
}
$('scale').onchange=renderField;
$('field').onchange=async()=>{
  const ticket=selection,id=selectedId;
  $('scale-label').hidden=!$('field').checked;$('field-legend').hidden=!$('field').checked;
  if(!$('field').checked){clearModel();displayGeometry(sourceStl);return;}
  $('field').disabled=true;
  try{
    if(!fieldData){const data=await request(`/runs/${id}/displacement-surface`,{signal:activeRequest.signal});if(ticket!==selection)return;if(data.source_archive_sha256!==archiveDigest)throw new Error('Field archive identity mismatch');fieldData=data;}
    renderField();
  }catch(error){if(ticket!==selection)return;$('field').checked=false;$('scale-label').hidden=true;$('field-legend').hidden=true;$('status').textContent='Displacement field unavailable: '+error.message;}
  finally{if(ticket===selection)$('field').disabled=false;}
};
