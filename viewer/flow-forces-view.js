const components=['x','y','z'];
export function forceRows(study,moment=false){
 const f=study?.loads;if(!f||f.method!=='wall-face-traction-v1')throw Error('Unsupported force estimate');
 const keys=moment?['pressure_moment_N_m','viscous_estimate_moment_N_m','total_estimate_moment_N_m']:['pressure_force_N','viscous_estimate_force_N','total_estimate_force_N'];
 if(!keys.every(k=>Array.isArray(f[k])&&f[k].length===3&&f[k].every(Number.isFinite)))throw Error('Invalid force vector');
 return components.map((axis,i)=>{const values=keys.map(k=>f[k][i]);if(Math.abs(values[0]+values[1]-values[2])>1e-12*Math.max(...values.map(Math.abs),1e-20))throw Error('Force components do not close');return {axis,values};});
}
export function mountForces(data,openRun,verify){
 if(data?.schema!=='kcee.bracket-flow-forces.v1'||![1,6].includes(data.studies?.length))throw Error('Invalid force study');
 const $=id=>document.getElementById(id),ns='http://www.w3.org/2000/svg';
 const cell=(tr,text)=>{const td=document.createElement('td');td.textContent=String(text);tr.append(td);return td;};
 $('forces-case').replaceChildren();$('forces-comparisons').replaceChildren();$('forces-benchmark').replaceChildren();$('forces-checks').replaceChildren();$('forces-verify-status').textContent='';
 for(const [i,s] of data.studies.entries()){forceRows(s);const o=document.createElement('option');o.value=i;o.textContent=s.mesh_name+' / '+s.local_profile+' / '+s.domain_name;$('forces-case').append(o);}
 const show=()=>{
  const s=data.studies[Number($('forces-case').value)],moment=$('forces-quantity').value==='moment',rows=forceRows(s,moment),unit=moment?'N·m':'N';$('forces-components').replaceChildren();$('forces-chart').replaceChildren();
  for(const r of rows){const tr=document.createElement('tr');for(const v of [r.axis,...r.values.map(v=>v.toExponential(6))])cell(tr,v);$('forces-components').append(tr);}
  $('forces-unit').textContent=unit;$('forces-case-info').textContent=s.cells+' fluid cells · '+s.loads.wall_faces+' wall faces · minimum normal distance '+(s.loads.minimum_normal_distance_m*1000).toExponential(3)+' mm · maximum wall nonorthogonality '+s.loads.maximum_wall_nonorthogonality_degrees.toFixed(2)+'°. Moments about (0,0,0) m. Coefficient reference: 0.0012 m² envelope area; ½ρU²A = '+s.loads.force_normalization_N.toExponential(3)+' N.';
  $('forces-open-source').onclick=()=>openRun(s.run_id);
  const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 360 290');svg.setAttribute('role','img');svg.setAttribute('aria-label','Signed '+(moment?'moments':'forces')+' in '+unit+'; pressure, viscous estimate and total estimate');
  const node=(tag,attrs,text)=>{const el=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));if(text!==undefined)el.textContent=text;return el;};
  const max=Math.max(...rows.flatMap(r=>r.values.map(Math.abs)),1e-30),colors=['#f4bd75','#79dcc8','#bda6ff'];svg.append(node('line',{x1:180,x2:180,y1:20,y2:240,stroke:'#a5b9c7'}));
  rows.forEach((r,i)=>{svg.append(node('text',{x:8,y:35+i*70,fill:'#dfe9f1','font-size':12},r.axis));r.values.forEach((v,j)=>{const width=Math.abs(v)/max*140,rect=node('rect',{x:v<0?180-width:180,y:24+i*70+j*17,width,height:12,fill:colors[j]});rect.append(node('title',{},r.axis+': '+v.toExponential(6)+' '+unit));svg.append(rect);});});
  svg.append(node('text',{x:30,y:250,fill:'#a5b9c7','font-size':10},'−'+max.toExponential(2)+' '+unit),node('text',{x:180,y:250,fill:'#a5b9c7','font-size':10},'0'),node('text',{x:250,y:250,fill:'#a5b9c7','font-size':10},'+'+max.toExponential(2)+' '+unit));
  ['Pressure','Viscous estimate','Total estimate'].forEach((text,i)=>svg.append(node('text',{x:8+i*118,y:279,fill:colors[i],'font-size':10},text)));$('forces-chart').append(svg);
 };
 $('forces-case').onchange=show;$('forces-quantity').onchange=show;$('forces-quantity').value='force';show();
 for(const c of data.comparisons){const tr=document.createElement('tr');cell(tr,c.label);for(const k of ['pressure_force_N','viscous_estimate_force_N','total_estimate_force_N'])cell(tr,c.signed_changes[k].map(v=>v.toExponential(4)).join(', '));$('forces-comparisons').append(tr);}
 $('forces-comparison-note').textContent=data.comparisons.length?'Signed changes (second case minus first), x/y/z in N. Fine far → outer includes small spacing/alignment changes. Differences do not establish convergence.':'Single saved case. Select a native design or a mesh/domain report to build the six-case comparison.';
 for(const r of data.benchmark.wall_shear_study){const tr=document.createElement('tr');for(const v of [r.cells,r.force_N.toExponential(6),r.exact_force_N.toExponential(6),(r.relative_error*100).toFixed(5)+'%'])cell(tr,v);$('forces-benchmark').append(tr);}
 for(const [key,value] of Object.entries({...data.benchmark.checks,...data.checks})){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=key.replaceAll('_',' ');dd.textContent=value?'Pass':'Needs attention';$('forces-checks').append(dt,dd);}
 $('forces-verify').onclick=async()=>{$('forces-verify').disabled=true;$('forces-verify-status').textContent='Reproducing source fields and wall loads…';try{const r=await verify();if(r.force_evidence!=='reproduced')throw Error('Evidence replay incomplete');$('forces-verify-status').textContent='Reproduced from '+r.source_cases+' verified source case(s). Engineering acceptance remains pending.';}catch(e){$('forces-verify-status').textContent=e.message;}finally{$('forces-verify').disabled=false;}};
}
