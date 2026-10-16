"""Save source-bound exploratory bracket CFD with independently recomputed diagnostics."""
import base64,csv,hashlib,io,json,os,shutil,tempfile,uuid,zipfile
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from kcee.bracket_flow import make_case,evaluate_case
from kcee.flow_sampling import LEGACY,DEFAULT,flow_version,sampling_spec
class BracketFlowError(ValueError):
 def __init__(self,message,run_id):super().__init__(message);self.run_id=run_id

def verified_archive(payload,raw,mesh_name='coarse',domain_name='base',bore_level=4):
 data=base64.b64decode(payload['archive_base64'],validate=True)
 if len(data)>(48 if mesh_name=='fine' and domain_name=='outer' else 36)*1024*1024 or hashlib.sha256(data).hexdigest()!=payload['archive_sha256']:raise ValueError('Flow archive mismatch')
 with zipfile.ZipFile(io.BytesIO(data)) as z,tempfile.TemporaryDirectory() as tmp:
  names=z.namelist()
  if len(names)!=len(set(names)) or len(names)>200 or sum(i.file_size for i in z.infolist())>(256 if mesh_name=='fine' and domain_name=='outer' else 192)*1024*1024 or any(n.startswith('/') or '..' in n.split('/') for n in names):raise ValueError('Unsafe flow archive')
  runtime=json.loads(z.read('runtime.json'))
  if not runtime['package'].startswith('1912.200626-3') or set(runtime['binaries_sha256'])!={'snappyHexMesh','simpleFoam','checkMesh','surfaceCheck'} or any(len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for v in runtime['binaries_sha256'].values()):raise ValueError('Invalid OpenFOAM runtime record')
  version=flow_version(payload.get('result',{}))
  declared=json.loads(z.read('sampling.json')) if 'sampling.json' in names else sampling_spec(LEGACY)
  if declared!=sampling_spec(version):raise ValueError('Archive sampling version differs from recorded probes')
  profile=payload.get('result',{}).get('inputs',{}).get('local_refinement_profile','baseline')
  expected=Path(tmp)/'expected';metadata=make_case(expected,raw,mesh_name,domain_name,bore_level,profile)
  for p in expected.rglob('*'):
   if p.is_file() and z.read(p.relative_to(expected).as_posix())!=p.read_bytes():raise ValueError('Flow case/source surface differs from fixed configuration')
  root=Path(tmp)/'output'
  needed=['1500/U','1500/p','1500/phi','surfaceCheck.log','checkMesh.log','simpleFoam.log']+['constant/polyMesh/'+n for n in ('points','faces','owner','neighbour','boundary')]
  for name in needed:
   path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(name))
  result=evaluate_case(root,metadata,mesh_name,raw,domain_name,bore_level,version,profile)
  if result!=payload['result']:raise ValueError('Flow diagnostics differ from raw solver evidence')
 return result,data

def run_bracket_flow(root,parent_id,record,mesh_name='coarse',domain_name='base',bore_level=4,sampling_version=DEFAULT,local_profile='baseline'):
 sampling_spec(sampling_version)
 source=Path(root)/str(parent_id);settings=json.loads((source/'geometry-request.json').read_text())
 if settings.get('geometry_mm')!={'length':60,'width':30,'height':40,'thickness':3.5} or not settings.get('mounting_holes'):raise ValueError('Select the default native 60×30×40 mm bracket with bores')
 raw=(source/'bracket.stl').read_bytes();dest=Path(root)/str(uuid.uuid4());dest.mkdir()
 for name in ('requirements.json','bracket.stl','geometry-request.json','geometry.json'):shutil.copy2(source/name,dest/name)
 try:
  request=Request(os.environ.get('CFD_URL','http://cfd:8007')+'/bracket-flow',data=json.dumps({'stl_base64':base64.b64encode(raw).decode(),'mesh_name':mesh_name,'domain_name':domain_name,'bore_level':bore_level,'sampling_version':sampling_version,'local_profile':local_profile}).encode(),headers={'Content-Type':'application/json'},method='POST')
  with urlopen(request,timeout=1080) as response:
   response_limit=(128 if mesh_name=='fine' and domain_name=='outer' else 96)*1024*1024
   encoded=response.read(response_limit+1)
   if len(encoded)>response_limit:raise ValueError('Flow response exceeds limit')
   payload=json.loads(encoded)
  if payload.get('error'):
   archive=base64.b64decode(payload['archive_base64'],validate=True)
   if len(archive)<=36*1024*1024 and hashlib.sha256(archive).hexdigest()==payload['archive_sha256']:(dest/'failed-solver-artifacts.zip').write_bytes(archive)
   raise ValueError('OpenFOAM execution failed; inspect retained solver logs')
  flow,archive=verified_archive(payload,raw,mesh_name,domain_name,bore_level)
  if flow_version(flow)!=sampling_version:raise ValueError('Worker returned a different sampling version')
 except Exception as error:
  (dest/'failure.json').write_text(json.dumps({'run_id':dest.name,'parent_design_id':str(parent_id),'stage':'bracket_flow','status':'failed','message':str(error)[:2000]},indent=2));raise BracketFlowError('Bracket flow failed; retained diagnostics are available.',dest.name) from error
 return save_completed(dest,root,parent_id,record,flow,archive)

def save_completed(dest,root,parent_id,record,flow,archive,origin=None):
 dest=Path(dest);source=Path(root)/str(parent_id)
 result={'kind':'bracket_flow','geometry_backend':'PicoGK source / OpenFOAM external fluid mesh','validation_status':flow['validation_status'],'flow':flow,'assumptions':flow['limits']}
 for name,value in [('result.json',result),('cfd.json',flow),('voice-summary.json',{'text':'Exploratory bracket flow completed. Mesh and domain convergence and engineering validation remain pending.','delivery':'artifact_only'})]:(dest/name).write_text(json.dumps(value,indent=2))
 (dest/'cfd-artifacts.zip').write_bytes(archive)
 requirements=json.loads((dest/'requirements.json').read_text());requirements['bracket_flow']=flow['inputs'];
 if origin:requirements['sampling_origin']=origin
 (dest/'requirements.json').write_text(json.dumps(requirements,indent=2))
 with (dest/'field.csv').open('w',newline='') as stream:
  writer=csv.DictWriter(stream,fieldnames=list(flow['field'][0]));writer.writeheader();writer.writerows(flow['field'])
 report=['# Exploratory native bracket external flow','','Parent: '+str(parent_id),'Status: '+flow['validation_status'],'Source STL SHA-256: '+flow['source']['source_stl_sha256'],'',flow['backend'],'','## Fixed SI inputs and boundary conditions',json.dumps(flow['inputs'],indent=2),'','## Surface and mesh',json.dumps(flow['source'],indent=2),json.dumps(flow['mesh'],indent=2),'Fluid cells: '+str(flow['cells']),'','## Solver diagnostics','Last initial residuals: '+json.dumps(flow['residuals']),'Boundary volume fluxes (m³/s): '+json.dumps(flow['boundary_flux_m3_s']),'Relative boundary imbalance: '+str(flow['relative_boundary_mass_imbalance']),'Final local continuity diagnostic: '+str(flow['final_local_continuity_error']),'Checks: '+json.dumps(flow['checks']),'Tolerances: '+json.dumps(flow['tolerances']),'','## Bore preservation sampling',json.dumps(flow.get('bore_verification'),indent=2),'## Cell position reconstruction and same-field sampling audit',json.dumps(flow.get('cell_position_audit'),indent=2),json.dumps(flow.get('sampling_audit'),indent=2),'## Fixed-location interpolated probes',json.dumps(flow.get('fixed_probes'),indent=2),'## Limitations',*['- '+s for s in flow['limits']],'','field.csv contains cell fields with independently reconstructed triangulated polyhedral volume centroids. cfd-artifacts.zip preserves all case dictionaries, converted surface, actual mesh, final fields, residual logs and runtime fingerprints.']
 report+=['','## Probe sampling version',json.dumps(sampling_spec(flow_version(flow)),indent=2)]
 if origin:report+=['','## Recomputed sampling source (solver fields unchanged)',json.dumps(origin,indent=2)]
 (dest/'report.md').write_text('\n'.join(report)+'\n')
 manifest={'schema_version':1,'kind':'bracket_flow','run_id':dest.name,'parent_design_id':str(parent_id),'created_at':datetime.now(timezone.utc).isoformat(),'software_commit':None,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'solver_source_sha256':hashlib.sha256(Path(__file__).with_name('bracket_flow.py').read_bytes()).hexdigest(),'centroid_source_sha256':hashlib.sha256(Path(__file__).with_name('flow_centres.py').read_bytes()).hexdigest(),'sampling_source_sha256':hashlib.sha256(Path(__file__).with_name('flow_sampling.py').read_bytes()).hexdigest(),'bore_check_source_sha256':hashlib.sha256(Path(__file__).with_name('flow_bores.py').read_bytes()).hexdigest(),'sampling_version':flow_version(flow),'sampling_origin':origin,'source_parent_manifest_sha256':record['manifest_sha256'],'validation_status':flow['validation_status'],'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}}
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2));return dest
