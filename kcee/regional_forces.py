"""Read-only regional diagnostics of verified native wall-load evidence."""
import csv,hashlib,io,json,math,tempfile,zipfile
from pathlib import Path
from kcee.native_forces import unpack,source_members,mesh_patch,boundary_values
from kcee.flow_forces import scale,cross,add,sub,norm
from kcee.openfoam_vortex import field_values
VERSION='native-regional-loads-v1'
KEYS=('pressure_force_N','viscous_force_N','total_force_N','pressure_moment_N_m','viscous_moment_N_m','total_moment_N_m')
CENTRES=((.033,.015,.00175),(.048,.015,.00175),(.00175,.015,.016),(.00175,.015,.030))
NAMES=('Base bore 1 neighborhood','Base bore 2 neighborhood','Upright bore 1 neighborhood','Upright bore 2 neighborhood','Root neighborhood','Base remainder','Upright remainder')
LIMITS=['Regions classify native face centres, not exact geometric intersections. Bore neighborhoods are 5 mm spheres and include nearby plate faces; they are not isolated bore-wall loads.', 'First matching bore sphere wins; remaining faces with x <= 8 mm and z <= 8 mm form the root neighborhood, then z <= 8 mm the base, then upright remainder. All coordinates are in metres.', 'Pressure uses the saved outlet reference. The recorded area vector gives the load change per +1 Pa uniform pressure offset. Regional pressure loads depend on that reference; this is a sensitivity, not an uncertainty estimate.', 'Every wall face belongs to exactly one region. Summed regional forces and moments must reproduce the verified native loads. Mesh-to-mesh region membership changes with face centres.', 'Saved Re=6 fields are reused. Regional changes do not establish mesh convergence, physical accuracy or structural acceptance. No new PDE solve or automatic load transfer is performed.']
def region(c):
 if len(c)!=3 or not all(math.isfinite(v) for v in c):raise ValueError('Invalid native face centre')
 for i,p in enumerate(CENTRES):
  if sum((x-y)**2 for x,y in zip(c,p))<=.005**2:return i
 return 4 if c[0]<=.008 and c[2]<=.008 else 5 if c[2]<=.008 else 6

def partition(mesh,centres,stress,pressures,rho,expected,normalization):
 if not len(mesh)==len(centres)==len(stress) or not mesh or not math.isfinite(rho) or rho<=0:raise ValueError('Regional field sizes or density differ')
 buckets=[[] for _ in NAMES]
 for (face,owner,sf),c,t in zip(mesh,centres,stress):
  if not 0<=owner<len(pressures) or len(t)!=6 or len(sf)!=3 or not all(math.isfinite(v) for v in [*t,*sf,pressures[owner]]):raise ValueError('Invalid regional wall data')
  fp=scale(sf,rho*pressures[owner]);xx,xy,xz,yy,yz,zz=t;fv=scale([sf[0]*xx+sf[1]*xy+sf[2]*xz,sf[0]*xy+sf[1]*yy+sf[2]*yz,sf[0]*xz+sf[1]*yz+sf[2]*zz],rho)
  buckets[region(c)].append((fp,fv,cross(c,fp),cross(c,fv),sf,cross(c,sf),norm(sf)))
 total=lambda rows,i:[math.fsum(r[i][k] for r in rows) for k in range(3)]
 regions=[]
 for name,rows in zip(NAMES,buckets):
  fp,fv,mp,mv,area,ma=[total(rows,i) for i in range(6)]
  regions.append({'region':name,'faces':len(rows),'area_m2':math.fsum(r[6] for r in rows),'loads':dict(zip(KEYS,(fp,fv,add(fp,fv),mp,mv,add(mp,mv)))),'pressure_offset_1Pa_force_N':area,'pressure_offset_1Pa_moment_N_m':ma})
 errors={k:norm(sub([math.fsum(r['loads'][k][i] for r in regions) for i in range(3)],expected[k]))/max(norm(expected[k]),normalization*(.06 if 'moment' in k else 1)) for k in KEYS}
 if not all(math.isfinite(v) and v<1e-9 for v in errors.values()):raise ValueError('Regional loads do not close to native loads')
 return {'regions':regions,'wall_faces':len(mesh),'relative_closure_errors':errors,'checks':{'all_faces_partitioned':sum(r['faces'] for r in regions)==len(mesh),'all_load_groups_close':True}}

def compare(cases):
 result=[]
 for a,b in zip(cases,cases[1:]):
  result.append({'from_run_id':a['run_id'],'to_run_id':b['run_id'],'label':a['mesh']+' / '+a.get('profile','')+' / '+a.get('domain','')+' → '+b['mesh']+' / '+b.get('profile','')+' / '+b.get('domain',''),'regions':[{'region':x['region'],'signed_changes':{k:sub(y['loads'][k],x['loads'][k]) for k in KEYS},'pressure_offset_1Pa_force_change_N':sub(y['pressure_offset_1Pa_force_N'],x['pressure_offset_1Pa_force_N'])} for x,y in zip(a['regions'],b['regions'])]})
 return result

def audit(root,identifier,registry):
 from kcee.native_forces_run import verify_study
 verify_study(root,identifier,registry)
 root=Path(root);p=root/str(identifier);manifest=json.loads((p/'manifest.json').read_text());saved=json.loads((p/'cfd.json').read_text());cases=[]
 with zipfile.ZipFile(p/'native-forces.zip') as outer:
  for s in saved['studies']:
   source=root/s['run_id'];flow=json.loads((source/'cfd.json').read_text());time=3000 if 'force_history' in s else 1500
   members=source_members((source/'cfd-artifacts.zip').read_bytes(),time);files=unpack(outer.read(s['run_id']+'.zip'))
   with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)
    for n,v in members.items():q=path/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(v)
    mesh=mesh_patch(path/'constant/polyMesh','bracket');centres=boundary_values(files['wall-centres.foam'],len(mesh),3);stress=boundary_values(files['wall-stress.foam'],len(mesh),6)
    result=partition(mesh,centres,stress,field_values(path/str(time)/'p'),flow['inputs']['density_kg_m3'],s['loads'],s['loads']['force_normalization_N'])
   cases.append({'run_id':s['run_id'],'manifest_sha256':s['manifest_sha256'],'archive_sha256':s['archive_sha256'],'native_evidence_sha256':s['native_evidence_sha256'],'mesh':s['mesh_name'],'profile':s['local_profile'],'domain':s['domain_name'],'source_checks':s['source_checks'],'bore_checks_pass':s['bore_checks_pass'],**result})
 return {'schema':VERSION,'report_run_id':str(identifier),'report_manifest_sha256':hashlib.sha256((p/'manifest.json').read_bytes()).hexdigest(),'native_archive_sha256':manifest['artifacts']['native-forces.zip'],'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'regions':list(NAMES),'cases':cases,'comparisons':compare(cases),'checks':{'source_evidence_reproduced':True,'all_regional_closures':all(all(c['checks'].values()) for c in cases)},'limits':LIMITS,'engineering_acceptance':'pending'}

def csv_text(data):
 stream=io.StringIO();w=csv.writer(stream);w.writerow(['method','report_run_id','report_manifest_sha256','source_run_id','source_manifest_sha256','mesh','profile','domain','region','faces','area_m2','axis',*KEYS,'pressure_offset_1Pa_force_N','pressure_offset_1Pa_moment_N_m'])
 for c in data['cases']:
  for r in c['regions']:
   for i,a in enumerate('xyz'):w.writerow([VERSION,data['report_run_id'],data['report_manifest_sha256'],c['run_id'],c['manifest_sha256'],c['mesh'],c['profile'],c['domain'],r['region'],r['faces'],r['area_m2'],a,*[r['loads'][k][i] for k in KEYS],r['pressure_offset_1Pa_force_N'][i],r['pressure_offset_1Pa_moment_N_m'][i]])
 return stream.getvalue()
