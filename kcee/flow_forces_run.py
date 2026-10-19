"""Source-linked force studies without rewriting saved CFD cases."""
import base64,csv,hashlib,json,math,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
from kcee.flow_forces import VERSION,LIMITS,benchmark,from_archive,sub,norm
from kcee.bracket_flow import LOCAL_PROFILE
from kcee.cfd_control import checkpoint,registered
from kcee.provenance import verify_directory
RECIPES=[('medium','far','baseline'),('fine','far','baseline'),('medium','far',LOCAL_PROFILE),('fine','far',LOCAL_PROFILE),('medium','outer',LOCAL_PROFILE),('fine','outer',LOCAL_PROFILE)]
STATUS='exploratory_wall_force_estimate_not_engineering_validated'

def source(root,identifier,registry):
 from kcee.bracket_flow_run import verified_archive
 checkpoint('verifying_sources');registry.verify(root,identifier);path=Path(root)/str(identifier);manifest,digest=verify_directory(path)
 if manifest.get('kind')!='bracket_flow':raise ValueError('Select a saved bracket-flow case')
 flow=json.loads((path/'cfd.json').read_text());archive=(path/'cfd-artifacts.zip').read_bytes()
 payload={'result':flow,'archive_base64':base64.b64encode(archive).decode(),'archive_sha256':hashlib.sha256(archive).hexdigest()}
 verified_archive(payload,(path/'bracket.stl').read_bytes(),flow['mesh_name'],flow.get('domain_name','base'),flow['inputs']['bore_refinement']['level'])
 registered(str(identifier));return {'run_id':str(identifier),'manifest_sha256':digest,'flow':flow}

def summarize(root,sources):
 root=Path(root);rows=[];hashes=set();physics=set();parent_ids=set()
 for s in sources:
  f=s['flow'];checkpoint('integrating_wall_faces',mesh=f['mesh_name'],domain=f.get('domain_name','base'),faces_processed=0)
  path=root/s['run_id'];manifest,digest=verify_directory(path,expected_digest=s['manifest_sha256']);parent_ids.add(manifest['parent_design_id'])
  hashes.add(f['source']['source_stl_sha256']);physics.add((f['inputs']['density_kg_m3'],f['inputs']['kinematic_viscosity_m2_s'],f['inputs']['inlet_velocity_m_s']))
  force=from_archive((path/'cfd-artifacts.zip').read_bytes(),f)
  rows.append({'run_id':s['run_id'],'manifest_sha256':digest,'archive_sha256':manifest['artifacts']['cfd-artifacts.zip'],'mesh_name':f['mesh_name'],'domain_name':f.get('domain_name','base'),'local_profile':f['inputs'].get('local_refinement_profile','baseline'),'cells':f['cells'],'inputs':f['inputs'],'source_checks':f['checks'],'bore_checks_pass':f['bore_verification']['all_pass'],'loads':force})
 if len(hashes)!=1 or len(physics)!=1 or len(parent_ids)!=1 or len({r['run_id'] for r in rows})!=len(rows):raise ValueError('Force comparison sources differ in parent, surface or physics')
 comparisons=[]
 if len(rows)==6:
  recipes=[(r['mesh_name'],r['domain_name'],r['local_profile']) for r in rows]
  if recipes!=RECIPES:raise ValueError('Force comparison recipes differ')
  for a,b,label in [(0,1,'Baseline medium → fine · far'),(2,3,'Targeted medium → fine · far'),(4,5,'Targeted medium → fine · outer'),(2,4,'Medium far → outer'),(3,5,'Fine far → outer + grid')]:
   x,y=rows[a],rows[b];differences={k:sub(y['loads'][k],x['loads'][k]) for k in ('pressure_force_N','viscous_estimate_force_N','total_estimate_force_N','total_estimate_moment_N_m')}
   comparisons.append({'label':label,'from_run_id':x['run_id'],'to_run_id':y['run_id'],'signed_changes':differences,'total_estimate_force_change_normalized':norm(differences['total_estimate_force_N'])/y['loads']['force_normalization_N']})
 elif len(rows)!=1:raise ValueError('Use one source or the fixed six-case comparison')
 checks={'analytical_benchmark':all(benchmark()['checks'].values()),'all_source_solver_checks':all(all(r['source_checks'].values()) for r in rows),'all_bore_gates':all(r['bore_checks_pass'] for r in rows),'all_force_internal_checks':all(all(r['loads']['checks'].values()) for r in rows)}
 return {'schema':'kcee.bracket-flow-forces.v1','method':VERSION,'source_stl_sha256':next(iter(hashes)),'parent_design_id':next(iter(parent_ids)),'studies':rows,'comparisons':comparisons,'benchmark':benchmark(),'checks':checks,'limits':LIMITS,'mesh_independence':'not_established','engineering_acceptance':'pending','native_force_object':'not_used; installed 1912 function-object postprocessing failed in SHA1 IO stream initialization','wall_shear_accuracy':'one-sided estimate; not established for the bracket'}

def save(root,parent,record,data):
 root=Path(root);dest=root/str(uuid.uuid4());dest.mkdir()
 for name in ('requirements.json','bracket.stl','geometry-request.json','geometry.json'):shutil.copy2(root/str(parent)/name,dest/name)
 req=json.loads((dest/'requirements.json').read_text());req['force_study']={'method':VERSION,'source_run_ids':[s['run_id'] for s in data['studies']]};(dest/'requirements.json').write_text(json.dumps(req,indent=2))
 result={'kind':'bracket_flow_forces','geometry_backend':'PicoGK / saved OpenFOAM wall-face traction estimate','validation_status':STATUS,'force_study':data,'assumptions':LIMITS}
 for name,value in [('cfd.json',data),('result.json',result),('voice-summary.json',{'text':'Exploratory pressure loads and wall shear estimates recorded. Force convergence and engineering acceptance remain unestablished.','delivery':'artifact_only'})]:(dest/name).write_text(json.dumps(value,indent=2))
 with (dest/'verification.csv').open('w',newline='') as stream:
  writer=csv.writer(stream);writer.writerow(['method','run_id','manifest_sha256','archive_sha256','mesh','domain','profile','component','pressure_N','viscous_estimate_N','total_estimate_N','pressure_moment_N_m','viscous_estimate_moment_N_m','total_estimate_moment_N_m','coefficient_estimate'])
  for s in data['studies']:
   f=s['loads']
   for i,axis in enumerate('xyz'):writer.writerow([VERSION,s['run_id'],s['manifest_sha256'],s['archive_sha256'],s['mesh_name'],s['domain_name'],s['local_profile'],axis,*[f[k][i] for k in ('pressure_force_N','viscous_estimate_force_N','total_estimate_force_N','pressure_moment_N_m','viscous_estimate_moment_N_m','total_estimate_moment_N_m','force_coefficients_estimate')]])
 lines=['# Bracket pressure loads and wall-shear estimates','','Method: '+VERSION,'','Force from fluid on solid, SI units N and N·m. Moments about (0,0,0) m. Viscous and total loads are estimates, not native OpenFOAM force-function results.','','| Case | Axis | Pressure N | Viscous estimate N | Total estimate N | Total moment estimate N·m |','|---|---|---|---|---|---|']
 for s in data['studies']:
  for i,axis in enumerate('xyz'):lines.append('| '+s['mesh_name']+' / '+s['local_profile']+' / '+s['domain_name']+' | '+axis+' | '+' | '.join(f"{s['loads'][k][i]:.10g}" for k in ('pressure_force_N','viscous_estimate_force_N','total_estimate_force_N','total_estimate_moment_N_m'))+' |')
 lines+=['','## Analytical verification benchmark',json.dumps(data['benchmark'],indent=2),'','## Signed mesh and domain comparisons',json.dumps(data['comparisons'],indent=2),'','## Source and internal checks',json.dumps(data['checks'],indent=2),'','## Source provenance and wall geometry diagnostics']
 for s in data['studies']:lines+=[json.dumps({k:v for k,v in s.items() if k!='loads'},indent=2),json.dumps({k:v for k,v in s['loads'].items() if k!='wall_face_samples'},indent=2)]
 lines+=['','## Limits',*['- '+t for t in LIMITS],'','Reference: https://doc.openfoam.com/2306/tools/post-processing/function-objects/forces/forces/ (native force definition; this estimator is distinct).'];(dest/'report.md').write_text('\n'.join(lines)+'\n')
 manifest={'schema_version':1,'kind':'bracket_flow_forces','run_id':dest.name,'parent_design_id':str(parent),'created_at':datetime.now(timezone.utc).isoformat(),'validation_status':STATUS,'source_parent_manifest_sha256':record['manifest_sha256'],'method':VERSION,'source_runs':[{'run_id':s['run_id'],'manifest_sha256':s['manifest_sha256'],'archive_sha256':s['archive_sha256']} for s in data['studies']],'implementation_sha256':{n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in ('flow_forces.py','flow_forces_run.py','bracket_flow_run.py','flow_centres.py')},'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}}
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2));return dest

def run_study(root,identifier,registry):
 root=Path(root);registry.verify(root,identifier);record=registry.get(identifier)
 if record['manifest'].get('kind')=='bracket_flow':
  sources=[source(root,identifier,registry)];parent=record['parent_id']
 else:
  from kcee.flow_sources import reusable
  parent=identifier;sources=[]
  for mesh,domain,profile in RECIPES:
   s=reusable(root,parent,record,registry,mesh,domain,local_profile=profile)
   if s is None:raise ValueError('Run the Compact v1 mesh/domain comparison first; all six source cases are required')
   sources.append(s)
 registry.verify(root,parent);parent_record=registry.get(parent);data=summarize(root,sources);checkpoint('saving_force_report');return save(root,parent,parent_record,data)

def verify_study(root,identifier,registry):
 registry.verify(root,identifier);path=Path(root)/str(identifier);record=registry.get(identifier)
 if record['manifest']['kind']!='bracket_flow_forces':raise ValueError('Select a force study')
 saved=json.loads((path/'cfd.json').read_text());sources=[]
 for row in saved['studies']:
  s=source(root,row['run_id'],registry)
  if s['manifest_sha256']!=row['manifest_sha256']:raise ValueError('Force source manifest changed')
  sources.append(s)
 actual=summarize(root,sources)
 if actual!=saved:raise ValueError('Force study differs from reproduced wall evidence')
 if json.loads((path/'result.json').read_text())['force_study']!=actual:raise ValueError('Force result differs')
 return {'run_id':str(identifier),'integrity':'verified','force_evidence':'reproduced','method':VERSION,'source_cases':len(sources),'checks':actual['checks'],'engineering_acceptance':'pending'}
