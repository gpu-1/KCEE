"""Matched wake/below refinement with unchanged Compact v1 sampling and flow."""
import base64,csv,hashlib,json,math,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
from kcee.bracket_flow import LOCAL_PROFILE,LOCAL_REGIONS,domain_spec
from kcee.bracket_flow_run import run_bracket_flow,verified_archive
from kcee.flow_sampling import COMPACT,PROBES,common_sampling,sampling_spec
from kcee.flow_refinement import controlled_inputs
from kcee.provenance import verify_directory
LIMITS=[
 'Matched baseline/targeted cases use medium and fine backgrounds in the same far domain. Two level-3 boxes refine the wake and below-bracket fluid; general surface, wake level 2 and bore level 4 remain fixed.',
 'Both local regions change together. Snapping and transition-cell topology also change. This does not isolate the contribution of either region or establish a global asymptotic refinement sequence.',
 'Compact v1, fixed probes and within-case upstream subtraction are identical in all four cases. Pressure changes use inlet kinematic dynamic scale 0.00005 m²/s²; velocity-vector changes use inlet speed 0.01 m/s.',
 'The upstream reference can remain boundary-sensitive. Custom bounded-candidate interpolation and triangulated-polyhedron centroids are not native OpenFOAM sampling.',
 'Finite bore rays and solver/mesh gates do not prove hydraulic area, force accuracy, mesh/domain independence or engineering acceptance. No prism layers; exploratory steady laminar Re=6 conditions only.'
]

def summary(sources):
 sampling=common_sampling(sources)
 expected=[('medium','baseline'),('fine','baseline'),('medium',LOCAL_PROFILE),('fine',LOCAL_PROFILE)]
 if sampling['version']!=COMPACT or len(sources)!=4 or [(s['flow']['mesh_name'],s['flow']['inputs'].get('local_refinement_profile','baseline')) for s in sources]!=expected:raise ValueError('Use Compact v1 medium/fine baseline followed by medium/fine targeted cases')
 if len({s['run_id'] for s in sources})!=4:raise ValueError('Use four distinct source cases')
 rows=[];common=None;source_hash=None
 for s in sources:
  f=s['flow'];profile=f['inputs'].get('local_refinement_profile','baseline');spec=domain_spec(f['mesh_name'],'far');controls={k:v for k,v in controlled_inputs(f).items() if k not in ('local_refinement_profile','targeted_refinement')}
  if common is None:common=controls;source_hash=f['source']['source_stl_sha256']
  if controls!=common or f['source']['source_stl_sha256']!=source_hash or f.get('domain_name')!='far' or f['inputs']['bore_refinement']['level']!=4:raise ValueError('Local refinement source, physics, domain or bore recipe differs')
  if any(f['inputs'][k]!=spec[k] for k in ('domain_min_m','domain_max_m','background_cells')):raise ValueError('Local study background/domain recipe differs')
  targeted={'regions':LOCAL_REGIONS,'nominal_cell_m':max(spec['background_spacing_m'])/8}
  if profile==LOCAL_PROFILE and (f['inputs'].get('targeted_refinement')!=targeted or f['mesh'].get('targeted_refinement')!=targeted):raise ValueError('Targeted regions differ from versioned recipe')
  if profile=='baseline' and ('targeted_refinement' in f['inputs'] or 'targeted_refinement' in f['mesh']):raise ValueError('Baseline contains targeted refinement')
  if f.get('field_position_basis')!='triangulated_polyhedral_volume_centroids':raise ValueError('Use centroid-based compact probes')
  probes=f['fixed_probes']
  if [(p['name'],p['requested_position_m']) for p in probes]!=[(n,list(p)) for n,p in PROBES] or not all(p.get('available') for p in probes) or not all(math.isfinite(v) for p in probes for v in [*p['velocity_m_s'],p['kinematic_pressure_m2_s2']]):raise ValueError('Missing or invalid local-study probes')
  anchor=probes[0]['kinematic_pressure_m2_s2']
  rows.append({'run_id':s['run_id'],'manifest_sha256':s['manifest_sha256'],'mesh_name':f['mesh_name'],'local_profile':profile,'cells':f['cells'],'targeted_refinement':f['mesh'].get('targeted_refinement'),'solver_checks':f['checks'],'bore_verification':f['bore_verification'],'mesh_quality':f['mesh'],'residuals':f['residuals'],'relative_boundary_mass_imbalance':f['relative_boundary_mass_imbalance'],'upstream_kinematic_pressure_m2_s2':anchor,'probes':[dict(p,pressure_minus_upstream_m2_s2=p['kinematic_pressure_m2_s2']-anchor) for p in probes]})
 def change(a,b,label):
  probes=[{'name':x['name'],'referenced_pressure_change_m2_s2':y['pressure_minus_upstream_m2_s2']-x['pressure_minus_upstream_m2_s2'],'velocity_vector_change_m_s':math.dist(x['velocity_m_s'],y['velocity_m_s'])} for x,y in zip(a['probes'],b['probes'])]
  return {'label':label,'from_run_id':a['run_id'],'to_run_id':b['run_id'],'probes':probes,'maximum_velocity_change_normalized_by_inlet':max(p['velocity_vector_change_m_s'] for p in probes)/.01,'maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale':max(abs(p['referenced_pressure_change_m2_s2']) for p in probes)/.00005,'largest_pressure_probe':max(probes,key=lambda p:abs(p['referenced_pressure_change_m2_s2']))['name']}
 return {'schema':'kcee.bracket-flow-local.v1','sampling':sampling,'source_stl_sha256':source_hash,'common_inputs':common,'targeted_regions':LOCAL_REGIONS,'studies':rows,'background_mesh_changes':[change(rows[0],rows[1],'Baseline'),change(rows[2],rows[3],'Targeted')],'local_refinement_changes':[change(rows[0],rows[2],'Medium'),change(rows[1],rows[3],'Fine')],'checks':{'all_solver_checks':all(all(s['solver_checks'].values()) for s in rows),'all_bore_opening_gates':all(s['bore_verification']['all_pass'] for s in rows),'targeted_cases_have_more_cells':rows[2]['cells']>rows[0]['cells'] and rows[3]['cells']>rows[1]['cells'],'sampling_and_reference_policy_match':True},'mesh_independence':'not_established','domain_convergence':'not_established','engineering_acceptance':'pending','limits':LIMITS}

def save(root,parent,record,sources):
 data=summary(sources);root=Path(root);dest=root/str(uuid.uuid4());dest.mkdir()
 for n in ('requirements.json','bracket.stl','geometry-request.json','geometry.json'):shutil.copy2(root/str(parent)/n,dest/n)
 req=json.loads((dest/'requirements.json').read_text());req['local_refinement']={'source_runs':[s['run_id'] for s in sources],'targeted_profile':LOCAL_PROFILE};(dest/'requirements.json').write_text(json.dumps(req,indent=2))
 status='exploratory_bracket_flow_local_recorded_not_engineering_validated'
 for name,value in [('cfd.json',data),('result.json',{'kind':'bracket_flow_local','validation_status':status,'geometry_backend':'PicoGK / OpenFOAM local refinement sensitivity','local_refinement':data,'assumptions':LIMITS}),('voice-summary.json',{'text':'Wake and below-bracket refinement compared. Review sensitivity; mesh independence and engineering acceptance remain unestablished.','delivery':'artifact_only'})]:(dest/name).write_text(json.dumps(value,indent=2))
 lines=['# Wake and below-bracket refinement study','','Source STL SHA-256: '+data['source_stl_sha256'],'','Mesh/domain independence is not established. Engineering acceptance is pending.','','## Sampling recipe',json.dumps(data['sampling'],indent=2),'','## Common SI inputs',json.dumps(data['common_inputs'],indent=2),'','## Added physical refinement boxes',json.dumps(LOCAL_REGIONS,indent=2),'','| Mesh | Profile | Cells | Solver / bores | Source run |','|---|---|---|---|---|']
 for s in data['studies']:lines.append(f"| {s['mesh_name']} | {s['local_profile']} | {s['cells']} | {all(s['solver_checks'].values())} / {s['bore_verification']['all_pass']} | {s['run_id']} |")
 for title,key in [('Background mesh changes (medium → fine)','background_mesh_changes'),('Local refinement changes (baseline → targeted)','local_refinement_changes')]:
  lines+=['','## '+title,'| Pair | Max velocity / inlet | Max referenced pressure / ½U² | Largest pressure probe |','|---|---|---|---|']
  for c in data[key]:lines.append(f"| {c['label']} | {c['maximum_velocity_change_normalized_by_inlet']*100:.5f}% | {c['maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale']*100:.5f}% | {c['largest_pressure_probe']} |")
 lines+=['','## Numerical checks',json.dumps(data['checks'],indent=2),'','## Full source and interpolation evidence',json.dumps(data['studies'],indent=2),'','## Limits',*['- '+s for s in LIMITS]];(dest/'report.md').write_text('\n'.join(lines)+'\n')
 with (dest/'verification.csv').open('w',newline='') as stream:
  w=csv.writer(stream);w.writerow(['sampling_version','run_id','manifest_sha256','mesh','local_profile','cells','probe','raw_kinematic_pressure_m2_s2','upstream_kinematic_pressure_m2_s2','pressure_minus_upstream_m2_s2','speed_m_s','maximum_support_distance_m','support_cell_indices','weights'])
  for s in data['studies']:
   for p in s['probes']:w.writerow([COMPACT,s['run_id'],s['manifest_sha256'],s['mesh_name'],s['local_profile'],s['cells'],p['name'],p['kinematic_pressure_m2_s2'],s['upstream_kinematic_pressure_m2_s2'],p['pressure_minus_upstream_m2_s2'],p['speed_m_s'],p['maximum_support_distance_m'],json.dumps(p['support_cell_indices']),json.dumps(p['weights'])])
 manifest={'schema_version':1,'kind':'bracket_flow_local','run_id':dest.name,'parent_design_id':str(parent),'created_at':datetime.now(timezone.utc).isoformat(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sampling_source_sha256':hashlib.sha256(Path(__file__).with_name('flow_sampling.py').read_bytes()).hexdigest(),'source_parent_manifest_sha256':record['manifest_sha256'],'sampling_version':COMPACT,'validation_status':status,'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}};(dest/'manifest.json').write_text(json.dumps(manifest,indent=2));return dest

def run_study(root,parent,record,registry):
 from kcee.flow_sources import reusable
 root=Path(root);sources=[]
 for profile in ('baseline',LOCAL_PROFILE):
  for mesh in ('medium','fine'):
   source=reusable(root,parent,record,registry,mesh,'far',local_profile=profile)
   if source is None:
    if profile=='baseline':raise ValueError('Run a Compact v1 far-domain combined study first; baseline medium/fine cases are required')
    dest=run_bracket_flow(root,parent,record,mesh,'far',4,COMPACT,profile);registry.register(dest);registry.verify(root,dest.name);_,digest=verify_directory(dest);source={'run_id':dest.name,'manifest_sha256':digest,'flow':json.loads((dest/'cfd.json').read_text())}
   sources.append(source)
 return save(root,parent,record,sources)
