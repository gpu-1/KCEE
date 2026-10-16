const NS='http://www.w3.org/2000/svg';
export function convergenceSeries(flow){
 const spatial=flow.mesh_study.map(m=>({x:m.cell_size_m,velocity:m.relative_velocity_l2_error,pressure:m.relative_pressure_l2_error,label:m.cells_per_axis+'²'}));
 const temporal=(flow.time_refinement?.successive_differences||[]).map(d=>({x:d.coarse_time_step_s,velocity:d.relative_velocity_difference,pressure:d.relative_pressure_difference,label:d.coarse_time_step_s+' → '+d.fine_time_step_s+' s'}));
 for(const rows of [spatial,temporal])if(rows.some(r=>![r.x,r.velocity,r.pressure].every(v=>Number.isFinite(v)&&v>0)))throw Error('Convergence plot requires positive finite values');
 return {spatial,temporal};
}
export function drawConvergence(container,rows,title,xLabel,yLabel){
 container.replaceChildren();if(rows.length<2){container.textContent='Not recorded in this historical run. Run a new OpenFOAM verification study to include time refinement.';return;}
 const make=(tag,attrs={},text)=>{const el=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));if(text!==undefined)el.textContent=text;return el;};
 const xs=rows.map(r=>Math.log10(r.x)),ys=rows.flatMap(r=>[Math.log10(r.velocity),Math.log10(r.pressure)]);const xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.floor(Math.min(...ys)),ymax=Math.ceil(Math.max(...ys));const x=v=>60+270*(Math.log10(v)-xmin)/(xmax-xmin||1),y=v=>190-140*(Math.log10(v)-ymin)/(ymax-ymin||1);
 const svg=make('svg',{viewBox:'0 0 360 275',role:'img','aria-label':title+'; logarithmic axes'});svg.append(make('title',{},title),make('text',{x:12,y:18,fill:'#dfe9f1','font-size':12},title));
 for(let exponent=ymin;exponent<=ymax;exponent++){const value=10**exponent;svg.append(make('line',{x1:60,y1:y(value),x2:330,y2:y(value),stroke:'#314653'}),make('text',{x:54,y:y(value)+3,fill:'#a5b9c7','font-size':9,'text-anchor':'end'},value.toExponential(0)));}
 for(const row of rows)svg.append(make('text',{x:x(row.x),y:207,fill:'#a5b9c7','font-size':9,'text-anchor':'middle'},Number(row.x.toPrecision(3))));
 for(const [key,color] of [['velocity','#79dcc8'],['pressure','#f4bd75']]){svg.append(make('polyline',{points:rows.map(r=>x(r.x)+','+y(r[key])).join(' '),fill:'none',stroke:color,'stroke-width':2}));for(const row of rows){const dot=make('circle',{cx:x(row.x),cy:y(row[key]),r:3,fill:color});dot.append(make('title',{},row.label+': '+key+' '+row[key]));svg.append(dot);}}
 svg.append(make('text',{x:180,y:225,fill:'#a5b9c7','font-size':10,'text-anchor':'middle'},xLabel+' · log scale'),make('text',{x:12,y:243,fill:'#a5b9c7','font-size':10},yLabel),make('text',{x:12,y:264,fill:'#79dcc8','font-size':10},'Velocity'),make('text',{x:180,y:264,fill:'#f4bd75','font-size':10},'Pressure'));container.append(svg);
}
