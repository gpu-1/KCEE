export function nativeRows(study,moment=false){
 const f=study?.loads;if(f?.method!=='openfoam-full-stress-v1')throw Error('Unsupported native force evidence');
 const keys=moment?['pressure_moment_N_m','viscous_moment_N_m','total_moment_N_m']:['pressure_force_N','viscous_force_N','total_force_N'];
 if(!keys.every(k=>Array.isArray(f[k])&&f[k].length===3&&f[k].every(Number.isFinite)))throw Error('Invalid native load vector');
 return ['x','y','z'].map((axis,i)=>{const values=keys.map(k=>f[k][i]);if(Math.abs(values[0]+values[1]-values[2])>1e-10*Math.max(...values.map(Math.abs),1e-20))throw Error('Native load components do not close');return {axis,values};});
}
export function mountNativeForces(data,openRun,verify){
 if(data?.schema!=='kcee.bracket-native-forces.v1'||![1,4,6].includes(data.studies?.length))throw Error('Invalid native force study');
 const $=id=>document.getElementById(id),ns='http://www.w3.org/2000/svg',cell=(tr,text)=>{const td=document.createElement('td');td.textContent=String(text);tr.append(td);return td;};
 for(const id of ['native-case','native-comparisons','native-benchmark','native-checks'])$(id).replaceChildren();$('native-verify-status').textContent='';
 $('native-layer-sensitivity').hidden=!data.layer_sensitivity;$('native-layer-chart').replaceChildren();$('native-layer-summary').textContent='';
 if(data.layer_sensitivity){
  const node=(tag,attrs={},text)=>{const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;return n;};
  const values=data.studies.map(s=>s.loads.total_force_N[0]),lo=Math.min(...values),hi=Math.max(...values),span=Math.max(hi-lo,Math.abs(hi)*.01,1e-30),y=v=>190-(v-lo)/span*140;
  const svg=node('svg',{viewBox:'0 0 360 270',role:'img','aria-label':'Medium to fine native total x-force, with and without layers'});
  svg.append(node('text',{x:12,y:18,fill:'#dfe9f1','font-size':12},'Total x-force (N)'),node('line',{x1:65,x2:310,y1:210,y2:210,stroke:'#a5b9c7'}));
  for(const [offset,color,label] of [[0,'#f4bd75','Without layers'],[2,'#79dcc8','With layers']]){
   svg.append(node('polyline',{points:`90,${y(values[offset])} 285,${y(values[offset+1])}`,fill:'none',stroke:color,'stroke-width':2}));
   for(let j=0;j<2;j++){const v=values[offset+j];svg.append(node('circle',{cx:90+j*195,cy:y(v),r:4,fill:color}),node('text',{x:48+j*195,y:y(v)-9,fill:color,'font-size':11},v.toExponential(4)));}
   svg.append(node('text',{x:12+offset*88,y:255,fill:color,'font-size':12},label));
  }
  svg.append(node('text',{x:65,y:229,fill:'#dfe9f1','font-size':12},'Medium'),node('text',{x:270,y:229,fill:'#dfe9f1','font-size':12},'Fine'));$('native-layer-chart').append(svg);
  const m=data.layer_sensitivity.medium_to_fine,format=v=>v===null?'undefined near zero':(100*v).toFixed(2)+'%';$('native-layer-summary').textContent='Total force-vector change relative to fine-vector magnitude: '+format(m.without_layers.total_force_N.relative_change_to_fine_norm)+' without layers; '+format(m.with_layers.total_force_N.relative_change_to_fine_norm)+' with layers. Layered pressure change: '+format(m.with_layers.pressure_force_N.relative_change_to_fine_norm)+'; layered viscous change: '+format(m.with_layers.viscous_force_N.relative_change_to_fine_norm)+'. Opposing component changes can cancel in the total. These are changes, not errors; convergence is not established.';
 }
 for(const [i,s] of data.studies.entries()){nativeRows(s);const o=document.createElement('option');o.value=i;o.textContent=s.mesh_name+' / '+s.local_profile+' / '+s.domain_name;$('native-case').append(o);}
 const show=()=>{
  const s=data.studies[Number($('native-case').value)],moment=$('native-quantity').value==='moment',rows=nativeRows(s,moment),unit=moment?'N·m':'N';$('native-components').replaceChildren();$('native-estimates').replaceChildren();$('native-chart').replaceChildren();$('native-unit').textContent=unit;
  for(const r of rows){const tr=document.createElement('tr');for(const v of [r.axis,...r.values.map(v=>v.toExponential(6))])cell(tr,v);$('native-components').append(tr);}
  const native=moment?s.loads.viscous_moment_N_m:s.loads.viscous_force_N,prior=moment?s.prior_estimate.viscous_estimate_moment_N_m:s.prior_estimate.viscous_estimate_force_N;
  for(const [i,axis] of ['x','y','z'].entries()){if(!Number.isFinite(prior[i]))throw Error('Missing prior estimate');const tr=document.createElement('tr');for(const v of [axis,native[i].toExponential(6),prior[i].toExponential(6),(native[i]-prior[i]).toExponential(6)])cell(tr,v);$('native-estimates').append(tr);}
  $('native-case-info').textContent=(s.layer_audit?'Requested 3 layers; final extrusion covers '+(s.layer_audit.extruded_face_fraction*100).toFixed(1)+'% of candidate faces. ':'')+s.cells+' fluid cells · '+s.loads.wall_faces+' wall faces · native laminar Stokes stress. Integration replay errors: '+s.loads.independent_force_replay_error_N.toExponential(2)+' N and '+s.loads.independent_moment_replay_error_N_m.toExponential(2)+' N·m. Engineering acceptance pending.';
  $('native-open-source').onclick=()=>openRun(s.run_id);
  const node=(tag,attrs={},text)=>{const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;return n;};
  const maximum=Math.max(...rows.flatMap(r=>r.values.map(Math.abs)),1e-30),colors=['#f4bd75','#79dcc8','#bda6ff'],svg=node('svg',{viewBox:'0 0 360 290',role:'img','aria-label':'Native pressure, full viscous and total '+(moment?'moments':'forces')+' in '+unit});svg.append(node('line',{x1:180,x2:180,y1:20,y2:240,stroke:'#a5b9c7'}));
  rows.forEach((r,i)=>{svg.append(node('text',{x:8,y:35+i*70,fill:'#dfe9f1','font-size':12},r.axis));r.values.forEach((v,j)=>{const w=Math.abs(v)/maximum*140,bar=node('rect',{x:v<0?180-w:180,y:24+i*70+j*17,width:w,height:12,fill:colors[j]});bar.append(node('title',{},r.axis+': '+v.toExponential(6)+' '+unit));svg.append(bar);});});
  svg.append(node('text',{x:25,y:250,fill:'#a5b9c7','font-size':10},'−'+maximum.toExponential(2)+' '+unit),node('text',{x:180,y:250,fill:'#a5b9c7','font-size':10},'0'),node('text',{x:250,y:250,fill:'#a5b9c7','font-size':10},'+'+maximum.toExponential(2)+' '+unit));['Pressure','Full viscous','Total'].forEach((t,i)=>svg.append(node('text',{x:8+i*118,y:279,fill:colors[i],'font-size':10},t)));$('native-chart').append(svg);
 };$('native-case').onchange=show;$('native-quantity').onchange=show;$('native-quantity').value='force';show();
 for(const c of data.comparisons){const tr=document.createElement('tr');cell(tr,c.label);for(const k of ['pressure_force_N','viscous_force_N','total_force_N'])cell(tr,c.signed_changes[k].map(v=>v.toExponential(4)).join(', '));$('native-comparisons').append(tr);}
 for(const r of data.benchmark.studies){const tr=document.createElement('tr');for(const v of [r.cells_x,(r.relative_errors.pressure_force_N*100).toExponential(3)+'%',(r.relative_errors.viscous_force_N*100).toExponential(3)+'%',(r.relative_errors.pressure_moment_N_m*100).toExponential(3)+'%',(r.relative_errors.viscous_moment_N_m*100).toExponential(3)+'%'])cell(tr,v);$('native-benchmark').append(tr);}
 for(const [key,value] of Object.entries({...data.benchmark.checks,...data.checks})){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=key.replaceAll('_',' ');dd.textContent=value?'Pass':'Needs attention';$('native-checks').append(dt,dd);}
 $('native-verify').onclick=async()=>{$('native-verify').disabled=true;$('native-verify-status').textContent='Replaying native wall stresses and source evidence…';try{const r=await verify();if(r.native_force_evidence!=='reproduced')throw Error('Native replay incomplete');$('native-verify-status').textContent='Native full-stress integration reproduced for '+r.source_cases+' source case(s). Engineering acceptance remains pending.';}catch(e){$('native-verify-status').textContent=e.message;}finally{$('native-verify').disabled=false;}};
}
