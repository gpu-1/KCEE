"""Reproducible pressure force and one-sided tangential wall-shear estimate.

Sf points out of the fluid (into the solid). Force is fluid on solid:
Fp = rho*p_kinematic*Sf; Fv = mu*A*U_owner,t / d_normal.
This is a separate discrete estimate, not OpenFOAM's forces function object.
"""
import hashlib,io,json,math,re,tempfile,zipfile
from pathlib import Path
from kcee.cfd_control import checkpoint
VERSION='wall-face-traction-v1'
LIMITS=[
 'Pressure uses the saved zeroGradient wall condition: boundary pressure equals owner-cell kinematic pressure, multiplied by density. Loads act from fluid on solid; +x is the inlet direction.',
 'Viscous load is a one-sided tangential wall-shear estimate mu*A*U_owner,t/d_normal. It is not the native OpenFOAM stress-tensor integration; normal viscous traction and nonorthogonal gradient corrections are omitted.',
 'No prism layers are present. Wall shear, force and moment convergence are unestablished; a passing analytical integration benchmark does not validate the CFD wall gradient.',
 'Face area vectors and centroids use vertex-mean triangle fans of the saved polyMesh. Warped-face geometry may differ from native OpenFOAM geometry.',
 'Moments are about the source coordinate origin (0,0,0) m. Density is 1 kg/m³ and dynamic viscosity is 0.0001 Pa·s for these illustrative Re=6 cases.',
 'The reference coefficient area is a declared 0.03×0.04 m² envelope area, not measured projected mesh area. Coefficients use 0.5*rho*U²*Aref; no aerodynamic acceptance threshold is applied.',
 'Fine far/outer domains change background spacing and alignment slightly. Their comparison includes grid changes; differences are not error bounds or proof of mesh/domain independence.',
 'This workflow does not transfer loads into structural analysis or establish engineering acceptance.'
]

def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def add(a,b):return [x+y for x,y in zip(a,b)]
def scale(a,s):return [x*s for x in a]
def norm(a):return math.sqrt(dot(a,a))

def face_geometry(vertices):
 if len(vertices)<3 or not all(math.isfinite(v) for p in vertices for v in p):raise ValueError('Invalid wall vertices')
 mean=[sum(p[k] for p in vertices)/len(vertices) for k in range(3)]
 triangles=[scale(cross(sub(a,mean),sub(b,mean)),.5) for a,b in zip(vertices,vertices[1:]+vertices[:1])]
 area_vector=[math.fsum(t[k] for t in triangles) for k in range(3)];area=norm(area_vector)
 if area<=1e-18:raise ValueError('Degenerate wall face')
 n=scale(area_vector,1/area);weights=[dot(t,n) for t in triangles]
 center=[math.fsum(w*(mean[k]+a[k]+b[k])/3 for w,a,b in zip(weights,vertices,vertices[1:]+vertices[:1]))/area for k in range(3)]
 moment_area=[math.fsum(cross([(mean[j]+a[j]+b[j])/3 for j in range(3)],t)[k] for a,b,t in zip(vertices,vertices[1:]+vertices[:1],triangles)) for k in range(3)]
 return area_vector,center,moment_area

def face_load(sf,center,owner_center,velocity,p,rho,nu):
 if not all(math.isfinite(v) for v in [*sf,*center,*owner_center,*velocity,p,rho,nu]) or rho<=0 or nu<=0:raise ValueError('Invalid traction inputs')
 area=norm(sf)
 if area<=1e-18:raise ValueError('Zero wall area')
 n=scale(sf,1/area);distance=dot(sub(center,owner_center),n)
 if distance<=1e-12:raise ValueError('Nonpositive owner-to-wall normal distance')
 tangent=sub(velocity,scale(n,dot(velocity,n)));fp=scale(sf,rho*p);fv=scale(tangent,rho*nu*area/distance)
 return {'pressure_N':fp,'viscous_estimate_N':fv,'pressure_moment_N_m':cross(center,fp),'viscous_estimate_moment_N_m':cross(center,fv),'normal_distance_m':distance,'nonorthogonality_degrees':math.degrees(math.acos(max(-1,min(1,distance/norm(sub(center,owner_center))))))}

def benchmark():
 """Closed box affine pressure + plane Poiseuille wall shear at three spacings."""
 # Unit cube: p/rho = 7 + 2x - 3y + 4z; fluid-domain normals point inward.
 vertices=[([1,0,0],[[0,0,0],[0,1,0],[0,1,1],[0,0,1]]),([-1,0,0],[[1,0,0],[1,0,1],[1,1,1],[1,1,0]]),([0,1,0],[[0,0,0],[0,0,1],[1,0,1],[1,0,0]]),([0,-1,0],[[0,1,0],[1,1,0],[1,1,1],[0,1,1]]),([0,0,1],[[0,0,0],[1,0,0],[1,1,0],[0,1,0]]),([0,0,-1],[[0,0,1],[0,1,1],[1,1,1],[1,0,1]])]
 forces=[];moments=[];gauges=[]
 for expected,points in vertices:
  sf,c,ma=face_geometry(points)
  if sf!=expected:raise ValueError('Benchmark normal convention failed')
  p=7+2*c[0]-3*c[1]+4*c[2];owner=add(c,scale(sf,-.25));r=face_load(sf,c,owner,[0,0,0],p,2,.01);forces.append(r['pressure_N']);moments.append(scale(ma,2*p));gauges.append(scale(sf,200))
 total=lambda rows:[math.fsum(v[k] for v in rows) for k in range(3)]
 exact=[-4,6,-8];moment=[-7,2,5];actual=total(forces);actual_moment=total(moments)
 # Plane Poiseuille u(y)=G*y*(H-y)/(2*mu); bottom-wall F=G*H*A/2.
 G=2.;H=.02;mu=.004;area=.03*.04;exact_shear=G*H*area/2;rows=[]
 for cells in (8,16,32):
  d=H/(2*cells);u=G*d*(H-d)/(2*mu);r=face_load([0,-area,0],[.015,0,.02],[.015,d,.02],[u,0,0],0,2,mu/2);value=r['viscous_estimate_N'][0]
  rows.append({'cells':cells,'distance_m':d,'force_N':value,'exact_force_N':exact_shear,'relative_error':abs(value-exact_shear)/exact_shear})
 orders=[math.log(a['relative_error']/b['relative_error'],2) for a,b in zip(rows,rows[1:])]
 checks={'affine_pressure_force':math.dist(actual,exact)<1e-12,'affine_pressure_moment':math.dist(actual_moment,moment)<1e-12,'uniform_pressure_offset_force':norm(total(gauges))<1e-12,'wall_shear_first_order':all(abs(v-1)<1e-10 for v in orders),'positive_drag_sign':all(r['force_N']>0 for r in rows)}
 if not all(checks.values()):raise ValueError('Force integration benchmark failed')
 return {'method':'Manufactured closed-box affine pressure and analytical plane-Poiseuille wall-gradient refinement; no new CFD solve','pressure_force_N':actual,'exact_pressure_force_N':exact,'pressure_moment_N_m':actual_moment,'exact_pressure_moment_N_m':moment,'wall_shear_study':rows,'observed_orders':orders,'checks':checks,'limits':'Tests integration, units, signs, origin moments and first-order wall derivative on orthogonal analytic fields. It does not verify native OpenFOAM stresses or establish bracket accuracy.'}

def from_archive(data,flow):
 from kcee.bracket_flow import mesh_list
 if len(data)>48*1024*1024:raise ValueError('Force source archive exceeds limit')
 fields=flow['field'];rho=flow['inputs']['density_kg_m3'];nu=flow['inputs']['kinematic_viscosity_m2_s'];count=len(fields)
 if not 1000<=count<=350000:raise ValueError('Invalid force field count')
 with zipfile.ZipFile(io.BytesIO(data)) as z,tempfile.TemporaryDirectory() as tmp:
  infos=z.infolist();names=z.namelist()
  if len(names)!=len(set(names)) or len(names)>200 or sum(i.file_size for i in infos)>256*1024*1024 or any(n.startswith('/') or '..' in n.split('/') for n in names):raise ValueError('Unsafe force source archive')
  root=Path(tmp)
  for name in ('points','faces','owner','neighbour','boundary'):
   (root/name).write_bytes(z.read('constant/polyMesh/'+name))
  n,raw=mesh_list(root/'points');points=[list(map(float,v.split())) for v in re.findall(r'\(([^()]*)\)',raw)]
  nf,raw=mesh_list(root/'faces');faces=[list(map(int,v.split())) for v in re.findall(r'\d+\(([^()]*)\)',raw)]
  no,raw=mesh_list(root/'owner');owners=list(map(int,raw.split()));ni,_=mesh_list(root/'neighbour')
  m=re.search(r'\bbracket\s*\{([^{}]*)\}',(root/'boundary').read_text(),re.S)
  if not m:raise ValueError('Missing bracket patch')
  start=int(re.search(r'startFace\s+(\d+)',m[1])[1]);size=int(re.search(r'nFaces\s+(\d+)',m[1])[1])
  if len(points)!=n or len(faces)!=nf or len(owners)!=nf or no!=nf or start<ni or not 1<=size<=nf-start:raise ValueError('Invalid force mesh addressing')
  time='3000' if flow['inputs'].get('local_refinement_profile')=='wall-bore-history-v1' else '1500'
  ptext=z.read(time+'/p').decode();utext=z.read(time+'/U').decode()
  ppatch=re.search(r'\bbracket\s*\{([^{}]*)\}',ptext,re.S);upatch=re.search(r'\bbracket\s*\{([^{}]*)\}',utext,re.S)
  if not ppatch or not re.search(r'type\s+zeroGradient\s*;',ppatch[1]) or not upatch or not re.search(r'type\s+fixedValue\s*;',upatch[1]) or not re.search(r'value\s+uniform\s+\(0\s+0\s+0\)\s*;',upatch[1]):raise ValueError('Unsupported wall boundary conditions')
  if not re.search(r'dimensions\s*\[0 2 -2 0 0 0 0\]',ptext):raise ValueError('Pressure is not kinematic SI')
  loads=[];area_vectors=[];areas=[];moment_areas=[];distances=[];angles=[];sample=[]
  for offset,face in enumerate(faces[start:start+size]):
   if offset%1000==0:checkpoint('integrating_wall_faces',faces_processed=offset,wall_faces=size)
   index=start+offset;owner=owners[index]
   if not 0<=owner<count or any(not 0<=v<n for v in face):raise ValueError('Force face addressing outside field')
   sf,c,ma=face_geometry([points[v] for v in face]);f=fields[owner];position=[f[k] for k in ('x_m','y_m','z_m')];u=[f[k] for k in ('u_m_s','v_m_s','w_m_s')]
   load=face_load(sf,c,position,u,f['p_kinematic_m2_s2'],rho,nu);load['pressure_moment_N_m']=scale(ma,rho*f['p_kinematic_m2_s2']);loads.append(load);areas.append(norm(sf));area_vectors.append(sf);moment_areas.append(ma);distances.append(load['normal_distance_m']);angles.append(load['nonorthogonality_degrees'])
   if offset%max(1,size//400)==0:sample.append({'face_index':index,'position_m':c,'pressure_force_N':load['pressure_N'],'viscous_estimate_force_N':load['viscous_estimate_N'],'normal_distance_m':load['normal_distance_m']})
  total=lambda key:[math.fsum(f[key][k] for f in loads) for k in range(3)]
  closure=[math.fsum(v[k] for v in area_vectors) for k in range(3)];moment_closure=[math.fsum(v[k] for v in moment_areas) for k in range(3)];area=math.fsum(areas)
  fp=total('pressure_N');fv=total('viscous_estimate_N');mp=total('pressure_moment_N_m');mv=total('viscous_estimate_moment_N_m');force=add(fp,fv);moment=add(mp,mv);normalizer=.5*rho*flow['inputs']['inlet_velocity_m_s']**2*.0012
  return {'method':VERSION,'wall_faces':size,'wall_area_m2':area,'pressure_force_N':fp,'viscous_estimate_force_N':fv,'total_estimate_force_N':force,'pressure_moment_N_m':mp,'viscous_estimate_moment_N_m':mv,'total_estimate_moment_N_m':moment,'force_coefficients_estimate':scale(force,1/normalizer),'coefficient_reference_area_m2':.0012,'force_normalization_N':normalizer,'moment_origin_m':[0,0,0],'area_vector_closure_m2':closure,'relative_area_vector_closure':norm(closure)/area,'moment_area_closure_m3':moment_closure,'uniform_pressure_offset_1Pa_force_N':closure,'uniform_pressure_offset_1Pa_moment_N_m':moment_closure,'minimum_normal_distance_m':min(distances),'maximum_wall_nonorthogonality_degrees':max(angles),'wall_face_samples':sample,'checks':{'closed_wall_force_gauge':norm(closure)/area<1e-9,'closed_wall_moment_gauge':norm(moment_closure)/(area*.06)<1e-9,'finite_loads':all(math.isfinite(v) for v in force+moment),'positive_owner_distances':min(distances)>1e-12}}
