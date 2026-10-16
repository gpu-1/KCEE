import {drawSensitivity} from './flow-combined-view.js';
export function pressureSeries(data,method='production'){
 if(!['production','compact'].includes(method))throw Error('Invalid sampling method');
 if(data?.schema!=='kcee.bracket-flow-pressure.v1')throw Error('Invalid pressure evidence');
 const convert=rows=>rows.map(row=>{const velocity=row.maximum_velocity_change_normalized_by_inlet*100,pressure=row.maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale*100;if(![velocity,pressure].every(v=>Number.isFinite(v)&&v>=0))throw Error('Invalid pressure sensitivity');return {label:row.label,velocity,pressure};});
 return {mesh:convert(method==='compact'?data.compact_background_mesh_changes:data.background_mesh_changes),bore:convert(method==='compact'?data.compact_local_bore_changes:data.local_bore_changes)};
}
export function pressureProbeRows(data,name){
 return data.studies.map(s=>{const saved=s.probes.find(p=>p.name===name),compact=s.compact_probes.find(p=>p.name===name),coverage=s.native_audit.probe_support_coverage.find(p=>p.name===name);if(!saved||!compact||!coverage)throw Error('Missing pressure probe');return {label:s.mesh_name+' / '+s.bore_level,saved:saved.pressure_minus_upstream_m2_s2,compact:compact.pressure_minus_upstream_m2_s2,change:(compact.pressure_minus_upstream_m2_s2-saved.pressure_minus_upstream_m2_s2)/.00005*100,savedRadius:saved.maximum_support_distance_m*1000,compactRadius:compact.maximum_support_distance_m*1000,native:coverage.native_support_cells_exported+'/'+coverage.support_cells};});
}
export function mountPressure(data,openRun){
 const $=id=>document.getElementById(id);const show=()=>{const series=pressureSeries(data,$('pressure-sampling').value);drawSensitivity($('pressure-mesh-chart'),series.mesh,'Medium → fine at each bore level');drawSensitivity($('pressure-bore-chart'),series.bore,'Bore level 4 → 5 on each mesh');};$('pressure-sampling').onchange=show;show();
 for(const s of data.studies){const tr=document.createElement('tr');for(const value of [s.mesh_name+' / '+s.bore_level,s.cells,(s.nominal_bore_cell_m*1000).toFixed(4),(s.native_audit.coverage_fraction*100).toFixed(2)+'%']){const td=document.createElement('td');td.textContent=String(value);tr.append(td);}const td=document.createElement('td'),b=document.createElement('button');b.textContent='Open';b.onclick=()=>openRun(s.run_id);td.append(b);tr.append(td);$('pressure-cases').append(tr);}
 for(const p of data.studies[0].probes){const option=document.createElement('option');option.value=p.name;option.textContent=p.name;$('pressure-probe').append(option);}
 const showProbe=()=>{$('pressure-probes').replaceChildren();for(const r of pressureProbeRows(data,$('pressure-probe').value)){const tr=document.createElement('tr');for(const value of [r.label,r.saved.toExponential(4),r.compact.toExponential(4),r.change.toFixed(4)+'%',r.savedRadius.toFixed(3)+' / '+r.compactRadius.toFixed(3),r.native]){const td=document.createElement('td');td.textContent=value;tr.append(td);}$('pressure-probes').append(tr);}};$('pressure-probe').onchange=showProbe;showProbe();
 for(const [key,value] of Object.entries(data.checks)){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=key.replaceAll('_',' ');dd.textContent=value?'Pass':'Attention';$('pressure-checks').append(dt,dd);}
}
