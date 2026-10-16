export function probeRows(data, name) {
  if(!['kcee.bracket-flow-domain.v1','kcee.bracket-flow-domain.v2'].includes(data?.schema)||data.studies?.length!==3)throw new Error('Invalid domain comparison');
  return data.studies.map(study=>{
    const p=study.probes.find(p=>p.name===name);
    if(!p||![p.speed_m_s,p.pressure_minus_upstream_m2_s2,p.maximum_support_distance_m].every(Number.isFinite))throw new Error('Missing finite referenced probe values');
    return {domain:study.domain_name,speed:p.speed_m_s,pressureDifference:p.pressure_minus_upstream_m2_s2,supportRadiusMm:p.maximum_support_distance_m*1000};
  });
}
export function mountDomainView(data,openRun) {
  probeRows(data,data.studies[0].probes[0].name);
  const $=id=>document.getElementById(id);
  const cell=(row,text)=>{const td=document.createElement('td');td.textContent=String(text);row.append(td);return td;};
  const metric=(label,value)=>{const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;$('domain-checks').append(dt,dd);};
  for(const study of data.studies){
    const row=document.createElement('tr');
    for(const value of [study.domain_name,study.cells,(study.boundary_clearances_m.inlet*1000).toFixed(1)+' / '+(study.boundary_clearances_m.outlet*1000).toFixed(1),Object.values(study.solver_checks).every(Boolean)&&study.bore_verification.all_pass?'Pass':'Attention'])cell(row,value);
    const button=document.createElement('button');button.textContent='Open';button.onclick=()=>openRun(study.run_id);cell(row,'').append(button);$('domain-cases').append(row);
    metric(study.domain_name+' · bounds x / y / z (mm)',study.domain_min_m.map((x,k)=>(x*1000).toFixed(2)+' to '+(study.domain_max_m[k]*1000).toFixed(2)).join(' / '));
    metric(study.domain_name+' · background cells',study.background_cells.join(' × '));
    metric(study.domain_name+' · background spacing (mm)',study.background_spacing_m.map(x=>(x*1000).toFixed(5)).join(' / '));
    metric(study.domain_name+' · verified source reused',study.reused?'Yes':'No');
  }
  for(const pair of data.successive_changes){
    metric(pair.from_domain+' → '+pair.to_domain+' · max velocity change / inlet',(pair.maximum_velocity_change_normalized_by_inlet*100).toFixed(4)+'%');
    metric(pair.from_domain+' → '+pair.to_domain+' · max referenced pressure change / inlet dynamic scale',(pair.maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale*100).toFixed(4)+'%');
  }
  for(const [name,value] of Object.entries(data.checks))metric(name.replaceAll('_',' '),value?'Pass':'Attention');
  metric('Domain convergence','Not established');metric('Mesh independence','Not established');
  for(const p of data.studies[0].probes){const option=document.createElement('option');option.value=p.name;option.textContent=p.name;$('domain-probe').append(option);}
  const show=()=>{$('domain-probes').replaceChildren();for(const p of probeRows(data,$('domain-probe').value)){const row=document.createElement('tr');for(const value of [p.domain,p.speed.toExponential(4),p.pressureDifference.toExponential(4),p.supportRadiusMm.toFixed(3)])cell(row,value);$('domain-probes').append(row);}};
  $('domain-probe').onchange=show;show();
}
