"""Controlled boundary-distance sensitivity at fixed medium background spacing."""
import base64,csv,hashlib,json,math,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
from kcee.bracket_flow import domain_spec
from kcee.bracket_flow_run import run_bracket_flow,verified_archive
from kcee.flow_sampling import PROBES
from kcee.provenance import verify_directory

DOMAINS=('base','expanded','far')
LIMITS=[
 'Three nested domains use medium background spacing, integer-cell boundary shifts, identical local refinement, source STL, inlet, viscosity, boundary types and 1500 SIMPLE iterations.',
 'Pressure differences subtract the same fixed upstream probe in each domain. This removes a uniform pressure-reference shift; the upstream probe can still be physically influenced by the boundaries.',
 'Background spacing and alignment are controlled. Actual snapped cells can change; this is a discrete domain sensitivity study, not a pure continuum boundary-error estimate.',
 'Custom positive tetrahedral interpolation uses independently reconstructed triangulated-polyhedron volume centroids, not OpenFOAM native cell-center export.',
 'Finite bore samples and solver gates do not establish mesh/domain independence, force accuracy or engineering acceptance. No prism layers or mounting wall are included.'
]

def controls(flow):
 return {k:v for k,v in flow['inputs'].items() if k not in ('domain_min_m','domain_max_m','background_cells')}

def summary(studies):
 if len(studies)!=3 or [s['flow'].get('domain_name','base') for s in studies]!=list(DOMAINS):raise ValueError('Provide base, expanded and far domains in order')
 if len({s['run_id'] for s in studies})!=3:raise ValueError('Domain source studies must be distinct')
 if len({s['flow']['source']['source_stl_sha256'] for s in studies})!=1:raise ValueError('Domain source surfaces differ')
 common=controls(studies[0]['flow']);rows=[]
 for source,name in zip(studies,DOMAINS):
  flow=source['flow'];spec=domain_spec('medium',name)
  if flow.get('mesh_name')!='medium' or controls(flow)!=common:raise ValueError('Domain flow physics or local mesh recipe differs')
  for key in ('domain_min_m','domain_max_m','background_cells'):
   if len(flow['inputs'][key])!=3 or any(not math.isclose(a,b,rel_tol=1e-13,abs_tol=1e-14) for a,b in zip(flow['inputs'][key],spec[key])):raise ValueError('Domain bounds or background spacing differs from the controlled recipe')
  if flow.get('field_position_basis')!='triangulated_polyhedral_volume_centroids':raise ValueError('Domain probes require centroid-based sampling')
  probes=flow.get('fixed_probes',[])
  if [(p['name'],p['requested_position_m']) for p in probes]!=[(n,list(x)) for n,x in PROBES] or not all(p.get('available') for p in probes):raise ValueError('Fixed domain probes are missing or unavailable')
  if not all(math.isfinite(v) for p in probes for v in [*p['velocity_m_s'],p['kinematic_pressure_m2_s2']]):raise ValueError('Nonfinite domain probe values')
  anchor=next(p['kinematic_pressure_m2_s2'] for p in probes if p['name']=='upstream')
  lo=spec['domain_min_m'];hi=spec['domain_max_m']
  rows.append({'domain_name':name,'run_id':source['run_id'],'manifest_sha256':source['manifest_sha256'],'reused':source.get('reused',False),'cells':flow['cells'],**spec,'boundary_clearances_m':{'inlet':-lo[0],'outlet':hi[0]-.06,'negative_y':-lo[1],'positive_y':hi[1]-.03,'negative_z':-lo[2],'positive_z':hi[2]-.04},'upstream_kinematic_pressure_m2_s2':anchor,'probes':[dict(p,pressure_minus_upstream_m2_s2=p['kinematic_pressure_m2_s2']-anchor) for p in probes],'solver_checks':flow['checks'],'residuals':flow['residuals'],'relative_boundary_mass_imbalance':flow['relative_boundary_mass_imbalance'],'mesh_quality':flow['mesh'],'bore_verification':flow['bore_verification'],'cell_position_audit':flow['cell_position_audit']})
 changes=[]
 for a,b in zip(rows,rows[1:]):
  probes=[{'name':x['name'],'velocity_vector_change_m_s':math.dist(x['velocity_m_s'],y['velocity_m_s']),'referenced_pressure_change_m2_s2':y['pressure_minus_upstream_m2_s2']-x['pressure_minus_upstream_m2_s2']} for x,y in zip(a['probes'],b['probes'])]
  changes.append({'from_domain':a['domain_name'],'to_domain':b['domain_name'],'probes':probes,'maximum_velocity_change_normalized_by_inlet':max(p['velocity_vector_change_m_s'] for p in probes)/.01,'maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale':max(abs(p['referenced_pressure_change_m2_s2']) for p in probes)/.00005})
 return {'schema':'kcee.bracket-flow-domain.v1','source_stl_sha256':studies[0]['flow']['source']['source_stl_sha256'],'common_inputs':common,'pressure_reference':{'probe':'upstream','position_m':[-.03,.015,.020],'definition':'p_kinematic(probe) - p_kinematic(upstream), within each domain','normalization_m2_s2':.00005},'studies':rows,'successive_changes':changes,'checks':{'all_solver_execution_checks':all(all(s['solver_checks'].values()) for s in rows),'all_bore_sampling_gates':all(s['bore_verification']['all_pass'] for s in rows),'all_fixed_location_probes_available':True,'controlled_background_spacing_and_alignment':True,'domain_extents_increase':True},'mesh_independence':'not_established','domain_convergence':'not_established','engineering_acceptance':'pending','limits':LIMITS}

def report_markdown(data):
 lines=['# Bracket-flow boundary-distance study','','Source STL SHA-256: '+data['source_stl_sha256'],'','Domain and mesh independence are not established. Engineering acceptance is pending.','','## Controlled inputs',json.dumps(data['common_inputs'],indent=2),'','## Pressure reference',json.dumps(data['pressure_reference'],indent=2),'','| Domain | Cells | Background cells | Minimum (m) | Maximum (m) | Reused verified source |','|---|---|---|---|---|---|']
 for row in data['studies']:lines.append(f"| {row['domain_name']} | {row['cells']} | {row['background_cells']} | {row['domain_min_m']} | {row['domain_max_m']} | {row['reused']} |")
 for row in data['studies']:
  lines+=['','## '+row['domain_name'],'Run: '+row['run_id'],'Manifest SHA-256: '+row['manifest_sha256'],'Background spacing (m): '+json.dumps(row['background_spacing_m']),'Clearances from bracket envelope (m): '+json.dumps(row['boundary_clearances_m']),'Solver checks: '+json.dumps(row['solver_checks']),'Residuals: '+json.dumps(row['residuals']),'Relative boundary imbalance: '+str(row['relative_boundary_mass_imbalance']),'Mesh quality: '+json.dumps(row['mesh_quality']),'Bore evidence: '+json.dumps(row['bore_verification']),'Cell-position audit: '+json.dumps(row['cell_position_audit']),'','| Probe | Speed (m/s) | Raw p/rho (m²/s²) | (p-p_upstream)/rho (m²/s²) | Support radius (m) |','|---|---|---|---|---|']
  for p in row['probes']:lines.append(f"| {p['name']} | {p['speed_m_s']} | {p['kinematic_pressure_m2_s2']} | {p['pressure_minus_upstream_m2_s2']} | {p['maximum_support_distance_m']} |")
  lines+=['','Full fixed-coordinate interpolation supports:',json.dumps(row['probes'],indent=2)]
 lines+=['','## Successive sensitivity (not analytical errors)',json.dumps(data['successive_changes'],indent=2),'','Checks: '+json.dumps(data['checks']),'','## Limits',*['- '+x for x in LIMITS]]
 return '\n'.join(lines)+'\n'

def save(root,parent,record,studies):
 data=summary(studies);root=Path(root);dest=root/str(uuid.uuid4());dest.mkdir()
 for name in ('requirements.json','bracket.stl','geometry-request.json','geometry.json'):shutil.copy2(root/str(parent)/name,dest/name)
 requirements=json.loads((dest/'requirements.json').read_text());requirements['flow_domain_study']={'common_inputs':data['common_inputs'],'source_runs':[s['run_id'] for s in studies]};(dest/'requirements.json').write_text(json.dumps(requirements,indent=2))
 status='exploratory_bracket_flow_domain_recorded_not_engineering_validated'
 for name,value in [('cfd.json',data),('result.json',{'kind':'bracket_flow_domain','validation_status':status,'geometry_backend':'PicoGK / OpenFOAM domain sensitivity','domain_study':data,'assumptions':LIMITS}),('voice-summary.json',{'text':'Boundary-distance study recorded. Review referenced pressure changes. Domain and mesh independence remain unestablished.','delivery':'artifact_only'})]:(dest/name).write_text(json.dumps(value,indent=2))
 with (dest/'verification.csv').open('w',newline='') as stream:
  writer=csv.writer(stream);writer.writerow(['domain','run_id','manifest_sha256','cells','probe','requested_position_m','speed_m_s','raw_kinematic_pressure_m2_s2','upstream_kinematic_pressure_m2_s2','pressure_minus_upstream_m2_s2','support_radius_m','support_cell_indices','support_positions_m','weights'])
  for row in data['studies']:
   for p in row['probes']:writer.writerow([row['domain_name'],row['run_id'],row['manifest_sha256'],row['cells'],p['name'],json.dumps(p['requested_position_m']),p['speed_m_s'],p['kinematic_pressure_m2_s2'],row['upstream_kinematic_pressure_m2_s2'],p['pressure_minus_upstream_m2_s2'],p['maximum_support_distance_m'],json.dumps(p['support_cell_indices']),json.dumps(p['support_positions_m']),json.dumps(p['weights'])])
 (dest/'report.md').write_text(report_markdown(data))
 manifest={'schema_version':1,'kind':'bracket_flow_domain','run_id':dest.name,'parent_design_id':str(parent),'created_at':datetime.now(timezone.utc).isoformat(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_parent_manifest_sha256':record['manifest_sha256'],'validation_status':status,'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}}
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2));return dest

def reusable_base(root,parent,record,registry):
 root=Path(root);raw=(root/str(parent)/'bracket.stl').read_bytes();offset=0
 while True:
  entries=registry.list(100,offset)
  for item in entries:
   if item['kind']!='bracket_flow' or str(item['parent_id'])!=str(parent):continue
   registry.verify(root,item['id']);path=root/str(item['id']);manifest,digest=verify_directory(path);flow=json.loads((path/'result.json').read_text()).get('flow',{})
   if flow.get('mesh_name')!='medium' or flow.get('domain_name','base')!='base' or not all(flow.get('checks',{}).values()) or not flow.get('bore_verification',{}).get('all_pass'):continue
   if manifest.get('source_parent_manifest_sha256')!=record['manifest_sha256']:continue
   archive=(path/'cfd-artifacts.zip').read_bytes()
   try:verified_archive({'archive_base64':base64.b64encode(archive).decode(),'archive_sha256':hashlib.sha256(archive).hexdigest(),'result':flow},raw,'medium','base')
   except ValueError:continue  # Historical recipes are not interchangeable with current cases.
   return {'run_id':path.name,'manifest_sha256':digest,'flow':flow,'reused':True}
  if len(entries)<100:return None
  offset+=100

def run_domains(root,parent,record,registry):
 studies=[];base=reusable_base(root,parent,record,registry)
 for name in DOMAINS:
  if name=='base' and base:studies.append(base);continue
  dest=run_bracket_flow(root,parent,record,'medium',name);registry.register(dest);registry.verify(root,dest.name);_,digest=verify_directory(dest)
  studies.append({'run_id':dest.name,'manifest_sha256':digest,'flow':json.loads((dest/'result.json').read_text())['flow'],'reused':False})
 return save(root,parent,record,studies)
