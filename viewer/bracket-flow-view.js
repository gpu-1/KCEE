export function flowPoints(flow,quantity='speed',scope='slice'){
 if(!['speed','pressure'].includes(quantity)||!['near','all','slice'].includes(scope)||!Array.isArray(flow.field)||flow.field.length!==flow.cells)throw Error('Invalid flow field scope');
 for(const row of flow.field)if(!['x_m','y_m','z_m','u_m_s','v_m_s','w_m_s','p_kinematic_m2_s2'].every(k=>Number.isFinite(row[k])))throw Error('Invalid flow field');
 const rows=flow.field.filter(r=>scope==='all'||r.x_m>=-.03&&r.x_m<=.12&&r.y_m>=-.04&&r.y_m<=.07&&r.z_m>=-.04&&r.z_m<=.10&&(scope!=='slice'||Math.abs(r.y_m-.015)<=.002));
 if(!rows.length)throw Error('No flow points in view');
 const values=rows.map(r=>quantity==='speed'?Math.hypot(r.u_m_s,r.v_m_s,r.w_m_s):r.p_kinematic_m2_s2),min=values.reduce((a,b)=>Math.min(a,b),Infinity),max=values.reduce((a,b)=>Math.max(a,b),-Infinity);
 return {positions:rows.flatMap(r=>[r.x_m*1000,r.y_m*1000,r.z_m*1000]),colors:values.flatMap(v=>{const t=max===min?.5:(v-min)/(max-min);return [t,.6*(1-Math.abs(2*t-1)),1-t];}),min,max,count:rows.length,units:quantity==='speed'?'m/s':'m²/s²'};
}
