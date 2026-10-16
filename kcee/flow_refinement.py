"""Three source-bound bracket-flow meshes and a derived sensitivity report."""
import csv,hashlib,json,math,shutil,uuid
from pathlib import Path
from datetime import datetime,timezone
from kcee.bracket_flow_run import run_bracket_flow
from kcee.provenance import verify_directory
PROBES=[('upstream',(-.03,.015,.020)),('wake',(.08,.015,.020)),('above',(.03,.015,.060)),('below',(.03,.015,-.020)),('base bore 1',(.033,.015,.00175)),('base bore 2',(.048,.015,.00175)),('upright bore 1',(.00175,.015,.016)),('upright bore 2',(.00175,.015,.030))]
LIMITS=['Three controlled background meshes with identical source surface, domain, boundary conditions and 500-iteration laminar solver settings; surface refinement level remains 3.','Probe values use the nearest mesh-vertex-average position, not interpolation at an identical physical point. Sampling-position changes contribute to observed field changes.','Bore gates check finite axial rays, not exact open area, minimum diameter or hydraulic resistance.','No prism layers, domain refinement, force convergence, Richardson extrapolation or accepted mesh-independent engineering solution.']
def comparison_summary(studies):
 if len(studies)!=3 or [s['flow'].get('mesh_name') for s in studies]!=['coarse','medium','fine']:raise ValueError('Use coarse, medium and fine studies in order')
 baseline={k:v for k,v in studies[0]['flow']['inputs'].items() if k!='background_cells'}
 if any({k:v for k,v in s['flow']['inputs'].items() if k!='background_cells'}!=baseline for s in studies):raise ValueError('Refinement physical inputs or domains differ')
 hashes={s['flow']['source']['source_stl_sha256'] for s in studies}
 if len(hashes)!=1:raise ValueError('Refinement source surfaces differ')
 rows=[]
 for s in studies:
  flow=s['flow'];probes=[]
  if not flow['field']:raise ValueError('Missing saved fields')
  for name,point in PROBES:
   row=min(flow['field'],key=lambda r:sum((r[k]-v)**2 for k,v in zip(('x_m','y_m','z_m'),point)));distance=math.sqrt(sum((row[k]-v)**2 for k,v in zip(('x_m','y_m','z_m'),point)))
   probes.append({'name':name,'requested_position_m':list(point),'sample_position_m':[row[k] for k in ('x_m','y_m','z_m')],'distance_m':distance,'velocity_m_s':[row[k] for k in ('u_m_s','v_m_s','w_m_s')],'speed_m_s':math.sqrt(sum(row[k]**2 for k in ('u_m_s','v_m_s','w_m_s'))),'kinematic_pressure_m2_s2':row['p_kinematic_m2_s2']})
  rows.append({k:s[k] for k in ('run_id','manifest_sha256')}|{'mesh_name':flow['mesh_name'],'cells':flow['cells'],'background_cells':flow['inputs']['background_cells'],'nominal_near_surface_cell_m':flow['mesh']['near_surface_nominal_cell_m'],'mesh_quality':flow['mesh'],'solver_checks':flow['checks'],'residuals':flow['residuals'],'relative_boundary_mass_imbalance':flow['relative_boundary_mass_imbalance'],'bore_verification':flow['bore_verification'],'probes':probes})
 changes=[]
 for a,b in zip(rows,rows[1:]):
  pair=[]
  for x,y in zip(a['probes'],b['probes']):pair.append({'probe':x['name'],'velocity_vector_change_m_s':math.sqrt(sum((u-v)**2 for u,v in zip(x['velocity_m_s'],y['velocity_m_s']))),'pressure_change_m2_s2':y['kinematic_pressure_m2_s2']-x['kinematic_pressure_m2_s2'],'coarse_sample_distance_m':x['distance_m'],'fine_sample_distance_m':y['distance_m']})
  changes.append({'from_mesh':a['mesh_name'],'to_mesh':b['mesh_name'],'probes':pair,'maximum_velocity_change_normalized_by_inlet':max(p['velocity_vector_change_m_s'] for p in pair)/.01,'maximum_pressure_change_normalized_by_inlet_dynamic_scale':max(abs(p['pressure_change_m2_s2']) for p in pair)/(.5*.01**2)})
 return {'physical_inputs':baseline,'schema':'kcee.bracket-flow-refinement.v1','source_stl_sha256':next(iter(hashes)),'studies':rows,'successive_changes':changes,'checks':{'all_solver_execution_checks':all(all(r['solver_checks'].values()) for r in rows),'all_bore_sampling_gates':all(r['bore_verification']['all_pass'] for r in rows),'cell_counts_increase':all(b['cells']>a['cells'] for a,b in zip(rows,rows[1:]))},'mesh_independence':'not_established','domain_convergence':'not_established','engineering_acceptance':'pending','limits':LIMITS}

def report_markdown(summary):
 lines=['# Native bracket-flow mesh and bore verification','','Source STL SHA-256: '+summary['source_stl_sha256'],'','Engineering acceptance pending. Mesh independence and domain convergence are not established.','','## Common physical inputs (SI)',json.dumps(summary['physical_inputs'],indent=2),'## Saved source studies','| Mesh | Cells | Nominal near-surface size (mm) | Bore sampling | Relative boundary imbalance |','|---|---|---|---|---|']
 for r in summary['studies']:lines.append(f"| {r['mesh_name']} | {r['cells']} | {r['nominal_near_surface_cell_m']*1000} | {r['bore_verification']['all_pass']} | {r['relative_boundary_mass_imbalance']} |")
 for r in summary['studies']:
  lines+=['','## '+r['mesh_name'],'Run: '+r['run_id'],'Manifest SHA-256: '+r['manifest_sha256'],'Solver checks: '+json.dumps(r['solver_checks']),'','| Bore | Source open / rays | Mesh open / rays | Blocked source-open | Unexpected open | Center remains open | Sampling gate |','|---|---|---|---|---|---|---|']
  for h in r['bore_verification']['rows']:lines.append(f"| {h['hole']} | {h['source_open_rays']} / {h['sample_count']} | {h['mesh_open_rays']} / {h['sample_count']} | {h['source_open_rays_blocked_by_mesh']} | {h['unexpected_open_rays']} | {h['mesh_center_open']} | {h['passes_sampling_gate']} |")
  lines+=['','| Probe | Requested position (m) | Sample position (m) | Distance (m) | Speed (m/s) | Kinematic pressure (m²/s²) |','|---|---|---|---|---|---|']
  for p in r['probes']:lines.append(f"| {p['name']} | {p['requested_position_m']} | {p['sample_position_m']} | {p['distance_m']} | {p['speed_m_s']} | {p['kinematic_pressure_m2_s2']} |")
 lines+=['','## Successive field sensitivity','Pressure scale is 0.5 U_inlet² = 0.00005 m²/s². These are changes, not analytical errors.']
 for pair in summary['successive_changes']:lines += [pair['from_mesh']+' → '+pair['to_mesh'], 'Maximum sampled velocity change / inlet speed: '+str(pair['maximum_velocity_change_normalized_by_inlet']), 'Maximum sampled pressure change / inlet dynamic scale: '+str(pair['maximum_pressure_change_normalized_by_inlet_dynamic_scale']),json.dumps(pair['probes'],indent=2)]
 lines+=['','Checks: '+json.dumps(summary['checks']),'','Bore method: '+summary['studies'][0]['bore_verification']['method'],'Bore sampling settings: '+json.dumps({k:v for k,v in summary['studies'][0]['bore_verification'].items() if k!='rows'}),'','## Limits',*['- '+s for s in LIMITS]]
 return '\n'.join(lines)+'\n'

def run_refinement(root,parent_id,record,registry):
 studies=[]
 for mesh in ('coarse','medium','fine'):
  dest=run_bracket_flow(root,parent_id,record,mesh);registry.register(dest);registry.verify(root,dest.name);manifest,digest=verify_directory(dest)
  studies.append({'run_id':dest.name,'manifest_sha256':digest,'flow':json.loads((dest/'result.json').read_text())['flow']})
 return save_comparison(root,parent_id,record,studies)

def save_comparison(root,parent_id,record,studies):
 summary=comparison_summary(studies);dest=Path(root)/str(uuid.uuid4());dest.mkdir();source=Path(root)/str(parent_id)
 for name in ('requirements.json','bracket.stl','geometry-request.json','geometry.json'):shutil.copy2(source/name,dest/name)
 requirements=json.loads((dest/'requirements.json').read_text());requirements['bracket_flow_refinement']={'physical_inputs':summary['physical_inputs'],'source_runs':[s['run_id'] for s in studies]};(dest/'requirements.json').write_text(json.dumps(requirements,indent=2))
 status='exploratory_bracket_flow_refinement_recorded_not_engineering_validated'
 result={'kind':'bracket_flow_refinement','validation_status':status,'geometry_backend':'PicoGK / OpenFOAM mesh sensitivity','flow_refinement':summary,'assumptions':LIMITS}
 for name,data in [('result.json',result),('cfd.json',summary),('voice-summary.json',{'text':'Bracket flow refinement recorded. Review bore preservation and field sensitivity; mesh independence remains unestablished.','delivery':'artifact_only'})]:(dest/name).write_text(json.dumps(data,indent=2))
 with (dest/'verification.csv').open('w',newline='') as stream:
  writer=csv.writer(stream);writer.writerow(['mesh','run_id','manifest_sha256','cells','probe','requested_position_m','sample_position_m','distance_m','speed_m_s','kinematic_pressure_m2_s2','bore_sampling_pass'])
  for r in summary['studies']:
   for p in r['probes']:writer.writerow([r['mesh_name'],r['run_id'],r['manifest_sha256'],r['cells'],p['name'],json.dumps(p['requested_position_m']),json.dumps(p['sample_position_m']),p['distance_m'],p['speed_m_s'],p['kinematic_pressure_m2_s2'],r['bore_verification']['all_pass']])
 (dest/'report.md').write_text(report_markdown(summary))
 manifest={'schema_version':1,'kind':'bracket_flow_refinement','run_id':dest.name,'parent_design_id':str(parent_id),'created_at':datetime.now(timezone.utc).isoformat(),'software_commit':None,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_parent_manifest_sha256':record['manifest_sha256'],'validation_status':status,'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}}
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2));return dest
