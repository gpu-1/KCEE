const NS='http://www.w3.org/2000/svg';
export function vortexGrid(mesh,quantity='speed'){
 const n=mesh.cells_per_axis,rows=mesh.field;
 if(!Number.isInteger(n)||n<2||n>128||!Array.isArray(rows)||rows.length!==n*n||!['speed','pressure','velocity_error','pressure_error'].includes(quantity))throw Error('Invalid vortex field');
 const values=rows.map((r,i)=>{if(!['x_m','y_m','u_m_s','v_m_s','p_kinematic_m2_s2','exact_u_m_s','exact_v_m_s','exact_p_kinematic_m2_s2'].every(k=>Number.isFinite(r[k])))throw Error('Invalid vortex value');if(i&&i%n&&r.x_m<=rows[i-1].x_m)throw Error('Unordered vortex field');return quantity==='pressure'?r.p_kinematic_m2_s2:quantity==='velocity_error'?Math.hypot(r.u_m_s-r.exact_u_m_s,r.v_m_s-r.exact_v_m_s):quantity==='pressure_error'?r.p_kinematic_m2_s2-r.exact_p_kinematic_m2_s2:Math.hypot(r.u_m_s,r.v_m_s);});
 return {n,rows,values,min:Math.min(...values),max:Math.max(...values),units:quantity==='pressure'||quantity==='pressure_error'?'m²/s²':'m/s'};
}
export function drawVortex(container,mesh,quantity,showMesh=false){
 const grid=vortexGrid(mesh,quantity),{n,values,min,max}=grid;container.replaceChildren();
 const make=(tag,attrs={},text)=>{const el=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));if(text!==undefined)el.textContent=text;return el;};
 const svg=make('svg',{viewBox:'0 0 360 410',role:'img','aria-label':quantity+' field on '+n+' by '+n+' OpenFOAM cells at 0.5 seconds'}),size=300/n;
 svg.append(make('title',{},'Computed OpenFOAM vortex field, x and y in metres'));
 values.forEach((value,i)=>{const f=max===min?.5:(value-min)/(max-min);const rect=make('rect',{x:45+(i%n)*size,y:20+(n-1-Math.floor(i/n))*size,width:size,height:size,'shape-rendering':'crispEdges',fill:`hsl(${240-240*f} 75% 55%)`,stroke:showMesh?'#17212b':'none','stroke-width':showMesh?.25:0});rect.append(make('title',{},`x=${grid.rows[i].x_m} m, y=${grid.rows[i].y_m} m; value=${value} ${grid.units}`));svg.append(rect);});
 if(quantity==='speed'||quantity==='pressure')for(let j=2;j<n;j+=Math.max(2,Math.floor(n/8)))for(let i=2;i<n;i+=Math.max(2,Math.floor(n/8))){const r=grid.rows[j*n+i],x=45+(i+.5)*size,y=20+(n-j-.5)*size;const scale=10;svg.append(make('line',{x1:x,y1:y,x2:x+r.u_m_s*scale,y2:y-r.v_m_s*scale,stroke:'#fff','stroke-width':1.1}));svg.append(make('circle',{cx:x+r.u_m_s*scale,cy:y-r.v_m_s*scale,r:1,fill:'#fff'}));}
 svg.append(make('text',{x:45,y:337,fill:'#a5b9c7','font-size':11},'0'),make('text',{x:300,y:337,fill:'#a5b9c7','font-size':11},'2π m'),make('text',{x:175,y:355,fill:'#a5b9c7','font-size':11},'x (m) →'),make('text',{x:3,y:18,fill:'#a5b9c7','font-size':11},'y (m) ↑'),make('text',{x:45,y:380,fill:'#8bb9ff','font-size':11},'Blue: '+min.toExponential(4)),make('text',{x:205,y:380,fill:'#ff9b8b','font-size':11},'Red: '+max.toExponential(4)),make('text',{x:45,y:400,fill:'#a5b9c7','font-size':11},grid.units+' · independent scale for each view'));
 container.append(svg);
}
