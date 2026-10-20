import {mountRegionalVerification} from './regional-verification-view.js';
let generation=0,urls=[];
export function regionalRows(data,comparison,component='pressure',moment=false,axis=0){
 if(data?.schema!=='native-regional-loads-v1'||!['pressure','viscous','total'].includes(component)||![0,1,2].includes(axis))throw Error('Invalid regional diagnostics');
 const c=data.comparisons[comparison],key=component+(moment?'_moment_N_m':'_force_N');
 if(!c)throw Error('Missing regional comparison');
 return c.regions.map(r=>{const v=r.signed_changes[key];if(!Array.isArray(v)||v.length!==3||!v.every(Number.isFinite))throw Error('Invalid regional change');return {name:r.region,value:v[axis]};});
}
export function mountRegionalForces(load,verify){
 mountRegionalVerification(verify);
 const token=++generation,$=id=>document.getElementById(id);for(const u of urls)URL.revokeObjectURL(u);urls=[];
 $('regional-result').hidden=true;$('regional-status').textContent='';$('regional-load').disabled=false;
 $('regional-load').onclick=async()=>{
  $('regional-load').disabled=true;$('regional-status').textContent='Checking source evidence and regional closure…';
  try{
   const data=await load();if(token!==generation)return;
   if(data.schema!=='native-regional-loads-v1'||!Object.values(data.checks).every(v=>v===true))throw Error('Regional evidence checks failed');
   $('regional-comparison').replaceChildren();data.comparisons.forEach((c,i)=>{const o=document.createElement('option');o.value=i;o.textContent=c.label;$('regional-comparison').append(o);});
   const csv=[['report_run_id','report_manifest_sha256','source_run_id','source_manifest_sha256','mesh','profile','domain','region','faces','area_m2','axis','pressure_force_N','viscous_force_N','total_force_N','pressure_moment_N_m','viscous_moment_N_m','total_moment_N_m','pressure_offset_1Pa_force_N','pressure_offset_1Pa_moment_N_m']];
   for(const c of data.cases)for(const r of c.regions)for(const [i,a] of ['x','y','z'].entries())csv.push([data.report_run_id,data.report_manifest_sha256,c.run_id,c.manifest_sha256,c.mesh,c.profile,c.domain,r.region,r.faces,r.area_m2,a,...['pressure_force_N','viscous_force_N','total_force_N','pressure_moment_N_m','viscous_moment_N_m','total_moment_N_m'].map(k=>r.loads[k][i]),r.pressure_offset_1Pa_force_N[i],r.pressure_offset_1Pa_moment_N_m[i]]);
   for(const [id,body,type] of [['regional-json',JSON.stringify(data,null,2),'application/json'],['regional-csv',csv.map(row=>row.map(v=>'"'+String(v).replaceAll('"','""')+'"').join(',')).join('\r\n'),'text/csv']]){const u=URL.createObjectURL(new Blob([body],{type}));urls.push(u);$(id).href=u;}
   $('regional-limits').textContent=data.limits.join(' ');$('regional-provenance').textContent='Source report '+data.report_run_id+' · manifest '+data.report_manifest_sha256+' · method '+data.schema+' · implementation '+data.implementation_sha256;
   const show=()=>{
    const moment=$('regional-quantity').value==='moment',component=$('regional-component').value,axis=Number($('regional-axis').value),comparison=Number($('regional-comparison').value),rows=data.comparisons.length?regionalRows(data,comparison,component,moment,axis):[],unit=moment?'N·m':'N';
    $('regional-rows').replaceChildren();
    for(const r of rows){const tr=document.createElement('tr');for(const text of [r.name,r.value.toExponential(5)+' '+unit]){const td=document.createElement('td');td.textContent=text;tr.append(td);}$('regional-rows').append(tr);}
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 360 340');svg.setAttribute('role','img');svg.setAttribute('aria-label','Signed regional '+component+' '+(moment?'moment':'force')+' changes');
    const max=Math.max(...rows.map(r=>Math.abs(r.value)),1e-30);for(const [i,r] of rows.entries()){const rect=document.createElementNS(ns,'rect'),w=Math.abs(r.value)/max*145;for(const [k,v] of Object.entries({x:r.value<0?180-w:180,y:20+i*43,width:w,height:14,fill:r.value<0?'#f4bd75':'#79dcc8'}))rect.setAttribute(k,String(v));const title=document.createElementNS(ns,'title');title.textContent=r.name+': '+r.value.toExponential(5)+' '+unit;rect.append(title);const t=document.createElementNS(ns,'text');for(const [k,v] of Object.entries({x:8,y:16+i*43,fill:'#dfe9f1','font-size':10}))t.setAttribute(k,String(v));t.textContent=r.name;svg.append(t,rect);}
    $('regional-chart').replaceChildren(svg);$('regional-result').hidden=false;
   };
   for(const id of ['regional-comparison','regional-component','regional-quantity','regional-axis'])$(id).onchange=show;
   $('regional-status').textContent='Verified '+data.cases.length+' cases. Every face is assigned once; all six force/moment sums reproduce native loads. Changes are sensitivities, not error bounds.';show();
  }catch(e){if(token===generation)$('regional-status').textContent=e.message;}finally{if(token===generation)$('regional-load').disabled=false;}
 };
}
