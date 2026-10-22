"""Registered native full-stress studies, separate from historical estimates."""
import base64,csv,hashlib,json,os,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from kcee.native_forces import VERSION,pack,unpack,verify_source,validate_runtime
from kcee.native_force_benchmark import verify as verify_benchmark
from kcee.flow_forces_run import source,RECIPES
from kcee.flow_forces import from_archive as estimate,sub,norm
from kcee.provenance import verify_directory
from kcee.cfd_control import checkpoint,headers
STATUS='exploratory_native_full_stress_not_engineering_validated'
LIMITS=[
 'Native OpenFOAM 1912 forces integrates pressure and the full laminar deviatoric stress, including normal viscous terms and its own gradient/nonorthogonal correction. This does not establish bracket force accuracy or convergence.',
 'The fixed saved Re=6 fields, no-prism-layer mesh, inlet/outlet and far-field assumptions remain unchanged. Native processing reads the final fields; it does not solve new flow iterations.',
 'A narrowly scoped dictionary-hash compatibility overlay is used only by postprocessing; hashing remains enabled. Original meshing/solver executables are unchanged. Build, source, overlay and stress-library fingerprints are recorded.',
 'Independent replay integrates exported native wall stress tensors using source mesh area vectors and exported native face centres. It verifies integration, not an independently solved stress field.',
 'The analytical native benchmark uses prescribed divergence-free affine velocity and affine pressure with exact full-stress integrals. No flow PDE is solved; it does not validate the bracket geometry or flow model.',
 'Pressure moments use native face centres, which differ slightly from the earlier triangulated-face estimate on warped faces. Their uniform-pressure moment closure is retained as a diagnostic, not silently forced to zero.',
 'Forces are fluid on solid in N, moments about (0,0,0) m in N·m. +x follows the inlet. Coefficients retain the declared 0.0012 m² envelope area and 0.5*rho*U²*Aref.',
 'Fine far-to-outer comparison includes small grid spacing/alignment changes. Mesh/domain independence and engineering acceptance remain unestablished. No automatic structural load transfer is performed.'
]

def call(path,body):
 req=Request(os.environ.get('CFD_URL','http://cfd:8007')+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json',**headers()})
 try:
  with urlopen(req,timeout=600) as r:
   raw=r.read(20*1024*1024+1)
   if len(raw)>20*1024*1024:raise ValueError('Native worker response exceeds limit')
   payload=json.loads(raw)
 except HTTPError as error:
  try:message=json.loads(error.read(4096)).get('error','Native CFD worker failed')
  except Exception:message='Native CFD worker failed'
  raise ValueError(str(message)[:1800]) from error
 data=base64.b64decode(payload['archive_base64'],validate=True)
 if len(data)>12*1024*1024 or hashlib.sha256(data).hexdigest()!=payload['archive_sha256']:raise ValueError('Native worker evidence hash differs')
 return data

def summarize(root,sources,blobs):
 root=Path(root);rows=[];parents=set();surfaces=set();physics=set();runtimes=set()
 benchmark=verify_benchmark(blobs['benchmark.zip']);runtimes.add(json.dumps(benchmark['runtime'],sort_keys=True))
 for s in sources:
  f=s['flow'];p=root/s['run_id'];manifest,digest=verify_directory(p,expected_digest=s['manifest_sha256']);parents.add(manifest['parent_design_id']);surfaces.add(f['source']['source_stl_sha256']);physics.add(tuple(f['inputs'][k] for k in ('density_kg_m3','kinematic_viscosity_m2_s','inlet_velocity_m_s')))
  checkpoint('verifying_native_stresses',mesh=f['mesh_name'],domain=f.get('domain_name','base'))
  evidence=blobs[s['run_id']+'.zip'];data=(p/'cfd-artifacts.zip').read_bytes();loads=verify_source(evidence,data,f);old=estimate(data,f);meta=json.loads(unpack(evidence)['runtime.json']);runtimes.add(json.dumps(meta,sort_keys=True))
  difference={key:sub(loads[native],old[prior]) for key,native,prior in [('pressure_force_N','pressure_force_N','pressure_force_N'),('viscous_force_N','viscous_force_N','viscous_estimate_force_N'),('total_force_N','total_force_N','total_estimate_force_N'),('pressure_moment_N_m','pressure_moment_N_m','pressure_moment_N_m'),('viscous_moment_N_m','viscous_moment_N_m','viscous_estimate_moment_N_m'),('total_moment_N_m','total_moment_N_m','total_estimate_moment_N_m')]}
  rows.append({'run_id':s['run_id'],'manifest_sha256':digest,'archive_sha256':manifest['artifacts']['cfd-artifacts.zip'],'native_evidence_sha256':hashlib.sha256(evidence).hexdigest(),'mesh_name':f['mesh_name'],'domain_name':f.get('domain_name','base'),'local_profile':f['inputs'].get('local_refinement_profile','baseline'),'cells':f['cells'],'source_checks':f['checks'],'bore_checks_pass':f['bore_verification']['all_pass'],'loads':loads,'prior_estimate':old,'native_minus_estimate':difference,'runtime':meta})
  if f['inputs'].get('local_refinement_profile') in ('wall-layers-v1','wall-bore-history-v1','wall-bore-history-fine-v2','wall-hotspot-history-v1'):rows[-1]['layer_audit']=f['mesh']['layer_audit']
  if f['inputs'].get('local_refinement_profile') in ('wall-bore-history-v1','wall-bore-history-fine-v2','wall-hotspot-history-v1'):
   history=f['force_history'];runtimes.add(json.dumps(history['runtime'],sort_keys=True));last=history['series'][-1];errors={}
   for key in ('pressure_force_N','viscous_force_N','total_force_N','pressure_moment_N_m','viscous_moment_N_m','total_moment_N_m'):
    scale=max(norm(loads[key]),loads['force_normalization_N']*(.06 if 'moment' in key else 1));errors[key]=norm(sub(last[key],loads[key]))/scale
   if max(errors.values())>1e-6:raise ValueError('Final native history differs from independent postprocessing')
   rows[-1]['force_history']=history;rows[-1]['history_postprocess_relative_differences']=errors;rows[-1]['inputs']=f['inputs'];rows[-1]['mesh_recipe']=f['mesh']
 if len(parents)!=1 or len(surfaces)!=1 or len(physics)!=1 or len(runtimes)!=1 or len({s['run_id'] for s in rows})!=len(rows):raise ValueError('Native source identity/physics/runtime differs')
 comparisons=[]
 if len(rows)==6:
  if [(r['mesh_name'],r['domain_name'],r['local_profile']) for r in rows]!=RECIPES:raise ValueError('Native comparison recipes differ')
  for a,b,label in [(0,1,'Baseline medium → fine · far'),(2,3,'Targeted medium → fine · far'),(4,5,'Targeted medium → fine · outer'),(2,4,'Medium far → outer'),(3,5,'Fine far → outer + grid')]:
   x,y=rows[a],rows[b];differences={k:sub(y['loads'][k],x['loads'][k]) for k in ('pressure_force_N','viscous_force_N','total_force_N','total_moment_N_m')};comparisons.append({'label':label,'from_run_id':x['run_id'],'to_run_id':y['run_id'],'signed_changes':differences,'total_force_change_normalized':norm(differences['total_force_N'])/y['loads']['force_normalization_N']})
 elif len(rows)==4:
  expected=[('medium','far','wake-below-v1'),('fine','far','wake-below-v1'),('medium','far','wall-layers-v1'),('fine','far','wall-layers-v1')]
  if [(r['mesh_name'],r['domain_name'],r['local_profile']) for r in rows]!=expected:raise ValueError('Layer comparison recipes differ')
  for a,b,label in [(0,1,'Without layers: medium → fine'),(2,3,'With layers: medium → fine'),(0,2,'Medium: add near-wall layers'),(1,3,'Fine: add near-wall layers')]:
   x,y=rows[a],rows[b];differences={k:sub(y['loads'][k],x['loads'][k]) for k in ('pressure_force_N','viscous_force_N','total_force_N','total_moment_N_m')}
   comparisons.append({'label':label,'from_run_id':x['run_id'],'to_run_id':y['run_id'],'signed_changes':differences,'total_force_change_normalized':norm(differences['total_force_N'])/y['loads']['force_normalization_N']})
 elif len(rows)==3:
  if [(r['mesh_name'],r['domain_name'],r['local_profile']) for r in rows] not in ([(m,'far','wall-bore-history-v1') for m in ('coarse','medium','fine')],[('coarse','far','wall-bore-history-v1'),('medium','far','wall-bore-history-v1'),('fine','far','wall-bore-history-fine-v2')]):raise ValueError('Force-history recipes differ')
  for a,b in zip(rows,rows[1:]):
   differences={k:sub(b['loads'][k],a['loads'][k]) for k in ('pressure_force_N','viscous_force_N','total_force_N','total_moment_N_m')}
   comparisons.append({'label':a['mesh_name']+' → '+b['mesh_name']+' · wall/bore refinement','from_run_id':a['run_id'],'to_run_id':b['run_id'],'signed_changes':differences,'total_force_change_normalized':norm(differences['total_force_N'])/b['loads']['force_normalization_N']})
 elif len(rows)==2:
  if [(r['mesh_name'],r['domain_name'],r['local_profile']) for r in rows]!=[('fine','far','wall-bore-history-fine-v2'),('fine','far','wall-hotspot-history-v1')]:raise ValueError('Hotspot sensitivity recipes differ')
  x,y=rows;keys=('pressure_force_N','viscous_force_N','total_force_N','pressure_moment_N_m','viscous_moment_N_m','total_moment_N_m');differences={k:sub(y['loads'][k],x['loads'][k]) for k in keys}
  comparisons.append({'label':'Fine v2 → targeted root/upright hotspots','from_run_id':x['run_id'],'to_run_id':y['run_id'],'signed_changes':differences,'total_force_change_normalized':norm(differences['total_force_N'])/y['loads']['force_normalization_N']})
 elif len(rows)!=1:raise ValueError('Use one source or a fixed three/four/six-case native study')
 checks={'native_analytical_benchmark':all(benchmark['checks'].values()),'all_native_integration_replays':all(all(r['loads']['checks'].values()) for r in rows),'all_source_solver_checks':all(all(r['source_checks'].values()) for r in rows),'all_bore_gates':all(r['bore_checks_pass'] for r in rows)}
 limits=LIMITS if not any('layer_audit' in r for r in rows) else [s for s in LIMITS if 'no-prism-layer' not in s]+['Layered and unlayered cases share the far domain, surface refinement and physics. Extrusion moves wall-adjacent cells and can fail locally. Face coverage is not area coverage. Two mesh levels establish sensitivity only; no Richardson order, uncertainty estimate or force convergence is claimed.']
 result={'schema':'kcee.bracket-native-forces.v1','method':VERSION,'parent_design_id':next(iter(parents)),'source_stl_sha256':next(iter(surfaces)),'studies':rows,'comparisons':comparisons,'benchmark':benchmark,'checks':checks,'limits':limits,'mesh_independence':'not_established','engineering_acceptance':'pending'}
 if len(rows)==2:
  result['hotspot_sensitivity']={'method':'paired-hotspot-refinement-v1','changes':{k:{'signed_change':v,'relative_change_to_target_norm':norm(v)/norm(rows[1]['loads'][k]) if norm(rows[1]['loads'][k])>1e-30 else None} for k,v in comparisons[0]['signed_changes'].items()},'iterative_settling':all(r['force_history']['iterative_settling']=='criteria_met' for r in rows),'mesh_convergence':'not_established'}
  result['limits']=[s for s in LIMITS if 'no-prism-layer' not in s and 'only by postprocessing' not in s]+['Fine v2 and targeted root/upright boxes share the fine background, Re=6 physics, far boundaries, 3000 iterations and strict checkMesh gate. Local topology, snapping and actual layer coverage can change. Two cases establish sensitivity only; no convergence order or uncertainty bound is inferred.','Dictionary-digest compatibility is scoped to the fixed history solver and native postprocessing; meshing commands do not preload it.']
  result['checks']['history_final_postprocess_agreement']=True
 if len(rows)==4:result['layer_sensitivity']=layer_sensitivity(rows)
 if len(rows)==3:
  from kcee.force_history import mesh_comparison
  result['force_convergence']=mesh_comparison(rows)
  result['force_convergence']['physics']={k:rows[0]['inputs'][k] for k in ('inlet_velocity_m_s','kinematic_viscosity_m2_s','density_kg_m3','domain_min_m','domain_max_m')}
  result['limits']=[s for s in LIMITS if 'no-prism-layer' not in s and 'only by postprocessing' not in s]+['All three cases use the fixed low-speed laminar Re=6 demonstrator: inlet 0.01 m/s, kinematic viscosity 0.0001 m²/s and density 1 kg/m³. No service-condition, turbulence, thermal or structural validation is inferred.', 'The dictionary-hash compatibility overlay is explicitly scoped to this fixed native-force-history solver invocation and native postprocessing. Meshing commands do not preload it. Fingerprints are retained.', 'Surface level 4, bore level 5 and three requested wall layers are fixed across three background resolutions. Actual layer coverage is measured. These are locally refined meshes, not a uniform Richardson/GCI sequence.', 'Native force and moment histories are recorded at all 3000 iterations. Separate pressure/viscous/total window checks and final postprocess agreement are replayed. A small total change can hide larger opposing component changes.']
  result['checks']['history_final_postprocess_agreement']=True
 if len(rows)==1 and 'force_history' in rows[0]:
  result['limits']=[s for s in LIMITS if 'no-prism-layer' not in s and 'only by postprocessing' not in s]+['This single source uses the fixed Re=6 wall/bore-history recipe with 3000 online force/moment samples. It does not establish mesh independence.', 'The dictionary-digest overlay was scoped to the fixed history solver invocation and native postprocessing; meshing commands did not preload it. Native history and final postprocessing runtime identities and loads are checked.']
  result['checks']['history_final_postprocess_agreement']=True
 return result

def layer_sensitivity(rows):
 output={}
 for name,a,b in [('without_layers',0,1),('with_layers',2,3)]:
  output[name]={}
  for key in ('pressure_force_N','viscous_force_N','total_force_N'):
   x,y=rows[a]['loads'][key],rows[b]['loads'][key];difference=sub(y,x)
   output[name][key]={'signed_change':difference,'change_norm_N':norm(difference),'relative_change_to_fine_norm':norm(difference)/norm(y) if norm(y)>1e-30 else None}
 return {'medium_to_fine':output,'convergence':'not_established','reason':'Two resolutions and partial layer coverage do not support observed-order or extrapolated-error claims.'}

def save(root,parent,record,data,blobs):
 root=Path(root);dest=root/str(uuid.uuid4());dest.mkdir()
 for n in ('requirements.json','bracket.stl','geometry-request.json','geometry.json'):shutil.copy2(root/str(parent)/n,dest/n)
 req=json.loads((dest/'requirements.json').read_text());req['native_force_study']={'method':VERSION,'source_run_ids':[s['run_id'] for s in data['studies']]};(dest/'requirements.json').write_text(json.dumps(req,indent=2))
 result={'kind':'bracket_flow_native_forces','geometry_backend':'PicoGK / native OpenFOAM full stress','validation_status':STATUS,'native_force_study':data,'assumptions':data.get('limits',LIMITS)}
 for n,v in [('result.json',result),('cfd.json',data),('voice-summary.json',{'text':'Native full pressure and viscous loads recorded and compared with the earlier wall shear estimates. Engineering acceptance remains pending.','delivery':'artifact_only'})]:(dest/n).write_text(json.dumps(v,indent=2))
 evidence=pack(blobs)
 if len(evidence)>96*1024*1024:raise ValueError('Combined native evidence exceeds limit')
 (dest/'native-forces.zip').write_bytes(evidence)
 with (dest/'verification.csv').open('w',newline='') as stream:
  w=csv.writer(stream);w.writerow(['method','run_id','manifest_sha256','native_evidence_sha256','mesh','profile','domain','axis','native_pressure_N','native_viscous_N','native_total_N','prior_viscous_estimate_N','native_minus_estimate_viscous_N','native_pressure_moment_N_m','native_viscous_moment_N_m','native_total_moment_N_m'])
  for s in data['studies']:
   for i,a in enumerate('xyz'):w.writerow([VERSION,s['run_id'],s['manifest_sha256'],s['native_evidence_sha256'],s['mesh_name'],s['local_profile'],s['domain_name'],a,s['loads']['pressure_force_N'][i],s['loads']['viscous_force_N'][i],s['loads']['total_force_N'][i],s['prior_estimate']['viscous_estimate_force_N'][i],s['native_minus_estimate']['viscous_force_N'][i],s['loads']['pressure_moment_N_m'][i],s['loads']['viscous_moment_N_m'][i],s['loads']['total_moment_N_m'][i]])
 lines=['# Native bracket pressure and full viscous loads','','Method: '+VERSION,'','Full native Stokes stress; separately registered from historical one-sided estimates. Forces in N; moments about (0,0,0) m in N·m. Native integration reads saved flow fields. Layer comparison source cases are newly solved, with their recipes recorded separately.','','| Case | Axis | Pressure N | Native viscous N | Total N | Prior viscous estimate N |','|---|---|---|---|---|---|']
 for s in data['studies']:
  for i,a in enumerate('xyz'):lines.append('| '+s['mesh_name']+' / '+s['local_profile']+' / '+s['domain_name']+' | '+a+' | '+' | '.join(f'{v:.10g}' for v in [s['loads']['pressure_force_N'][i],s['loads']['viscous_force_N'][i],s['loads']['total_force_N'][i],s['prior_estimate']['viscous_estimate_force_N'][i]])+' |')
 if 'hotspot_sensitivity' in data:lines+=['','## Paired hotspot refinement sensitivity',json.dumps(data['hotspot_sensitivity'],indent=2)]
 if 'force_convergence' in data:lines+=['','## Iterative settling and three-level component sensitivity',json.dumps(data['force_convergence'],indent=2)]
 if 'layer_sensitivity' in data:lines+=['','## Near-wall layer mesh sensitivity',json.dumps(data['layer_sensitivity'],indent=2)]
 lines+=['','## Native analytical benchmark',json.dumps(data['benchmark'],indent=2),'','## Native mesh/domain comparisons',json.dumps(data['comparisons'],indent=2),'','## Checks',json.dumps(data['checks'],indent=2),'','## Source, runtime and full component evidence']
 for s in data['studies']:lines.append(json.dumps({**s,**({'force_history':{k:v for k,v in s['force_history'].items() if k!='series'}} if 'force_history' in s else {}),'loads':{k:v for k,v in s['loads'].items() if k!='wall_samples'},'prior_estimate':{k:v for k,v in s['prior_estimate'].items() if k!='wall_face_samples'}},indent=2))
 lines+=['','## Limits',*['- '+s for s in data.get('limits',LIMITS)]];(dest/'report.md').write_text('\n'.join(lines)+'\n')
 if 'force_convergence' in data or 'hotspot_sensitivity' in data:
  with (dest/'force-history.csv').open('w',newline='') as stream:
   writer=csv.writer(stream);keys=[k for k in data['studies'][0]['force_history']['series'][0] if k!='iteration'];writer.writerow(['run_id','mesh','iteration']+[k+'_'+axis for k in keys for axis in 'xyz'])
   for study in data['studies']:
    for row in study['force_history']['series']:writer.writerow([study['run_id'],study['mesh_name'],row['iteration']]+[v for k in keys for v in row[k]])
 implementation=('native_forces.py','native_force_benchmark.py','native_forces_run.py','flow_forces.py','flow_forces_run.py','cfd_control.py')
 if len(data['studies'])==2:implementation+=('force_history.py','hotspot_refinement.py','bracket_flow.py','bracket_flow_run.py')
 if len(data['studies'])==3:implementation+=('force_history.py','force_convergence_run.py','bracket_flow.py','bracket_flow_run.py')
 if len(data['studies'])==4:implementation+=('layer_forces_run.py','bracket_flow.py','bracket_flow_run.py')
 m={'schema_version':1,'run_id':dest.name,'kind':'bracket_flow_native_forces','parent_design_id':str(parent),'source_parent_manifest_sha256':record['manifest_sha256'],'created_at':datetime.now(timezone.utc).isoformat(),'validation_status':STATUS,'method':VERSION,'implementation_sha256':{n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in implementation},'source_runs':[{'run_id':s['run_id'],'manifest_sha256':s['manifest_sha256'],'native_evidence_sha256':s['native_evidence_sha256']} for s in data['studies']],'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}};(dest/'manifest.json').write_text(json.dumps(m,indent=2));return dest

def run_study(root,identifier,registry):
 root=Path(root);registry.verify(root,identifier);record=registry.get(identifier)
 if record['manifest'].get('kind')=='bracket_flow':sources=[source(root,identifier,registry)];parent=record['parent_id']
 else:
  from kcee.flow_sources import reusable
  parent=identifier;sources=[]
  for mesh,domain,profile in RECIPES:
   s=reusable(root,parent,record,registry,mesh,domain,local_profile=profile)
   if s is None:raise ValueError('Run the Compact v1 six-case mesh/domain study first')
   sources.append(s)
 blobs={};checkpoint('native_force_benchmark');blobs['benchmark.zip']=call('/native-force-benchmark',{})
 for s in sources:
  f=s['flow'];p=root/s['run_id'];archive=(p/'cfd-artifacts.zip').read_bytes();checkpoint('native_force_postprocess',mesh=f['mesh_name'],domain=f.get('domain_name','base'))
  blobs[s['run_id']+'.zip']=call('/native-forces',{'archive_base64':base64.b64encode(archive).decode(),'archive_sha256':hashlib.sha256(archive).hexdigest(),'stl_base64':base64.b64encode((p/'bracket.stl').read_bytes()).decode(),'mesh_name':f['mesh_name'],'domain_name':f.get('domain_name','base'),'bore_level':f['inputs']['bore_refinement']['level'],'local_profile':f['inputs'].get('local_refinement_profile','baseline')})
 registry.verify(root,parent);data=summarize(root,sources,blobs);checkpoint('saving_native_force_report');return save(root,parent,registry.get(parent),data,blobs)

def verify_study(root,identifier,registry):
 root=Path(root);registry.verify(root,identifier);record=registry.get(identifier)
 if record['manifest']['kind']!='bracket_flow_native_forces':raise ValueError('Select a native force study')
 p=root/str(identifier);saved=json.loads((p/'cfd.json').read_text());sources=[]
 # Outer archive contains only a fixed benchmark ZIP and bounded per-source ZIPs.
 import zipfile,io
 raw=(p/'native-forces.zip').read_bytes()
 if len(raw)>96*1024*1024:raise ValueError('Native report archive exceeds limit')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  names={'benchmark.zip'}|{s['run_id']+'.zip' for s in saved['studies']}
  if len(z.namelist())!=len(names) or set(z.namelist())!=names or sum(i.file_size for i in z.infolist())>96*1024*1024:raise ValueError('Native report inventory differs')
  blobs={n:z.read(n) for n in names}
 for s in saved['studies']:
  current=source(root,s['run_id'],registry)
  if current['manifest_sha256']!=s['manifest_sha256']:raise ValueError('Native source manifest differs')
  sources.append(current)
 actual=summarize(root,sources,blobs)
 if actual!=saved or json.loads((p/'result.json').read_text())['native_force_study']!=saved:raise ValueError('Native evidence differs from reproduced full-stress integration')
 return {'run_id':str(identifier),'integrity':'verified','native_force_evidence':'reproduced','source_cases':len(sources),'method':VERSION,'checks':actual['checks'],'engineering_acceptance':'pending'}
