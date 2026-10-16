"""Fixed periodic 2D Taylor–Green verification using packaged OpenFOAM icoFoam."""
import math,re,json,subprocess,tempfile,zipfile,io,base64,hashlib,shutil
from pathlib import Path
INPUTS={'length_m':2*math.pi,'amplitude_m_s':1.,'kinematic_viscosity_m2_s':.1,'end_time_s':.5,'time_step_s':.005,'density_kg_m3':1.}
REFERENCE='https://gitlab.com/openfoam/community/verification-and-validation/-/tree/main/cases/Taylor-Green-vortex'
LIMITS=['Fixed two-dimensional periodic analytical reference; not arbitrary geometry or bracket flow.','Incompressible laminar Newtonian flow; no turbulence, thermal coupling or physical validation.','OpenFOAM p is kinematic pressure (m²/s²), not pressure in Pa. Each displayed pressure field has its spatial mean removed.','Only spatial refinement is compared here. Time-step convergence and engineering acceptance remain pending.']
def exact(x,y,t):
 a=math.exp(-.2*t);return math.sin(x)*math.cos(y)*a,-math.cos(x)*math.sin(y)*a,.25*(math.cos(2*x)+math.cos(2*y))*a*a

def header(name,kind='dictionary'):
 return 'FoamFile { version 2.0; format ascii; class '+kind+'; object '+name+'; }\n'
def make_case(root,n):
 if n not in (16,32,64):raise ValueError('Unsupported reference grid')
 root=Path(root)
 def write(name,text):
  path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
 L=2*math.pi
 write('system/blockMeshDict',header('blockMeshDict')+f'''convertToMeters 1;
vertices ((0 0 0) ({L} 0 0) ({L} {L} 0) (0 {L} 0) (0 0 0.1) ({L} 0 0.1) ({L} {L} 0.1) (0 {L} 0.1));
blocks (hex (0 1 2 3 4 5 6 7) ({n} {n} 1) simpleGrading (1 1 1));
edges ();
boundary (
left {{ type cyclic; neighbourPatch right; faces ((0 4 7 3)); }}
right {{ type cyclic; neighbourPatch left; faces ((1 2 6 5)); }}
bottom {{ type cyclic; neighbourPatch top; faces ((0 1 5 4)); }}
top {{ type cyclic; neighbourPatch bottom; faces ((3 7 6 2)); }}
frontAndBack {{ type empty; faces ((0 3 2 1) (4 5 6 7)); }}
);
mergePatchPairs ();
''')
 write('system/controlDict',header('controlDict')+'''application icoFoam; startFrom startTime; startTime 0; stopAt endTime; endTime 0.5; deltaT 0.005; writeControl timeStep; writeInterval 100; purgeWrite 0; writeFormat ascii; writePrecision 14; writeCompression off; timeFormat general; timePrecision 8; runTimeModifiable false;
''')
 write('system/fvSchemes',header('fvSchemes')+'''ddtSchemes { default backward; }
gradSchemes { default Gauss linear; }
divSchemes { default none; div(phi,U) Gauss linear; }
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
fluxRequired { default no; p; }
''')
 write('system/fvSolution',header('fvSolution')+'''solvers {
p { solver PCG; preconditioner DIC; tolerance 1e-10; relTol 0; }
pFinal { $p; relTol 0; }
U { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-10; relTol 0; }
}
PISO { nCorrectors 3; nNonOrthogonalCorrectors 0; pRefCell 0; pRefValue 0; }
''')
 write('constant/transportProperties',header('transportProperties')+'nu [0 2 -1 0 0 0 0] 0.1;\n')
 rows=[exact((i+.5)*L/n,(j+.5)*L/n,0) for j in range(n) for i in range(n)]
 boundary='boundaryField { left {type cyclic;} right {type cyclic;} bottom {type cyclic;} top {type cyclic;} frontAndBack {type empty;} }\n'
 write('0/U',header('U','volVectorField')+'dimensions [0 1 -1 0 0 0 0];\ninternalField nonuniform List<vector>\n'+str(n*n)+'\n(\n'+'\n'.join(f'({u:.16g} {v:.16g} 0)' for u,v,p in rows)+'\n);\n'+boundary)
 write('0/p',header('p','volScalarField')+'dimensions [0 2 -2 0 0 0 0];\ninternalField nonuniform List<scalar>\n'+str(n*n)+'\n(\n'+'\n'.join(f'{p:.16g}' for u,v,p in rows)+'\n);\n'+boundary)

def field_values(path,vector=False):
 text=Path(path).read_text();match=re.search(r'internalField\s+nonuniform\s+List<\w+>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
 if not match:raise ValueError('Missing nonuniform field')
 count=int(match[1]);raw=match[2]
 values=[tuple(map(float,r.split())) for r in re.findall(r'\(([^()]*)\)',raw)] if vector else list(map(float,raw.split()))
 if len(values)!=count or (vector and any(len(r)!=3 for r in values)):raise ValueError('Invalid field count')
 if not all(math.isfinite(v) for row in values for v in (row if vector else [row])):raise ValueError('Nonfinite solver field')
 return values

def metrics(n,velocities,pressures):
 if len(velocities)!=n*n or len(pressures)!=n*n:raise ValueError('Field size mismatch')
 pmean=sum(pressures)/len(pressures);h=2*math.pi/n;rows=[]
 for index,((u,v,w),p) in enumerate(zip(velocities,pressures)):
  i=index%n;j=index//n;x=(i+.5)*h;y=(j+.5)*h;ue,ve,pe=exact(x,y,.5)
  if not all(math.isfinite(a) for a in (u,v,w,p)):raise ValueError('Nonfinite field')
  rows.append({'x_m':x,'y_m':y,'u_m_s':u,'v_m_s':v,'p_kinematic_m2_s2':p-pmean,'exact_u_m_s':ue,'exact_v_m_s':ve,'exact_p_kinematic_m2_s2':pe})
 ue=sum((r['u_m_s']-r['exact_u_m_s'])**2+(r['v_m_s']-r['exact_v_m_s'])**2 for r in rows);un=sum(r['exact_u_m_s']**2+r['exact_v_m_s']**2 for r in rows)
 pe=sum((r['p_kinematic_m2_s2']-r['exact_p_kinematic_m2_s2'])**2 for r in rows);pn=sum(r['exact_p_kinematic_m2_s2']**2 for r in rows)
 # Cell-centred central-difference diagnostic, distinct from OpenFOAM face-flux continuity.
 div=[]
 for j in range(n):
  for i in range(n):
   div.append((velocities[j*n+(i+1)%n][0]-velocities[j*n+(i-1)%n][0]+velocities[((j+1)%n)*n+i][1]-velocities[((j-1)%n)*n+i][1])/(2*h))
 energy=sum(u*u+v*v+w*w for u,v,w in velocities)/(2*n*n);exact_energy=.25*math.exp(-.4*.5)
 return {'cells_per_axis':n,'cells':n*n,'cell_size_m':h,'time_s':.5,'relative_velocity_l2_error':math.sqrt(ue/un),'relative_pressure_l2_error':math.sqrt(pe/pn),'kinetic_energy_m2_s2':energy,'analytical_kinetic_energy_m2_s2':exact_energy,'relative_energy_error':abs(energy-exact_energy)/exact_energy,'maximum_cell_central_divergence_s_inv':max(map(abs,div)),'field':rows}

def summarize(meshes):
 fine=meshes[-1];checks={'velocity_accuracy':fine['relative_velocity_l2_error']<.02,'pressure_accuracy':fine['relative_pressure_l2_error']<.05,'energy_accuracy':fine['relative_energy_error']<.04,'velocity_refinement':all(b['relative_velocity_l2_error']<a['relative_velocity_l2_error'] for a,b in zip(meshes,meshes[1:])),'pressure_refinement':all(b['relative_pressure_l2_error']<a['relative_pressure_l2_error'] for a,b in zip(meshes,meshes[1:])),'face_flux_continuity':all(m['maximum_local_continuity_error']<1e-7 for m in meshes),'mesh_quality':all(m['mesh_check_passed'] for m in meshes)}
 return {'kind':'cfd_vortex','validation_status':'cfd_vortex_numerical_checks_passed_not_engineering_validated' if all(checks.values()) else 'cfd_vortex_numerical_checks_failed','backend':'OpenFOAM 1912 · icoFoam · PISO pressure-velocity coupling','inputs':INPUTS,'method':'blockMesh uniform hexahedra, periodic x/y, empty z; backward time, central spatial schemes; three PISO correctors','analytical_solution':'u=sin(x)cos(y)exp(-2νt); v=-cos(x)sin(y)exp(-2νt); p/rho=(cos(2x)+cos(2y))exp(-4νt)/4 + C','mesh_study':meshes,'checks':checks,'tolerances':{'relative_velocity_l2_error':.02,'relative_pressure_l2_error':.05,'relative_energy_error':.04,'maximum_local_continuity_error':1e-7},'limits':LIMITS,'reference':REFERENCE}

def execute():
 with tempfile.TemporaryDirectory(prefix='kcee-vortex-') as tmp:
  root=Path(tmp);meshes=[]
  runtime={'package':subprocess.check_output(['dpkg-query','-W','-f=${Version}', 'openfoam'],text=True).strip(),'architecture':subprocess.check_output(['dpkg','--print-architecture'],text=True).strip(),'binaries_sha256':{name:hashlib.sha256(Path(shutil.which(name)).read_bytes()).hexdigest() for name in ('blockMesh','checkMesh','icoFoam')}}
  (root/'runtime.json').write_text(json.dumps(runtime,indent=2))
  for n in (16,32,64):
   case=root/str(n);make_case(case,n)
   for command in ('blockMesh','checkMesh','icoFoam'):
    with (case/(command+'.log')).open('w') as log:subprocess.run([command,'-case',str(case)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
   mesh_ok='Mesh OK.' in (case/'checkMesh.log').read_text()
   log=(case/'icoFoam.log').read_text();continuity=[float(x) for x in re.findall(r'time step continuity errors : sum local = ([^,\s]+)',log)]
   if len(continuity)<100 or 'End' not in log:raise ValueError('Incomplete solver run')
   row=metrics(n,field_values(case/'0.5/U',True),field_values(case/'0.5/p'));row.update(mesh_check_passed=mesh_ok,maximum_local_continuity_error=max(continuity));meshes.append(row)
  result=summarize(meshes);buffer=io.BytesIO()
  with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
   for path in sorted(root.rglob('*')):
    if path.is_file():archive.write(path,path.relative_to(root).as_posix())
  raw=buffer.getvalue()
  return {'result':result,'archive_base64':base64.b64encode(raw).decode(),'archive_sha256':hashlib.sha256(raw).hexdigest()}
