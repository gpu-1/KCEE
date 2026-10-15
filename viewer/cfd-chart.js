const NS='http://www.w3.org/2000/svg';
export function profileSeries(mesh){
 if(!Array.isArray(mesh.profile)||mesh.profile.length!==mesh.cells||mesh.profile.some((r,i,a)=>![r.y_m,r.velocity_m_s,r.analytical_velocity_m_s].every(Number.isFinite)||(i>0&&r.y_m<=a[i-1].y_m)))throw new Error('Invalid CFD profile');
 return {gap:mesh.profile.map(r=>r.y_m*1000),velocity:mesh.profile.map(r=>r.velocity_m_s),exact:mesh.profile.map(r=>r.analytical_velocity_m_s)};
}
export function drawCFDChart(container,mesh){
 const s=profileSeries(mesh);container.replaceChildren();const make=(tag,attrs={},text)=>{const node=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))node.setAttribute(k,String(v));if(text!==undefined)node.textContent=text;return node;};
 const svg=make('svg',{viewBox:'0 0 360 250',role:'img','aria-label':'Channel velocity versus gap position: numerical solid line and analytical dashed line'});svg.append(make('title',{},'Plane Poiseuille velocity profile'));
 const max=Math.max(...s.velocity,...s.exact)*1.1,x=v=>55+(v-s.gap[0])/(s.gap.at(-1)-s.gap[0])*285,y=v=>185-v/max*140;
 svg.append(make('text',{x:55,y:20,fill:'#dfe9f1','font-size':12},'Velocity (m/s)'));
 for(let i=0;i<=4;i++){const v=max*i/4;svg.append(make('line',{x1:55,y1:y(v),x2:340,y2:y(v),stroke:'#314653'}),make('text',{x:50,y:y(v)+3,'text-anchor':'end',fill:'#a5b9c7','font-size':9},v.toFixed(5)));const pos=s.gap[0]+(s.gap.at(-1)-s.gap[0])*i/4;svg.append(make('text',{x:x(pos),y:202,'text-anchor':'middle',fill:'#a5b9c7','font-size':10},pos.toFixed(2)));}
 for(const [values,color,dash] of [[s.velocity,'#79dcc8',''],[s.exact,'#f4bd75','5 4']])svg.append(make('polyline',{points:values.map((v,i)=>x(s.gap[i])+','+y(v)).join(' '),fill:'none',stroke:color,'stroke-width':2,'stroke-dasharray':dash}));
 svg.append(make('text',{x:190,y:220,'text-anchor':'middle',fill:'#a5b9c7','font-size':10},'Across gap (mm), cell centres'),make('text',{x:55,y:240,fill:'#79dcc8','font-size':10},'Solid: numerical'),make('text',{x:190,y:240,fill:'#f4bd75','font-size':10},'Dashed: analytical'));container.append(svg);
}
