export function historyPoints(study,component='total',moment=false,tail=true){
 if(!['pressure','viscous','total'].includes(component))throw Error('Unsupported history component');
 const key=component+(moment?'_moment_N_m':'_force_N'),rows=study?.force_history?.series;
 if(!Array.isArray(rows)||rows.length<400||rows.some((r,i)=>r.iteration!==i+1||!Array.isArray(r[key])||r[key].length!==3||!r[key].every(Number.isFinite)))throw Error('Invalid force history');
 const selected=tail?rows.slice(-400):rows;return selected.filter((r,i)=>i%Math.max(1,Math.floor(selected.length/400))===0||i===selected.length-1).map(r=>({iteration:r.iteration,values:r[key]}));
}
export function renderForceHistory(data,study,moment=false){
 const $=id=>document.getElementById(id);$('native-history').hidden=!data.force_convergence;
 if(!data.force_convergence)return;
 const component=$('native-history-component').value,tail=$('native-history-range').value==='tail',points=historyPoints(study,component,moment,tail),unit=moment?'N·m':'N',ns='http://www.w3.org/2000/svg';
 const node=(tag,attrs={},text)=>{const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;return n;};
 const chart=(series,labels,title,xlabels)=>{
  const values=series.flatMap(s=>s.values),lo=Math.min(0,...values),hi=Math.max(0,...values),span=Math.max(hi-lo,1e-30),y=v=>200-(v-lo)/span*155,svg=node('svg',{viewBox:'0 0 360 275',role:'img','aria-label':title});
  svg.append(node('text',{x:10,y:18,fill:'#dfe9f1','font-size':11},title),node('text',{x:8,y:36,fill:'#a5b9c7','font-size':10},hi.toExponential(3)+' '+unit),node('text',{x:8,y:218,fill:'#a5b9c7','font-size':10},lo.toExponential(3)+' '+unit));
  const colors=['#79dcc8','#f4bd75','#bda6ff'];series.forEach((s,j)=>{const coords=s.values.map((v,i)=>[55+i*265/Math.max(1,s.values.length-1),y(v)]);svg.append(node('polyline',{points:coords.map(p=>p.join(',')).join(' '),fill:'none',stroke:colors[j],'stroke-width':1.8}));svg.append(node('text',{x:10+j*116,y:267,fill:colors[j],'font-size':11},labels[j]));});
  xlabels.forEach((label,i)=>svg.append(node('text',{x:50+i*250/Math.max(1,xlabels.length-1),y:240,fill:'#a5b9c7','font-size':10},label)));return svg;
 };
 $('native-history-chart').replaceChildren(chart(['x','y','z'].map((axis,i)=>({values:points.map(p=>p.values[i])})),['x','y','z'],component+' '+(moment?'moment':'force')+' history',[String(points[0].iteration),String(points.at(-1).iteration)]));
 const h=study.force_history,key=component+(moment?'_moment_N_m':'_force_N'),stat=h.statistics[key];$('native-history-status').textContent=study.mesh_name+' · '+h.iterations+' recorded iterations · all force/moment settling checks: '+(h.iterative_settling==='criteria_met'?'criteria met':'not established')+'. Window checks are not an error bound.';
 $('native-history-window').textContent='Last '+h.window_iterations+' vs previous '+h.window_iterations+' iterations: mean-vector change '+(stat.relative_window_mean_change*100).toExponential(3)+'% (limit 0.1%); max deviation from final window mean '+(stat.relative_max_deviation_from_last_mean*100).toExponential(3)+'% (limit 0.2%). Selected check: '+(h.checks[key]?'criteria met':'not established')+'. Normalization uses the larger of the last mean-vector magnitude and the declared dynamic force/moment scale.';
 const keys=['pressure','viscous','total'].map(c=>c+(moment?'_moment_N_m':'_force_N'));$('native-refinement-chart').replaceChildren(chart(keys.map(k=>({values:data.studies.map(s=>s.loads[k][0])})),['Pressure','Viscous','Total'],'Native x-'+(moment?'moment':'force')+' · three meshes',data.studies.map(s=>s.mesh_name)));
 const summaries=data.force_convergence.adjacent_mesh_changes.map((c,i)=>data.studies[i].mesh_name+' → '+data.studies[i+1].mesh_name+': '+keys.map((k,j)=>['pressure','viscous','total'][j]+' '+(c.changes[k].relative_change_to_finer_norm===null?'undefined near zero':(100*c.changes[k].relative_change_to_finer_norm).toFixed(3)+'%')).join('; '));$('native-refinement-summary').textContent=summaries.join('. ')+'. Changes are vector norms relative to the finer result. Component cancellation, partial layer coverage and nonuniform refinement prevent an automatic convergence or error-bound claim.';
}
