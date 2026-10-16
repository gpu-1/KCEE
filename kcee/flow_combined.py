"""Joint evidence report: mesh refinement in the far domain and domain sensitivity."""
import base64,csv,hashlib,json,math,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
from kcee.bracket_flow import domain_spec
from kcee.bracket_flow_run import run_bracket_flow,verified_archive
from kcee.flow_refinement import controlled_inputs
from kcee.flow_sampling import PROBES,COMPACT,DEFAULT,LEGACY,common_sampling,sampling_spec,flow_version
from kcee.provenance import verify_directory

LIMITS=[
 'Mesh refinement holds the far-domain bounds, source STL, fluid, boundary types, local refinement recipe and 1500 SIMPLE iterations fixed. Background cell counts and derived nominal local cell sizes change.',
 'Every pressure comparison subtracts the same fixed upstream probe within its case, then compares pressure differences. The reference probe can still be physically influenced by the boundaries.',
 'The domain comparison varies boundary distances at medium resolution; the new mesh comparison varies resolution only in the far domain. This is not a full Cartesian mesh/domain study or an accepted joint error bound.',
 'Successive-difference plots are sensitivity trends, not analytical errors, fitted convergence orders, Richardson extrapolation or engineering acceptance tests.',
 'Volume-centroid reconstruction, custom positive tetrahedral interpolation, finite bore rays, absent prism layers and the exploratory Reynolds-number-6 boundary conditions retain their documented limitations.'
]

def mesh_summary(studies):
 sampling=common_sampling(studies)
 if len(studies)!=3 or [s['flow']['mesh_name'] for s in studies]!=['coarse','medium','fine']:raise ValueError('Use coarse, medium, fine in order')
 if len({s['run_id'] for s in studies})!=3:raise ValueError('Mesh sources must be distinct')
 common=controlled_inputs(studies[0]['flow']);source_hash=studies[0]['flow']['source']['source_stl_sha256'];rows=[]
 for source in studies:
  f=source['flow'];name=f['mesh_name'];spec=domain_spec(name,'far')
  if f.get('domain_name')!='far' or controlled_inputs(f)!=common or f['source']['source_stl_sha256']!=source_hash:raise ValueError('Far-domain mesh physics, bounds or source differ')
  if f['inputs']['background_cells']!=spec['background_cells']:raise ValueError('Mesh background differs from fixed far-domain recipe')
  if any(any(not math.isclose(a,b,rel_tol=1e-13,abs_tol=1e-14) for a,b in zip(f['inputs'][k],spec[k])) for k in ('domain_min_m','domain_max_m')):raise ValueError('Mesh bounds differ from the fixed far domain')
  if f.get('field_position_basis')!='triangulated_polyhedral_volume_centroids':raise ValueError('Use centroid-based mesh probes')
  probes=f.get('fixed_probes',[])
  if [(p['name'],p['requested_position_m']) for p in probes]!=[(n,list(p)) for n,p in PROBES] or not all(p.get('available') for p in probes):raise ValueError('Missing fixed mesh probes')
  if not all(math.isfinite(v) for p in probes for v in [*p['velocity_m_s'],p['kinematic_pressure_m2_s2']]):raise ValueError('Nonfinite mesh probe')
  anchor=next(p['kinematic_pressure_m2_s2'] for p in probes if p['name']=='upstream')
  rows.append({'mesh_name':name,'run_id':source['run_id'],'manifest_sha256':source['manifest_sha256'],'reused':source.get('reused',False),'cells':f['cells'],**spec,'nominal_near_surface_cell_m':f['mesh']['near_surface_nominal_cell_m'],'probes':[dict(p,pressure_minus_upstream_m2_s2=p['kinematic_pressure_m2_s2']-anchor) for p in probes],'upstream_kinematic_pressure_m2_s2':anchor,'solver_checks':f['checks'],'mesh_quality':f['mesh'],'bore_verification':f['bore_verification'],'residuals':f['residuals'],'relative_boundary_mass_imbalance':f['relative_boundary_mass_imbalance'],'cell_position_audit':f['cell_position_audit']})
 changes=[]
 for a,b in zip(rows,rows[1:]):
  probes=[{'name':x['name'],'velocity_vector_change_m_s':math.dist(x['velocity_m_s'],y['velocity_m_s']),'referenced_pressure_change_m2_s2':y['pressure_minus_upstream_m2_s2']-x['pressure_minus_upstream_m2_s2']} for x,y in zip(a['probes'],b['probes'])]
  changes.append({'from_mesh':a['mesh_name'],'to_mesh':b['mesh_name'],'probes':probes,'maximum_velocity_change_normalized_by_inlet':max(p['velocity_vector_change_m_s'] for p in probes)/.01,'maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale':max(abs(p['referenced_pressure_change_m2_s2']) for p in probes)/.00005})
 return {'sampling':sampling,'common_inputs':common,'source_stl_sha256':source_hash,'studies':rows,'successive_changes':changes}

def combined_summary(studies,domain):
 mesh=mesh_summary(studies);data=domain['data']
 if data.get('sampling',sampling_spec(LEGACY))!=mesh['sampling']:raise ValueError('Domain and mesh sampling versions differ')
 if data.get('pressure_reference',{}).get('probe')!='upstream' or data['pressure_reference'].get('position_m')!=[-.03,.015,.020] or data['pressure_reference'].get('normalization_m2_s2')!=.00005:raise ValueError('Domain pressure reference differs')
 if data.get('schema')!=('kcee.bracket-flow-domain.v2' if mesh['sampling']['version']==COMPACT else 'kcee.bracket-flow-domain.v1') or data['source_stl_sha256']!=mesh['source_stl_sha256']:raise ValueError('Domain comparison source/schema differs')
 if data['studies'][-1]['run_id']!=mesh['studies'][1]['run_id'] or data['studies'][-1]['manifest_sha256']!=mesh['studies'][1]['manifest_sha256']:raise ValueError('Reuse the exact verified medium/far source from the domain comparison')
 expected={k:v for k,v in mesh['common_inputs'].items() if k not in ('domain_min_m','domain_max_m')}
 actual=dict(data['common_inputs'])
 if 'bore_refinement' in actual:actual['bore_refinement']={k:v for k,v in actual['bore_refinement'].items() if k!='nominal_cell_m'}
 if actual!=expected:raise ValueError('Domain and far-mesh settings differ')
 checks={'all_mesh_solver_checks':all(all(s['solver_checks'].values()) for s in mesh['studies']),'all_mesh_bore_gates':all(s['bore_verification']['all_pass'] for s in mesh['studies']),'all_domain_checks':all(data['checks'].values()),'far_mesh_cell_counts_increase':all(b['cells']>a['cells'] for a,b in zip(mesh['studies'],mesh['studies'][1:])),'identical_medium_far_source':True}
 return {'sampling':mesh['sampling'],'schema':('kcee.bracket-flow-combined.v2' if mesh['sampling']['version']==COMPACT else 'kcee.bracket-flow-combined.v1'),'source_stl_sha256':mesh['source_stl_sha256'],'mesh_study':mesh,'domain_comparison':domain,'checks':checks,'pressure_reference':data['pressure_reference'],'mesh_independence':'not_established','domain_convergence':'not_established','joint_independence':'not_established','engineering_acceptance':'pending','limits':LIMITS}

def save(root,parent,record,studies,domain):
 data=combined_summary(studies,domain);root=Path(root);dest=root/str(uuid.uuid4());dest.mkdir()
 for name in ('requirements.json','bracket.stl','geometry-request.json','geometry.json'):shutil.copy2(root/str(parent)/name,dest/name)
 requirements=json.loads((dest/'requirements.json').read_text());requirements['flow_combined']={'far_mesh_source_runs':[s['run_id'] for s in studies],'domain_comparison_run_id':domain['run_id']};(dest/'requirements.json').write_text(json.dumps(requirements,indent=2))
 status='exploratory_bracket_flow_combined_recorded_not_engineering_validated'
 for name,value in [('cfd.json',data),('result.json',{'kind':'bracket_flow_combined','validation_status':status,'geometry_backend':'PicoGK / OpenFOAM combined mesh and domain evidence','combined_flow':data,'assumptions':LIMITS}),('voice-summary.json',{'text':'Combined mesh and boundary-distance evidence recorded. Joint independence remains unestablished.','delivery':'artifact_only'})]:(dest/name).write_text(json.dumps(value,indent=2))
 lines=['# Combined bracket-flow mesh and domain verification','','Source STL SHA-256: '+data['source_stl_sha256'],'','Mesh, domain and joint independence remain unestablished. Engineering acceptance is pending.','','## Sampling version',json.dumps(data['sampling'],indent=2),'','## Far-domain controlled mesh inputs',json.dumps(data['mesh_study']['common_inputs'],indent=2),'','| Mesh | Cells | Background cells | Nominal near-surface cell (mm) | Solver / bores |','|---|---|---|---|---|']
 for s in data['mesh_study']['studies']:lines.append(f"| {s['mesh_name']} | {s['cells']} | {s['background_cells']} | {s['nominal_near_surface_cell_m']*1000} | {all(s['solver_checks'].values())} / {s['bore_verification']['all_pass']} |")
 lines+=['','## Pressure reference',json.dumps(data['pressure_reference'],indent=2),'','## Far-domain successive mesh differences',json.dumps(data['mesh_study']['successive_changes'],indent=2),'','## Original medium-resolution domain differences',json.dumps(domain['data']['successive_changes'],indent=2),'','Domain comparison run: '+domain['run_id'],'Domain comparison manifest SHA-256: '+domain['manifest_sha256'],'','## Far-domain source evidence',json.dumps(data['mesh_study']['studies'],indent=2),'','## Limits',*['- '+x for x in LIMITS],'','## Original verified domain report (unaltered)',(root/domain['run_id']/'report.md').read_text()]
 (dest/'report.md').write_text('\n'.join(lines)+'\n')
 with (dest/'verification.csv').open('w',newline='') as stream:
  w=csv.writer(stream);w.writerow(['sampling_version','study','case','run_id','manifest_sha256','cells','probe','requested_position_m','speed_m_s','raw_kinematic_pressure_m2_s2','upstream_kinematic_pressure_m2_s2','pressure_minus_upstream_m2_s2','support_radius_m','support_cell_indices','support_positions_m','weights'])
  for category,rows in [('far_mesh',data['mesh_study']['studies']),('domain',domain['data']['studies'])]:
   for s in rows:
    for p in s['probes']:w.writerow([data['sampling']['version'],category,s.get('mesh_name',s.get('domain_name')),s['run_id'],s['manifest_sha256'],s['cells'],p['name'],json.dumps(p['requested_position_m']),p['speed_m_s'],p['kinematic_pressure_m2_s2'],s['upstream_kinematic_pressure_m2_s2'],p['pressure_minus_upstream_m2_s2'],p['maximum_support_distance_m'],json.dumps(p['support_cell_indices']),json.dumps(p['support_positions_m']),json.dumps(p['weights'])])
 manifest={'schema_version':1,'kind':'bracket_flow_combined','run_id':dest.name,'parent_design_id':str(parent),'created_at':datetime.now(timezone.utc).isoformat(),'sampling_source_sha256':hashlib.sha256(Path(__file__).with_name('flow_sampling.py').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sampling_version':data['sampling']['version'],'source_parent_manifest_sha256':record['manifest_sha256'],'validation_status':status,'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}};(dest/'manifest.json').write_text(json.dumps(manifest,indent=2));return dest

def run_combined(root,parent,record,registry):
 root=Path(root);offset=0;domain=None
 while domain is None:
  items=registry.list(100,offset)
  for item in items:
   if item['kind']=='bracket_flow_domain' and str(item['parent_id'])==str(parent):
    registry.verify(root,item['id']);path=root/str(item['id']);_,digest=verify_directory(path);candidate=json.loads((path/'cfd.json').read_text())
    if candidate.get('sampling')!=sampling_spec(DEFAULT):continue
    domain={'run_id':path.name,'manifest_sha256':digest,'data':candidate};break
  if domain is not None or len(items)<100:break
  offset+=100
 if domain is None:raise ValueError('Run a compact-sampled boundary-distance study first; combined verification requires its exact far-domain medium case')
 medium=domain['data']['studies'][-1];registry.verify(root,medium['run_id']);mp=root/medium['run_id'];manifest,digest=verify_directory(mp)
 if digest!=medium['manifest_sha256'] or manifest.get('source_parent_manifest_sha256')!=record['manifest_sha256']:raise ValueError('Medium/far source identity differs')
 for s in domain['data']['studies']:registry.verify(root,s['run_id'])
 medium_flow=json.loads((mp/'result.json').read_text())['flow']
 if flow_version(medium_flow)!=DEFAULT:raise ValueError('Domain source sampling version differs')
 archive=(mp/'cfd-artifacts.zip').read_bytes()
 verified_archive({'archive_base64':base64.b64encode(archive).decode(),'archive_sha256':hashlib.sha256(archive).hexdigest(),'result':medium_flow},(root/str(parent)/'bracket.stl').read_bytes(),'medium','far')
 studies=[]
 for mesh in ('coarse','medium','fine'):
  if mesh=='medium':studies.append({'run_id':mp.name,'manifest_sha256':digest,'flow':medium_flow,'reused':True});continue
  from kcee.flow_sources import reusable
  existing=reusable(root,parent,record,registry,mesh,'far')
  if existing:studies.append(existing);continue
  dest=run_bracket_flow(root,parent,record,mesh,'far');registry.register(dest);registry.verify(root,dest.name);_,sha=verify_directory(dest);studies.append({'run_id':dest.name,'manifest_sha256':sha,'flow':json.loads((dest/'result.json').read_text())['flow'],'reused':False})
 return save(root,parent,record,studies,domain)
