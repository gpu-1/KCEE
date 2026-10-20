"""Piecewise-constant wall pressure and full native viscous traction for display."""
import hashlib,json,math,tempfile,zipfile
from pathlib import Path
from kcee.regional_wall import surface
from kcee.native_forces import source_members,unpack,boundary_values,mesh_patch
from kcee.flow_forces import scale,cross,add,sub,norm
from kcee.openfoam_vortex import field_values
VERSION='native-wall-fields-v1'
def face_fields(mesh,centres,stress,pressures,rho,expected,normalization):
 if not 0<len(mesh)<=100000 or len(mesh)!=len(centres) or len(mesh)!=len(stress) or not math.isfinite(rho) or rho<=0:raise ValueError('Invalid wall field sizes or density')
 rows=[];seen=set()
 for (face,owner,sf),c,t in zip(mesh,centres,stress):
  if face in seen or not 0<=owner<len(pressures) or len(sf)!=3 or len(c)!=3 or len(t)!=6 or not all(math.isfinite(v) for v in [*sf,*c,*t,pressures[owner]]):raise ValueError('Invalid wall field data')
  seen.add(face);area=norm(sf)
  if not area>0:raise ValueError('Zero-area native wall face')
  pressure=rho*pressures[owner];xx,xy,xz,yy,yz,zz=t;fp=scale(sf,pressure);fv=scale([sf[0]*xx+sf[1]*xy+sf[2]*xz,sf[0]*xy+sf[1]*yy+sf[2]*yz,sf[0]*xz+sf[1]*yz+sf[2]*zz],rho)
  rows.append({'face':face,'centre_m':c,'area_m2':area,'area_vector_m2':sf,'pressure_Pa':pressure,'pressure_force_N':fp,'viscous_force_N':fv,'total_force_N':add(fp,fv),'viscous_traction_Pa':scale(fv,1/area),'total_traction_Pa':scale(add(fp,fv),1/area)})
 keys=('pressure_force_N','viscous_force_N','total_force_N','pressure_moment_N_m','viscous_moment_N_m','total_moment_N_m');totals={}
 for k in keys:
  values=[cross(row['centre_m'],row[k.replace('_moment_N_m','_force_N')]) if 'moment' in k else row[k] for row in rows];totals[k]=[math.fsum(v[i] for v in values) for i in range(3)]
 errors={k:norm(sub(totals[k],expected[k]))/max(norm(expected[k]),normalization*(.06 if 'moment' in k else 1)) for k in keys}
 if not all(math.isfinite(e) and e<1e-9 for e in errors.values()):raise ValueError('Displayed face forces do not reproduce native regional totals')
 return {'method':VERSION,'units':'Pa','faces':rows,'integrated_loads':totals,'relative_closure_errors':errors,'checks':{'all_six_load_groups_close':True,'unique_native_faces':len(seen)==len(mesh)},'limits':'Piecewise constant values on native parent wall faces; no smoothing or nodal stress recovery. Pressure is rho times saved owner-cell kinematic pressure relative to the outlet reference. Viscous traction includes full laminar deviatoric normal and shear terms. Forces act fluid on solid; moments use native face centres about (0,0,0) m. Field colors are case-specific and do not establish accuracy or convergence.'}

def fields(root,identifier,source_id,registry):
 d=surface(root,identifier,source_id,registry);root=Path(root);p=root/str(source_id);flow=json.loads((p/'cfd.json').read_text());time=3000 if 'force_history' in flow else 1500;members=source_members((p/'cfd-artifacts.zip').read_bytes(),time)
 with zipfile.ZipFile(root/str(identifier)/'native-forces.zip') as z:files=unpack(z.read(str(source_id)+'.zip'))
 with tempfile.TemporaryDirectory() as tmp:
  path=Path(tmp)
  for n,v in members.items():q=path/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(v)
  mesh=mesh_patch(path/'constant/polyMesh','bracket');centres=boundary_values(files['wall-centres.foam'],len(mesh),3);stress=boundary_values(files['wall-stress.foam'],len(mesh),6)
  expected={k:[math.fsum(r['loads'][k][i] for r in d['source']['regions']) for i in range(3)] for k in d['source']['regions'][0]['loads']};rho=flow['inputs']['density_kg_m3'];normalization=.5*rho*flow['inputs']['inlet_velocity_m_s']**2*.0012
  values=face_fields(mesh,centres,stress,field_values(path/str(time)/'p'),rho,expected,normalization)
 if set(d['surface']['triangle_source_faces'])!={r['face'] for r in values['faces']}:raise ValueError('Display faces differ from wall field identities')
 return {**d,'schema':VERSION,'geometry_schema':d['schema'],'wall_fields':values,'field_implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'checks':{**d['checks'],**values['checks']}}
