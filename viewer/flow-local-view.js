import {drawSensitivity} from './flow-combined-view.js';
export function localSeries(data){
 if(data?.schema!=='kcee.bracket-flow-local.v1')throw Error('Invalid local refinement evidence');
 const convert=rows=>rows.map(p=>{const velocity=p.maximum_velocity_change_normalized_by_inlet*100,pressure=p.maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale*100;if(![velocity,pressure].every(v=>Number.isFinite(v)&&v>=0))throw Error('Invalid local sensitivity');return {label:p.label,velocity,pressure};});
 return {mesh:convert(data.background_mesh_changes),local:convert(data.local_refinement_changes)};
}
export function localProbeRows(data,name){
 return data.studies.map(s=>{const p=s.probes.find(p=>p.name===name);if(!p||![p.speed_m_s,p.pressure_minus_upstream_m2_s2,p.maximum_support_distance_m].every(Number.isFinite))throw Error('Missing local probe');return {label:s.mesh_name+' / '+(s.local_profile==='baseline'?'baseline':'targeted'),speed:p.speed_m_s,pressure:p.pressure_minus_upstream_m2_s2,radius:p.maximum_support_distance_m*1000};});
}
export function mountLocal(data,openRun){
 const $=id=>document.getElementById(id),series=localSeries(data);drawSensitivity($('local-mesh-chart'),series.mesh,'Medium → fine on each profile');drawSensitivity($('local-effect-chart'),series.local,'Baseline → targeted on each mesh');
 const cell=(row,text)=>{const td=document.createElement('td');td.textContent=String(text);row.append(td);return td;};
 for(const s of data.studies){const tr=document.createElement('tr');for(const v of [s.mesh_name+' / '+(s.local_profile==='baseline'?'baseline':'targeted'),s.cells,Object.values(s.solver_checks).every(Boolean)&&s.bore_verification.all_pass?'Pass':'Attention'])cell(tr,v);const b=document.createElement('button');b.textContent='Open';b.onclick=()=>openRun(s.run_id);cell(tr,'').append(b);$('local-cases').append(tr);}
 for(const [key,v] of Object.entries(data.checks)){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=key.replaceAll('_',' ');dd.textContent=v?'Pass':'Attention';$('local-checks').append(dt,dd);}
 for(const p of data.studies[0].probes){const o=document.createElement('option');o.value=p.name;o.textContent=p.name;$('local-probe').append(o);}
 const show=()=>{$('local-probes').replaceChildren();for(const p of localProbeRows(data,$('local-probe').value)){const tr=document.createElement('tr');for(const v of [p.label,p.speed.toExponential(4),p.pressure.toExponential(4),p.radius.toFixed(3)])cell(tr,v);$('local-probes').append(tr);}};$('local-probe').onchange=show;show();
}
