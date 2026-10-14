const NS='http://www.w3.org/2000/svg';
function element(name,attributes={},text){const node=document.createElementNS(NS,name);for(const [key,value] of Object.entries(attributes))node.setAttribute(key,String(value));if(text!==undefined)node.textContent=text;return node;}
export function drawThermalChart(container,mesh){
  const rows=mesh.profile;if(!Array.isArray(rows)||rows.length<2||rows.some(row=>![row.x_m,row.temperature_C,row.analytical_temperature_C].every(Number.isFinite)))throw new Error('Invalid thermal chart profile');
  const x=rows.map(row=>row.x_m*1000),t=rows.map(row=>row.temperature_C),reference=rows.map(row=>row.analytical_temperature_C),error=rows.map(row=>Math.abs(row.temperature_C-row.analytical_temperature_C));
  if(x.some((value,index)=>index>0&&value<=x[index-1]))throw new Error('Thermal profile positions must increase');
  container.replaceChildren();
  function chart(title,series,labels,maximum,minimum){
    const svg=element('svg',{viewBox:'0 0 360 225',role:'img','aria-label':title});svg.appendChild(element('title',{},title));
    const X=value=>48+(value-x[0])/(x.at(-1)-x[0])*296,Y=value=>170-(value-minimum)/(maximum-minimum)*130;
    svg.appendChild(element('text',{x:48,y:18,fill:'#dfe9f1','font-size':12},title));
    for(let index=0;index<=4;index++){const value=minimum+(maximum-minimum)*index/4,y=Y(value);svg.appendChild(element('line',{x1:48,y1:y,x2:344,y2:y,stroke:'#314653'}));svg.appendChild(element('text',{x:43,y:y+4,'text-anchor':'end',fill:'#a5b9c7','font-size':10},value.toFixed(maximum<1?4:1)));const position=x[0]+(x.at(-1)-x[0])*index/4;svg.appendChild(element('text',{x:X(position),y:188,'text-anchor':'middle',fill:'#a5b9c7','font-size':10},position.toFixed(0)));}
    svg.appendChild(element('text',{x:196,y:204,'text-anchor':'middle',fill:'#a5b9c7','font-size':10},'Position along bar (mm)'));
    const colors=['#79dcc8','#f4bd75'];series.forEach((values,index)=>{svg.appendChild(element('polyline',{points:values.map((value,i)=>X(x[i])+','+Y(value)).join(' '),fill:'none',stroke:colors[index],'stroke-width':2,...(index===1?{'stroke-dasharray':'5 4'}:{})}));svg.appendChild(element('text',{x:48+index*155,y:222,fill:colors[index],'font-size':10},labels[index]));});container.appendChild(svg);
  }
  const low=Math.min(...t,...reference),high=Math.max(...t,...reference);chart('Temperature (°C)',[t,reference],['Numerical · '+mesh.cells+' cells','Analytical at nodes'],high+2,low-2);
  chart('Absolute temperature error (°C)',[error],['Numerical vs analytical'],Math.max(...error)*1.1||.001,0);
}
