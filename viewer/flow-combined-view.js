export function combinedSeries(data){
 if(!['kcee.bracket-flow-combined.v1','kcee.bracket-flow-combined.v2'].includes(data?.schema))throw Error('Invalid combined evidence');
 const convert=(pairs,key)=>pairs.map(p=>{const velocity=p.maximum_velocity_change_normalized_by_inlet*100,pressure=p.maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale*100;if(![velocity,pressure].every(v=>Number.isFinite(v)&&v>=0))throw Error('Invalid sensitivity value');return {label:p['from_'+key]+' → '+p['to_'+key],velocity,pressure};});
 return {mesh:convert(data.mesh_study.successive_changes,'mesh'),domain:convert(data.domain_comparison.data.successive_changes,'domain')};
}
export function drawSensitivity(container,rows,title){
 container.replaceChildren();const ns='http://www.w3.org/2000/svg';
 const el=(tag,attrs={},text)=>{const node=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))node.setAttribute(k,String(v));if(text!==undefined)node.textContent=text;return node;};
 const maximum=Math.max(...rows.flatMap(r=>[r.velocity,r.pressure]),0);const upper=maximum>0?maximum*1.15:1;const x=i=>75+i*220/Math.max(1,rows.length-1),y=v=>185-140*v/upper;
 const svg=el('svg',{viewBox:'0 0 360 275',role:'img','aria-label':title+'; successive normalized differences on a linear percent axis'});svg.append(el('title',{},title),el('text',{x:12,y:18,fill:'#dfe9f1','font-size':12},title));
 for(let i=0;i<=4;i++){const value=upper*i/4;svg.append(el('line',{x1:60,x2:330,y1:y(value),y2:y(value),stroke:'#314653'}),el('text',{x:55,y:y(value)+3,'text-anchor':'end',fill:'#a5b9c7','font-size':10},value.toFixed(2)+'%'));}
 rows.forEach((r,i)=>svg.append(el('text',{x:x(i),y:207,'text-anchor':'middle',fill:'#a5b9c7','font-size':10},r.label)));
 for(const [key,color] of [['velocity','#79dcc8'],['pressure','#f4bd75']]){svg.append(el('polyline',{points:rows.map((r,i)=>x(i)+','+y(r[key])).join(' '),stroke:color,fill:'none','stroke-width':2}));rows.forEach((r,i)=>{const dot=el('circle',{cx:x(i),cy:y(r[key]),r:4,fill:color});dot.append(el('title',{},r.label+' '+key+': '+r[key].toFixed(5)+'%'));svg.append(dot);});}
 svg.append(el('text',{x:12,y:235,fill:'#a5b9c7','font-size':10},'Successive changes, not analytical errors'),el('text',{x:12,y:259,fill:'#79dcc8','font-size':10},'Velocity / inlet'),el('text',{x:172,y:259,fill:'#f4bd75','font-size':10},'Referenced pressure / ½U²'));container.append(svg);
}
export function mountCombined(data,openRun){
 const series=combinedSeries(data),$=id=>document.getElementById(id);
 drawSensitivity($('combined-mesh-chart'),series.mesh,'Far-domain mesh sensitivity');drawSensitivity($('combined-domain-chart'),series.domain,'Medium-mesh domain sensitivity');
 const cell=(tr,text)=>{const td=document.createElement('td');td.textContent=String(text);tr.append(td);return td;};
 for(const s of data.mesh_study.studies){const tr=document.createElement('tr');for(const value of [s.mesh_name,s.cells,(s.nominal_near_surface_cell_m*1000).toFixed(4),Object.values(s.solver_checks).every(Boolean)&&s.bore_verification.all_pass?'Pass':'Attention'])cell(tr,value);const b=document.createElement('button');b.textContent='Open';b.onclick=()=>openRun(s.run_id);cell(tr,'').append(b);$('combined-meshes').append(tr);}
 $('combined-open-domain').onclick=()=>openRun(data.domain_comparison.run_id);
 for(const [key,value] of Object.entries(data.checks)){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=key.replaceAll('_',' ');dd.textContent=value?'Pass':'Attention';$('combined-checks').append(dt,dd);}
 for(const p of data.mesh_study.studies[0].probes){const option=document.createElement('option');option.value=p.name;option.textContent=p.name;$('combined-probe').append(option);}
 const show=()=>{$('combined-probes').replaceChildren();for(const s of data.mesh_study.studies){const p=s.probes.find(p=>p.name===$('combined-probe').value);const tr=document.createElement('tr');for(const value of [s.mesh_name,p.speed_m_s.toExponential(4),p.pressure_minus_upstream_m2_s2.toExponential(4),(p.maximum_support_distance_m*1000).toFixed(3)])cell(tr,value);$('combined-probes').append(tr);}};$('combined-probe').onchange=show;show();
}
