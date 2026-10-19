"""Native OpenFOAM stress postprocessing and independently replayed wall loads."""
import base64,hashlib,io,json,math,os,re,subprocess,tempfile,zipfile
from pathlib import Path
from kcee.flow_forces import face_geometry,cross,scale,norm,sub,add
from kcee.cfd_control import checkpoint,run_logged
from kcee.openfoam_vortex import header,field_values
VERSION='openfoam-full-stress-v1'
NATIVE=Path('/opt/kcee/native')
FILES={'force.dat','moment.dat','wall-centres.foam','wall-stress.foam','postprocess.log','controlDict','runtime.json'}

def functions(patch,rho):
 if patch not in ('bracket','bottom') or not math.isfinite(rho) or rho<=0:raise ValueError('Invalid native patch or density')
 return '''\nfunctions {
 bodyForces {type forces; libs ("libforces.so"); patches ('''+patch+'''); rho rhoInf; rhoInf '''+format(rho,'.15g')+'''; pRef 0; CofR (0 0 0); writeControl timeStep; writeInterval 1;}
 stressExport {type turbulenceFields; libs ("libfieldFunctionObjects.so"); fields (devReff); writeControl timeStep; writeInterval 1;}
 centresExport {type writeCellCentres; libs ("libfieldFunctionObjects.so"); writeControl timeStep; writeInterval 1;}
}\n'''

def pack(files):
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
  for n,v in sorted(files.items()):z.writestr(n,v)
 return b.getvalue()

def unpack(data,required=FILES):
 if len(data)>12*1024*1024:raise ValueError('Native evidence archive exceeds limit')
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  names=z.namelist()
  if len(names)!=len(set(names)) or set(names)!=set(required) or sum(i.file_size for i in z.infolist())>64*1024*1024:raise ValueError('Unexpected native evidence inventory or size')
  return {n:z.read(n) for n in names}

def patch_text(text,patch):
 matches=re.findall(r'\b'+re.escape(patch)+r'\s*\{([^{}]*)\}',text,re.S)
 if len(matches)!=1:raise ValueError('Missing/ambiguous native wall field')
 return patch+'\n{'+matches[0]+'}\n'

def boundary_values(raw,count,components):
 text=raw.decode() if isinstance(raw,bytes) else raw
 types={3:'vector',6:'symmTensor'}
 m=re.search(r'\bvalue\s+nonuniform\s+List<'+types[components]+r'>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
 if m:
  rows=[list(map(float,v.split())) for v in re.findall(r'\(([^()]*)\)',m[2])]
  if int(m[1])!=count or len(rows)!=count:raise ValueError('Native wall field count mismatch')
 else:
  m=re.search(r'\bvalue\s+uniform\s+\(([^()]*)\)\s*;',text)
  if not m:raise ValueError('Missing native wall values')
  rows=[list(map(float,m[1].split())) for _ in range(count)]
 if any(len(r)!=components or not all(math.isfinite(v) for v in r) for r in rows):raise ValueError('Nonfinite/malformed native wall field')
 return rows

def native_vectors(raw,time):
 text=raw.decode() if isinstance(raw,bytes) else raw
 rows=[l.strip() for l in text.splitlines() if l.strip() and not l.lstrip().startswith('#')]
 if len(rows)!=1:raise ValueError('Expected one native force sample')
 line=rows[0];vectors=[list(map(float,v.split())) for v in re.findall(r'\(([^()]*)\)',line)]
 if float(line.split()[0])!=time or len(vectors)!=3 or any(len(v)!=3 or not all(math.isfinite(x) for x in v) for v in vectors):raise ValueError('Invalid native force time or components')
 if norm(sub(vectors[0],add(vectors[1],vectors[2])))>1e-11*max(norm(vectors[0]),norm(vectors[1]),norm(vectors[2]),1e-30):raise ValueError('Native total/pressure/viscous components differ')
 return dict(zip(('total','pressure','viscous'),vectors))

def mesh_patch(root,patch):
 from kcee.bracket_flow import mesh_list
 root=Path(root);n,raw=mesh_list(root/'points');points=[list(map(float,v.split())) for v in re.findall(r'\(([^()]*)\)',raw)]
 nf,raw=mesh_list(root/'faces');faces=[list(map(int,v.split())) for v in re.findall(r'\d+\(([^()]*)\)',raw)]
 no,raw=mesh_list(root/'owner');owners=list(map(int,raw.split()));ni,_=mesh_list(root/'neighbour')
 b=patch_text((root/'boundary').read_text(),patch);count=int(re.search(r'nFaces\s+(\d+)',b)[1]);start=int(re.search(r'startFace\s+(\d+)',b)[1])
 if n!=len(points) or nf!=len(faces) or nf!=len(owners) or no!=nf or start<ni or not 0<count<=nf-start:raise ValueError('Native wall mesh addressing differs')
 selected=[]
 for i,face in enumerate(faces[start:start+count]):
  if len(face)<3 or any(not 0<=v<n for v in face):raise ValueError('Invalid native wall face vertices')
  sf,_,_=face_geometry([points[v] for v in face]);selected.append((start+i,owners[start+i],sf))
 return selected

def runtime():
 build=json.loads((NATIVE/'build.json').read_text())
 for n,digest in build['binaries_sha256'].items():
  if hashlib.sha256((NATIVE/n).read_bytes()).hexdigest()!=digest:raise ValueError('Native compatibility binary changed')
 import shutil
 return {'method':VERSION,'package':subprocess.check_output(['dpkg-query','-W','-f=${Version}','openfoam'],text=True),'simpleFoam_sha256':hashlib.sha256(Path(shutil.which('simpleFoam')).read_bytes()).hexdigest(),'overlay':build,'libraries_sha256':{n:hashlib.sha256((Path('/usr/lib')/n).read_bytes()).hexdigest() for n in ('libOpenFOAM.so','libforces.so','libincompressibleTurbulenceModels.so','libincompressibleTransportModels.so')}}

def validate_runtime(meta):
 if meta.get('method')!=VERSION or not meta.get('package','').startswith('1912.200626-3'):raise ValueError('Native runtime package/method differs')
 build=meta.get('overlay',{})
 if build.get('source_sha256')!='c75ca0f04cc4f49708296c1926cbde9d0138b3fef298fed54270dfe29e2df404' or build.get('scope') not in __import__('kcee.force_history',fromlist=['SCOPES']).SCOPES:raise ValueError('Native compatibility scope differs')
 for key,names in [('binaries_sha256',{'libkceeDigest.so','hash-self-test'}),('implementation_sha256',{'build.py','digest.cpp','hash_test.cpp','exports.map'})]:
  values=build.get(key,{})
  if set(values)!=names or not all(re.fullmatch('[a-f0-9]{64}',v or '') for v in values.values()):raise ValueError('Native compatibility fingerprints missing')
 libraries=meta.get('libraries_sha256',{})
 if set(libraries)!={'libOpenFOAM.so','libforces.so','libincompressibleTurbulenceModels.so','libincompressibleTransportModels.so'} or not all(re.fullmatch('[a-f0-9]{64}',v or '') for v in libraries.values()) or not re.fullmatch('[a-f0-9]{64}',meta.get('simpleFoam_sha256','')):raise ValueError('Native solver/library fingerprints missing')
 return meta

def execute_case(root,time,patch,rho):
 root=Path(root);p=root/'system/controlDict';p.write_bytes(__import__('kcee.force_history',fromlist=['postprocess_control']).postprocess_control(p.read_bytes())+functions(patch,rho).encode())
 checkpoint('native_force_postprocess',case='Native '+patch+' stresses')
 env={**os.environ,'LD_PRELOAD':str(NATIVE/'libkceeDigest.so')}
 proc=run_logged(['simpleFoam','-case',str(root),'-postProcess','-time',str(time)],root,'native_force_postprocess',180,env=env)
 if proc.returncode:raise ValueError('Native force postprocessing failed: '+(root/'native_force_postprocess.log').read_text()[-1800:])
 def fragment(name):
  text=(root/str(time)/name).read_text();dimensions=re.search(r'dimensions\s*\[[^]]+\]\s*;',text)
  if not dimensions:raise ValueError('Native field dimensions missing')
  return dimensions[0]+'\n'+patch_text(text,patch)
 force=list((root/'postProcessing/bodyForces').glob('*/force.dat'));moment=list((root/'postProcessing/bodyForces').glob('*/moment.dat'))
 if len(force)!=1 or len(moment)!=1:raise ValueError('Missing native force/moment evidence')
 files={'force.dat':force[0].read_bytes(),'moment.dat':moment[0].read_bytes(),'wall-centres.foam':fragment('C'),'wall-stress.foam':fragment('turbulenceProperties:devReff'),'postprocess.log':(root/'native_force_postprocess.log').read_bytes(),'controlDict':p.read_bytes(),'runtime.json':json.dumps(runtime(),indent=2)}
 return files

def integrate(files,mesh,pressures,rho,normalization,time):
 if not re.search(rb'dimensions\s*\[0 1 0 0 0 0 0\]',files['wall-centres.foam']) or not re.search(rb'dimensions\s*\[0 2 -2 0 0 0 0\]',files['wall-stress.foam']):raise ValueError('Native geometry/stress units differ')
 centres=boundary_values(files['wall-centres.foam'],len(mesh),3);stress=boundary_values(files['wall-stress.foam'],len(mesh),6)
 native_force=native_vectors(files['force.dat'],time);native_moment=native_vectors(files['moment.dat'],time)
 pressure=[];viscous=[];mp=[];mv=[];areas=[];moment_areas=[];trace=0.;samples=[]
 for i,((face,owner,sf),c,t) in enumerate(zip(mesh,centres,stress)):
  if i%1000==0:checkpoint('verifying_native_stresses',faces_processed=i,wall_faces=len(mesh))
  if not 0<=owner<len(pressures) or not math.isfinite(pressures[owner]):raise ValueError('Native pressure owner outside source field')
  fp=scale(sf,rho*pressures[owner]);xx,xy,xz,yy,yz,zz=t;fv=scale([sf[0]*xx+sf[1]*xy+sf[2]*xz,sf[0]*xy+sf[1]*yy+sf[2]*yz,sf[0]*xz+sf[1]*yz+sf[2]*zz],rho)
  pressure.append(fp);viscous.append(fv);mp.append(cross(c,fp));mv.append(cross(c,fv));areas.append(sf);moment_areas.append(cross(c,sf));trace=max(trace,abs(xx+yy+zz)/max(norm(t),1e-30))
  if i%max(1,len(mesh)//300)==0:samples.append({'face_index':face,'position_m':c,'pressure_force_N':fp,'viscous_force_N':fv,'deviatoric_stress_m2_s2':t})
 total=lambda v:[math.fsum(row[k] for row in v) for k in range(3)]
 p,v,pm,vm=map(total,(pressure,viscous,mp,mv));f=add(p,v);m=add(pm,vm);fs=max(norm(f),norm(p),norm(v),normalization);ms=max(norm(m),norm(pm),norm(vm),fs*.06)
 force_error=max(norm(sub(p,native_force['pressure'])),norm(sub(v,native_force['viscous'])),norm(sub(f,native_force['total'])));moment_error=max(norm(sub(pm,native_moment['pressure'])),norm(sub(vm,native_moment['viscous'])),norm(sub(m,native_moment['total'])))
 checks={'native_force_replay':force_error/fs<1e-9,'native_moment_replay':moment_error/ms<1e-9,'deviatoric_stress_trace':trace<1e-9,'finite_loads':all(math.isfinite(x) for x in f+m)}
 if not all(checks.values()):raise ValueError('Native force replay/stress checks failed: '+json.dumps(checks))
 return {'method':VERSION,'pressure_force_N':native_force['pressure'],'viscous_force_N':native_force['viscous'],'total_force_N':native_force['total'],'pressure_moment_N_m':native_moment['pressure'],'viscous_moment_N_m':native_moment['viscous'],'total_moment_N_m':native_moment['total'],'coefficients':scale(native_force['total'],1/normalization),'force_normalization_N':normalization,'coefficient_reference_area_m2':.0012,'moment_origin_m':[0,0,0],'wall_faces':len(mesh),'independent_force_replay_error_N':force_error,'independent_moment_replay_error_N_m':moment_error,'maximum_relative_stress_trace':trace,'uniform_pressure_offset_1Pa_force_N':total(areas),'uniform_pressure_offset_1Pa_moment_N_m':total(moment_areas),'checks':checks,'wall_samples':samples}

def source_members(data,time=1500):
 if len(data)>48*1024*1024:raise ValueError('Native source archive exceeds limit')
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  names=z.namelist()
  if len(names)!=len(set(names)) or len(names)>200 or sum(i.file_size for i in z.infolist())>256*1024*1024 or any(n.startswith('/') or '..' in n.split('/') for n in names):raise ValueError('Unsafe native source archive')
  required=[str(time)+'/U',str(time)+'/p',str(time)+'/phi']+['constant/polyMesh/'+n for n in ('points','faces','owner','neighbour','boundary')]+['constant/transportProperties','constant/turbulenceProperties','system/controlDict','system/fvSchemes','system/fvSolution','runtime.json']
  members={n:z.read(n) for n in required}
  # OpenFOAM supports executable dictionary directives. Saved numeric ASCII
  # fields/meshes need none; never execute archive-supplied code or includes.
  for name,value in members.items():
   if name!='runtime.json' and (b'#' in value or b'\x00' in value or not value.isascii() or re.search(rb'\b(?:coded\w*|codeStream|dynamicCode|systemCall)\b',value)):
    raise ValueError('Native source must contain plain numeric ASCII without executable directives')
  return members

def execute_source(data,raw,mesh_name,domain_name,bore_level,profile):
 from kcee.bracket_flow import make_case
 time=3000 if profile=='wall-bore-history-v1' else 1500
 members=source_members(data,time)
 with tempfile.TemporaryDirectory(prefix='kcee-native-force-') as tmp:
  root=Path(tmp);make_case(root,raw,mesh_name,domain_name,bore_level,profile)
  for n in ('constant/transportProperties','constant/turbulenceProperties','system/controlDict','system/fvSchemes','system/fvSolution'):
   if (root/n).read_bytes()!=members[n]:raise ValueError('Native source case recipe differs')
  for n,v in members.items():p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v)
  files=execute_case(root,time,'bracket',1.);return pack(files)

def verify_source(evidence,data,flow):
 from kcee.bracket_flow import make_case
 time=3000 if flow['inputs'].get('local_refinement_profile')=='wall-bore-history-v1' else 1500
 files=unpack(evidence);members=source_members(data,time)
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp)
  for n,v in members.items():p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v)
  if files['controlDict']!=__import__('kcee.force_history',fromlist=['postprocess_control']).postprocess_control(members['system/controlDict'])+functions('bracket',flow['inputs']['density_kg_m3']).encode():raise ValueError('Native postprocess recipe differs')
  meta=validate_runtime(json.loads(files['runtime.json']))
  if meta['simpleFoam_sha256']!=json.loads(members['runtime.json'])['binaries_sha256']['simpleFoam']:raise ValueError('Native postprocessing solver differs from source solver')
  mesh=mesh_patch(root/'constant/polyMesh','bracket');pressures=field_values(root/str(time)/'p')
  return integrate(files,mesh,pressures,flow['inputs']['density_kg_m3'],.5*flow['inputs']['density_kg_m3']*flow['inputs']['inlet_velocity_m_s']**2*.0012,time)
