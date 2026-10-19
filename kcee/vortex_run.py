"""Persist independently re-evaluated OpenFOAM vortex outputs and raw solver files."""
import base64,csv,hashlib,io,json,os,re,tempfile,uuid,zipfile
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from kcee.openfoam_vortex import field_values,metrics,combined_summary,make_case,CASE_SPECS

def verify_payload(payload):
 archive=base64.b64decode(payload['archive_base64'],validate=True)
 if len(archive)>16*1024*1024 or hashlib.sha256(archive).hexdigest()!=payload['archive_sha256']:raise ValueError('Solver archive hash mismatch')
 meshes=[];time_rows=[]
 with zipfile.ZipFile(io.BytesIO(archive)) as z,tempfile.TemporaryDirectory() as tmp:
  names=z.namelist()
  if len(names)!=len(set(names)) or len(names)>200 or sum(i.file_size for i in z.infolist())>64*1024*1024 or any(n.startswith('/') or '..' in n.split('/') for n in names):raise ValueError('Unsafe solver archive')
  runtime=json.loads(z.read('runtime.json'))
  if not runtime['package'].startswith('1912.200626-3') or runtime['architecture'] not in ('arm64','amd64') or set(runtime['binaries_sha256'])!={'blockMesh','checkMesh','icoFoam'} or any(not re.fullmatch('[a-f0-9]{64}',v) for v in runtime['binaries_sha256'].values()):raise ValueError('Unexpected OpenFOAM runtime')
  for name,n,dt in CASE_SPECS:
   expected=Path(tmp)/'expected'/name;make_case(expected,n,dt)
   for file in expected.rglob('*'):
    if file.is_file() and z.read(name+'/'+file.relative_to(expected).as_posix())!=file.read_bytes():raise ValueError('Unexpected solver case configuration')
   output=Path(tmp)/name;output.mkdir()
   for field in ('U','p'):(output/field).write_bytes(z.read(f'{name}/0.5/{field}'))
   row=metrics(n,field_values(output/'U',True),field_values(output/'p'))
   log=z.read(f'{name}/icoFoam.log').decode();values=[float(x) for x in re.findall(r'time step continuity errors : sum local = ([^,\s]+)',log)]
   if len(values)!=3*round(.5/dt) or 'Time = 0.5' not in log or '\nEnd\n' not in log:raise ValueError('Incomplete solver history')
   row.update(mesh_check_passed='Mesh OK.' in z.read(f'{name}/checkMesh.log').decode(),maximum_local_continuity_error=max(values),time_step_s=dt)
   if name==str(n):meshes.append(row)
   if n==64:time_rows.append(row)
 time_rows.sort(key=lambda r:-r['time_step_s']);result=combined_summary(meshes,time_rows)
 if result!=payload['result'] or not all(result['checks'].values()):raise ValueError('Vortex verification or worker result comparison failed')
 return result,archive

def run_vortex(root):
 from kcee.cfd_control import checkpoint,headers
 checkpoint('solver',case='Taylor–Green vortex')
 with urlopen(Request(os.environ.get('CFD_URL','http://cfd:8007')+'/vortex',data=b'',headers=headers(),method='POST'),timeout=240) as response:
  raw=response.read(24*1024*1024+1)
  if len(raw)>24*1024*1024:raise ValueError('Solver payload too large')
  payload=json.loads(raw)
 checkpoint('verifying_solver_evidence')
 flow,archive=verify_payload(payload);dest=Path(root)/str(uuid.uuid4());dest.mkdir(parents=True,exist_ok=False)
 result={'kind':'cfd_vortex','validation_status':flow['validation_status'],'geometry_backend':'OpenFOAM periodic reference domain envelope','vortex':flow,'assumptions':flow['limits']}
 for name,data in [('result.json',result),('cfd.json',flow),('requirements.json',flow['inputs']),('voice-summary.json',{'text':'OpenFOAM vortex numerical verification completed. Engineering validation remains pending.','delivery':'artifact_only'})]:(dest/name).write_text(json.dumps(data,indent=2))
 (dest/'cfd-artifacts.zip').write_bytes(archive)
 rows=flow['mesh_study'][-1]['field'];keys=list(rows[0]);(dest/'field.csv').write_text(','.join(keys)+'\n'+'\n'.join(','.join(str(r[k]) for k in keys) for r in rows)+'\n')
 # Preserve one combined scalar table; field.csv remains the spatial fine-grid field.
 columns=['study','cells_per_axis','time_step_s','fine_time_step_s','relative_velocity_l2_error','relative_pressure_l2_error','relative_energy_error','relative_velocity_difference','relative_pressure_difference','maximum_local_continuity_error']
 with (dest/'verification.csv').open('w',newline='') as stream:
  writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
  for kind,rows in [('mesh',flow['mesh_study']),('time',flow['time_study'])]:
   for row in rows:writer.writerow(dict({k:row[k] for k in columns if k in row},study=kind))
  for row in flow['time_refinement']['successive_differences']:writer.writerow({'study':'successive_time_difference','cells_per_axis':64,'time_step_s':row['coarse_time_step_s'],'fine_time_step_s':row['fine_time_step_s'],'relative_velocity_difference':row['relative_velocity_difference'],'relative_pressure_difference':row['relative_pressure_difference']})
 L=flow['inputs']['length_m']*1000;vertices=[(0,0,0),(L,0,0),(L,L,0),(0,L,0),(0,0,100),(L,0,100),(L,L,100),(0,L,100)];faces=[(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
 lines=['solid periodic_domain']
 for face in faces:lines+=['facet normal 0 0 0','outer loop']+['vertex '+' '.join(map(str,vertices[i])) for i in face]+['endloop','endfacet']
 (dest/'bracket.stl').write_text('\n'.join(lines+['endsolid periodic_domain']))
 report=['# OpenFOAM Taylor–Green vortex verification','','Numerical verification; engineering acceptance pending.',flow['backend'],flow['method'],flow['analytical_solution'],'','## Fixed SI inputs',json.dumps(flow['inputs'],indent=2),'','| Grid | Velocity L2 relative error | Pressure L2 relative error | Energy error | Max local continuity error |','|---|---|---|---|---|']
 for m in flow['mesh_study']:report.append(f"| {m['cells_per_axis']}² | {m['relative_velocity_l2_error']} | {m['relative_pressure_l2_error']} | {m['relative_energy_error']} | {m['maximum_local_continuity_error']} |")
 report+=['','## Fixed-grid time refinement','64² cells; all cases end at t=0.5 s. Analytical errors include spatial and temporal error.','| Δt (s) | Steps | Velocity L2 relative error | Pressure L2 relative error | Energy error |','|---|---|---|---|---|']
 for m in flow['time_study']:report.append(f"| {m['time_step_s']} | {round(.5/m['time_step_s'])} | {m['relative_velocity_l2_error']} | {m['relative_pressure_l2_error']} | {m['relative_energy_error']} |")
 report+=['','## Successive time-step field differences','Normalized by the finer numerical field on the same grid, with pressure means removed.','| Coarse Δt | Fine Δt | Relative velocity difference | Relative pressure difference |','|---|---|---|---|']
 for d in flow['time_refinement']['successive_differences']:report.append(f"| {d['coarse_time_step_s']} | {d['fine_time_step_s']} | {d['relative_velocity_difference']} | {d['relative_pressure_difference']} |")
 report+=['','Observed difference orders: '+json.dumps(flow['time_refinement']['observed_difference_orders']),'Time tolerances: '+json.dumps(flow['time_refinement']['tolerances']),flow['time_refinement']['interpretation'],'Study scope: '+json.dumps(flow['study_scope']),'','verification.csv combines scalar mesh/time results and successive differences. field.csv remains the 64² mesh case at Δt=0.005 s; the ZIP and JSON retain all temporal fields.']
 report+=['','Checks: '+json.dumps(flow['checks']),'Tolerances: '+json.dumps(flow['tolerances']),'','## Limitations',*['- '+s for s in flow['limits']],'','Reference: '+flow['reference'],'','Raw OpenFOAM cases, meshes, logs, initial/final fields: cfd-artifacts.zip. field.csv contains fine-grid cell-centre data.']
 (dest/'report.md').write_text('\n'.join(report)+'\n')
 manifest={'schema_version':1,'kind':'cfd_vortex','run_id':dest.name,'parent_design_id':None,'created_at':datetime.now(timezone.utc).isoformat(),'software_commit':None,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'solver_source_sha256':hashlib.sha256(Path(__file__).with_name('openfoam_vortex.py').read_bytes()).hexdigest(),'validation_status':flow['validation_status'],'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}}
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2));return dest
