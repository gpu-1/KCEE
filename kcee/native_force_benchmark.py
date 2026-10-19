"""Native constitutive/integration benchmark on prescribed analytic SI fields.

No flow PDE is solved. U=(a*x+g*y,-a*y,0) is divergence free and has constant
full deviatoric stress, including nonzero normal traction at y=0.
"""
import hashlib,json,math,tempfile
from pathlib import Path
from kcee.openfoam_vortex import header
from kcee.native_forces import execute_case,pack,unpack,mesh_patch,integrate,FILES,VERSION
from kcee.flow_forces import norm,sub
from kcee.cfd_control import checkpoint
SIZES=(8,16,32)
EXTRAS={'points','faces','owner','neighbour','boundary','U','p','blockMeshDict','fvSchemes','fvSolution','transportProperties','turbulenceProperties','blockMesh.log'}
L=.06;H=.02;W=.03;RHO=2.;NU=.002;GAMMA=3.;A=.4;P0=.7;GX=.3;GZ=-.2

def dictionaries(n):
 if n not in SIZES:raise ValueError('Unsupported native benchmark mesh')
 return {
 'system/blockMeshDict':header('blockMeshDict')+f'''scale 1; vertices ((0 0 0) ({L} 0 0) ({L} {H} 0) (0 {H} 0) (0 0 {W}) ({L} 0 {W}) ({L} {H} {W}) (0 {H} {W}));
blocks (hex (0 1 2 3 4 5 6 7) ({n} {n//2} {n//2}) simpleGrading (1 1 1)); edges ();
boundary (bottom {{type wall;faces ((0 1 5 4));}} top {{type wall;faces ((3 7 6 2));}} ends {{type wall;faces ((0 4 7 3)(1 2 6 5));}} sides {{type wall;faces ((0 3 2 1)(4 5 6 7));}}); mergePatchPairs ();
''',
 'system/controlDict':header('controlDict')+'application simpleFoam;startFrom startTime;startTime 0;stopAt endTime;endTime 0;deltaT 1;writeControl timeStep;writeInterval 1;writeFormat ascii;writePrecision 14;runTimeModifiable false;\n',
 'system/fvSchemes':header('fvSchemes')+'ddtSchemes {default steadyState;} gradSchemes {default Gauss linear;} divSchemes {default none;div(phi,U) bounded Gauss upwind;div((nuEff*dev2(T(grad(U))))) Gauss linear;} laplacianSchemes {default Gauss linear corrected;} interpolationSchemes {default linear;} snGradSchemes {default corrected;} fluxRequired {default no;p;}\n',
 'system/fvSolution':header('fvSolution')+'solvers {p {solver PCG;preconditioner DIC;tolerance 1e-12;relTol 0;} U {solver smoothSolver;smoother symGaussSeidel;tolerance 1e-12;relTol 0;}} SIMPLE {nNonOrthogonalCorrectors 0;}\n',
 'constant/transportProperties':header('transportProperties')+'transportModel Newtonian;nu [0 2 -1 0 0 0 0] .002;\n',
 'constant/turbulenceProperties':header('turbulenceProperties')+'simulationType laminar;\n'}

def fields(root,n):
 from kcee.bracket_flow import cell_positions
 from kcee.native_forces import mesh_patch
 from kcee.flow_forces import face_geometry
 from kcee.bracket_flow import mesh_list
 import re
 root=Path(root);mesh=root/'constant/polyMesh';centres=cell_positions(mesh,n*(n//2)**2)
 np,raw=mesh_list(mesh/'points');points=[list(map(float,v.split())) for v in re.findall(r'\(([^()]*)\)',raw)]
 nf,raw=mesh_list(mesh/'faces');faces=[list(map(int,v.split())) for v in re.findall(r'\d+\(([^()]*)\)',raw)]
 def value(p,vector):return [A*p[0]+GAMMA*p[1],-A*p[1],0.] if vector else P0+GX*p[0]+GZ*p[2]
 def values(positions,vector):
  rows=[value(p,vector) for p in positions]
  return 'nonuniform List<'+('vector' if vector else 'scalar')+'>\n'+str(len(rows))+'\n(\n'+'\n'.join('('+' '.join(format(v,'.15g') for v in r)+')' if vector else format(r,'.15g') for r in rows)+'\n)'
 result={}
 for name,vector,dims in [('U',True,'0 1 -1 0 0 0 0'),('p',False,'0 2 -2 0 0 0 0')]:
  text=header(name,'volVectorField' if vector else 'volScalarField')+'dimensions ['+dims+'];\ninternalField '+values(centres,vector)+';\nboundaryField {\n'
  for patch in ('bottom','top','ends','sides'):
   entries=mesh_patch(mesh,patch);positions=[face_geometry([points[v] for v in faces[index]])[1] for index,_,_ in entries]
   text+=patch+' {type fixedValue; value '+values(positions,vector)+';}\n'
  result['0/'+name]=text+'}\n'
 return result

def exact():
 area=L*W;mu=RHO*NU;pressure=[0.,-RHO*area*(P0+GX*L/2+GZ*W/2),0.];visc=[mu*GAMMA*area,-2*mu*A*area,0.]
 pm=[RHO*area*(P0*W/2+GX*L*W/4+GZ*W*W/3),0.,-RHO*area*(P0*L/2+GX*L*L/3+GZ*L*W/4)]
 vm=[-W/2*visc[1],W/2*visc[0],L/2*visc[1]]
 return {'pressure_force_N':pressure,'viscous_force_N':visc,'pressure_moment_N_m':pm,'viscous_moment_N_m':vm}

def execute():
 from kcee.bracket_flow import command
 blobs={}
 for n in SIZES:
  checkpoint('native_force_benchmark',case='Analytic full stress '+str(n))
  with tempfile.TemporaryDirectory(prefix='kcee-native-benchmark-') as tmp:
   root=Path(tmp)
   for name,text in dictionaries(n).items():p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
   command(root,'blockMesh');expected=fields(root,n)
   for name,text in expected.items():p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
   files=execute_case(root,0,'bottom',RHO)
   for name in EXTRAS:
    path=root/('constant/polyMesh/'+name if name in ('points','faces','owner','neighbour','boundary') else '0/'+name if name in ('U','p') else 'system/'+name if name in ('blockMeshDict','fvSchemes','fvSolution') else 'constant/'+name if name.endswith('Properties') else name)
    files[name]=path.read_bytes()
   blobs[str(n)+'.zip']=pack(files)
 return pack(blobs)

def verify(data):
 from kcee.native_forces import functions,validate_runtime
 from kcee.openfoam_vortex import field_values
 blobs=unpack(data,{str(n)+'.zip' for n in SIZES});rows=[];analytical=exact();runtimes=set();runtime_record=None
 for n in SIZES:
  files=unpack(blobs[str(n)+'.zip'],FILES|EXTRAS);runtime_record=validate_runtime(json.loads(files['runtime.json']));runtimes.add(json.dumps(runtime_record,sort_keys=True))
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for name in EXTRAS:
    path=root/('constant/polyMesh/'+name if name in ('points','faces','owner','neighbour','boundary') else '0/'+name if name in ('U','p') else 'system/'+name if name in ('blockMeshDict','fvSchemes','fvSolution') else 'constant/'+name if name.endswith('Properties') else name)
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(files[name])
   for name,text in dictionaries(n).items():
    if name=='system/controlDict':
     if files['controlDict']!=(text+functions('bottom',RHO)).encode():raise ValueError('Native benchmark postprocessing recipe differs')
    elif (root/name).read_bytes()!=text.encode():raise ValueError('Native benchmark dictionary differs')
   for name,text in fields(root,n).items():
    if (root/name).read_bytes()!=text.encode():raise ValueError('Native benchmark analytic fields differ')
   mesh=mesh_patch(root/'constant/polyMesh','bottom');loads=integrate(files,mesh,field_values(root/'0/p'),RHO,1.,0)
   errors={key:norm(sub(loads[key],value))/max(norm(value),1e-30) for key,value in analytical.items()}
   rows.append({'cells_x':n,'cells':n*(n//2)**2,'loads':{k:v for k,v in loads.items() if k not in ('wall_samples','coefficients','force_normalization_N','coefficient_reference_area_m2')},'relative_errors':errors})
 if len(runtimes)!=1:raise ValueError('Native benchmark runtimes differ')
 orders=[math.log(a['relative_errors']['pressure_moment_N_m']/b['relative_errors']['pressure_moment_N_m'],2) for a,b in zip(rows,rows[1:])]
 checks={'pressure_force':all(r['relative_errors']['pressure_force_N']<1e-9 for r in rows),'full_viscous_force_including_normal':all(r['relative_errors']['viscous_force_N']<1e-9 for r in rows),'viscous_moment':all(r['relative_errors']['viscous_moment_N_m']<1e-9 for r in rows),'pressure_moment_second_order':all(abs(v-2)<1e-5 for v in orders),'fine_pressure_moment_error':rows[-1]['relative_errors']['pressure_moment_N_m']<1e-4,'all_native_replays':all(all(r['loads']['checks'].values()) for r in rows)}
 if not all(checks.values()):raise ValueError('Native analytical benchmark failed: '+json.dumps({'checks':checks,'orders':orders,'rows':rows}))
 return {'schema':'kcee.native-force-benchmark.v1','method':VERSION,'description':'Prescribed divergence-free affine velocity U=(0.4*x+3*y,-0.4*y,0) and affine kinematic pressure 0.7+0.3*x-0.2*z; native full Stokes stress and forces on bottom wall','inputs':{'length_m':L,'height_m':H,'width_m':W,'density_kg_m3':RHO,'kinematic_viscosity_m2_s':NU},'exact':analytical,'studies':rows,'pressure_moment_observed_orders':orders,'checks':checks,'runtime':runtime_record,'scope':'Native constitutive stress and force/moment integration on prescribed analytic fields; no flow PDE solved. Not a bracket accuracy or mesh-independence proof.'}
