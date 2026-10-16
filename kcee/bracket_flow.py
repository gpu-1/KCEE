"""Exploratory external laminar OpenFOAM flow around a bounded native bracket STL."""
import base64,hashlib,io,json,math,re,struct,subprocess,tempfile,zipfile
from pathlib import Path
from kcee.openfoam_vortex import header,field_values
INPUTS={'inlet_velocity_m_s':.01,'kinematic_viscosity_m2_s':.0001,'density_kg_m3':1.,'domain_min_m':[-.12,-.09,-.10],'domain_max_m':[.24,.12,.14],'background_cells':[24,14,16],'surface_refinement_level':3,'maximum_iterations':1000}
LIMITS=['Exploratory steady laminar external flow at Reynolds number 6 based on 60 mm and inlet speed; not realistic service conditions.','Single mesh, no prism layers; thin walls, bores and root details may be under-resolved. No mesh/domain convergence or force acceptance.','Uniform +x inlet, zero kinematic pressure outlet, slip far-field sides and no-slip bracket. No mounting wall, bolts, contact, turbulence or thermal coupling.','OpenFOAM p is kinematic pressure in m²/s² at the outlet reference, not pressure in Pa.','Velocity and pressure are cell fields. Viewer point positions are arithmetic means of each cell’s unique mesh vertices, not interpolated fields or exact volume centroids. Engineering validation remains pending.']
def prepare_surface(raw):
 if len(raw)<84 or len(raw)>12*1024*1024:raise ValueError('Use bounded binary PicoGK STL')
 count=struct.unpack_from('<I',raw,80)[0]
 if not 4<=count<=200000 or len(raw)!=84+50*count:raise ValueError('Invalid binary STL')
 points=[];lines=['solid bracket']
 for i in range(count):
  values=struct.unpack_from('<12fH',raw,84+i*50);vertices=[values[j:j+3] for j in (3,6,9)]
  if not all(math.isfinite(x) for v in vertices for x in v):raise ValueError('Nonfinite STL')
  points.extend(vertices);lines+=['facet normal 0 0 0','outer loop']+['vertex '+' '.join(format(x*.001,'.12g') for x in v) for v in vertices]+['endloop','endfacet']
 bounds=[[min(p[k] for p in points),max(p[k] for p in points)] for k in range(3)]
 if any(a<-.6 or b>limit+.6 for (a,b),limit in zip(bounds,[60,30,40])) or any(b-a<limit-2 for (a,b),limit in zip(bounds,[60,30,40])):raise ValueError('Only the default 60×30×40 mm native bracket envelope is supported')
 converted=('\n'.join(lines+['endsolid bracket'])+'\n').encode()
 return converted,{'source_stl_sha256':hashlib.sha256(raw).hexdigest(),'converted_surface_sha256':hashlib.sha256(converted).hexdigest(),'triangles':count,'bounds_mm':bounds,'unit_conversion':'mm to m, factor 0.001; no geometry smoothing or repair'}

MESHES={'coarse':[24,14,16],'medium':[32,20,22],'fine':[40,24,28]}
def make_case(root,raw,mesh_name='coarse'):
 if mesh_name not in MESHES:raise ValueError('Unsupported bracket-flow mesh')
 root=Path(root);surface,metadata=prepare_surface(raw)
 def write(name,data):
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data if isinstance(data,bytes) else data.encode())
 write('constant/triSurface/bracket.stl',surface)
 write('system/blockMeshDict',header('blockMeshDict')+'''scale 1;
vertices ((-0.12 -0.09 -0.10) (0.24 -0.09 -0.10) (0.24 0.12 -0.10) (-0.12 0.12 -0.10) (-0.12 -0.09 0.14) (0.24 -0.09 0.14) (0.24 0.12 0.14) (-0.12 0.12 0.14));
blocks (hex (0 1 2 3 4 5 6 7) (24 14 16) simpleGrading (1 1 1)); edges ();
boundary (inlet {type patch;faces ((0 4 7 3));} outlet {type patch;faces ((1 2 6 5));} sides {type wall;faces ((0 1 5 4)(3 7 6 2)(0 3 2 1)(4 5 6 7));}); mergePatchPairs ();
''')
 write('system/snappyHexMeshDict',header('snappyHexMeshDict')+'''castellatedMesh true; snap true; addLayers false;
geometry {bracket.stl {type triSurfaceMesh;name bracket;} wake {type searchableBox;min (0.06 -0.005 -0.015);max (0.16 0.035 0.065);}}
castellatedMeshControls {maxLocalCells 150000; maxGlobalCells 200000;minRefinementCells 0;maxLoadUnbalance 0.1;nCellsBetweenLevels 3;features ();refinementSurfaces {bracket {level (3 3);patchInfo {type wall;}}} resolveFeatureAngle 30;refinementRegions {wake {mode inside;levels ((1e15 2));}};locationInMesh (-0.111 -0.081 -0.091);allowFreeStandingZoneFaces true;}
snapControls {nSmoothPatch 3;tolerance 2.0;nSolveIter 30;nRelaxIter 5;nFeatureSnapIter 10;implicitFeatureSnap true;explicitFeatureSnap false;multiRegionFeatureSnap false;}
addLayersControls {relativeSizes true;layers {};expansionRatio 1.0;finalLayerThickness 0.3;minThickness 0.1;nGrow 0;featureAngle 60;nRelaxIter 3;nSmoothSurfaceNormals 1;nSmoothNormals 3;nSmoothThickness 10;maxFaceThicknessRatio 0.5;maxThicknessToMedialRatio 0.3;minMedianAxisAngle 90;nBufferCellsNoExtrude 0;nLayerIter 50;}
meshQualityControls {maxNonOrtho 65;maxBoundarySkewness 20;maxInternalSkewness 4;maxConcave 80;minVol 1e-16;minTetQuality 1e-15;minArea -1;minTwist 0.02;minDeterminant 0.001;minFaceWeight 0.05;minVolRatio 0.01;minTriangleTwist -1;nSmoothScale 4;errorReduction 0.75;}
mergeTolerance 1e-6;
''')
 write('system/controlDict',header('controlDict')+'''application simpleFoam;startFrom startTime;startTime 0;stopAt endTime;endTime 1000;deltaT 1;writeControl timeStep;writeInterval 1000;purgeWrite 0;writeFormat ascii;writePrecision 14;writeCompression off;timeFormat general;timePrecision 8;runTimeModifiable false;
''')
 write('system/fvSchemes',header('fvSchemes')+'''ddtSchemes {default steadyState;} gradSchemes {default Gauss linear;} divSchemes {default none;div(phi,U) bounded Gauss upwind;div((nuEff*dev2(T(grad(U))))) Gauss linear;} laplacianSchemes {default Gauss linear corrected;} interpolationSchemes {default linear;} snGradSchemes {default corrected;} fluxRequired {default no;p;}
''')
 write('system/fvSolution',header('fvSolution')+'''solvers {p {solver GAMG;tolerance 1e-9;relTol 0.01;smoother GaussSeidel;} U {solver smoothSolver;smoother symGaussSeidel;tolerance 1e-9;relTol 0.01;}}
SIMPLE {nNonOrthogonalCorrectors 2;consistent yes;}
relaxationFactors {fields {p 0.3;} equations {U 0.7;}}
''')
 write('constant/transportProperties',header('transportProperties')+'transportModel Newtonian;nu [0 2 -1 0 0 0 0] 0.0001;\n')
 write('constant/turbulenceProperties',header('turbulenceProperties')+'simulationType laminar;\n')
 write('0/U',header('U','volVectorField')+'''dimensions [0 1 -1 0 0 0 0];internalField uniform (0.01 0 0);boundaryField {inlet {type fixedValue;value uniform (0.01 0 0);}outlet {type zeroGradient;}sides {type slip;}bracket {type fixedValue;value uniform (0 0 0);}}
''')
 write('0/p',header('p','volScalarField')+'''dimensions [0 2 -2 0 0 0 0];internalField uniform 0;boundaryField {inlet {type zeroGradient;}outlet {type fixedValue;value uniform 0;}sides {type zeroGradient;}bracket {type zeroGradient;}}
''')
 if mesh_name!='coarse':
  path=root/'system/blockMeshDict';path.write_text(path.read_text().replace('(24 14 16)', '('+' '.join(map(str,MESHES[mesh_name]))+')'))
 return metadata

def command(root,name,args=(),timeout=180):
 with (root/(name+'.log')).open('w') as log:
  proc=subprocess.run([name,'-case',str(root),*args],stdout=log,stderr=subprocess.STDOUT,timeout=timeout,cwd=root)
 if proc.returncode:raise ValueError(name+' failed: '+(root/(name+'.log')).read_text()[-1500:])

def mesh_list(path):
 text=Path(path).read_text();text=re.sub(r'/\*.*?\*/','',text,flags=re.S);text=re.sub(r'//[^\n]*','',text)
 match=re.search(r'}\s*(\d+)\s*\((.*)\)\s*$',text,re.S)
 if not match:raise ValueError('Malformed mesh list')
 return int(match[1]),match[2]
def cell_positions(root,count):
 root=Path(root);np,raw=mesh_list(root/'points');points=[tuple(map(float,v.split())) for v in re.findall(r'\(([^()]*)\)',raw)]
 nf,raw=mesh_list(root/'faces');faces=[list(map(int,v.split())) for v in re.findall(r'\d+\(([^()]*)\)',raw)]
 no,raw=mesh_list(root/'owner');owners=list(map(int,raw.split()));nn,raw=mesh_list(root/'neighbour');neighbours=list(map(int,raw.split()))
 if len(points)!=np or len(faces)!=nf or len(owners)!=nf or no!=nf or len(neighbours)!=nn:raise ValueError('Mesh addressing size mismatch')
 cells=[set() for _ in range(count)]
 for face,owner in zip(faces,owners):
  if not 0<=owner<count or any(not 0<=v<np for v in face):raise ValueError('Mesh addressing outside bounds')
  cells[owner].update(face)
 for face,neighbour in zip(faces,neighbours):
  if not 0<=neighbour<count:raise ValueError('Invalid neighbour')
  cells[neighbour].update(face)
 if any(len(c)<4 for c in cells):raise ValueError('Degenerate cell')
 return [tuple(sum(points[v][k] for v in sorted(cell))/len(cell) for k in range(3)) for cell in cells]

def boundary_flux(text,patch):
 match=re.search(r'\b'+patch+r'\s*\{([^{}]*)\}',text,re.S)
 if not match:raise ValueError('Missing boundary flux: '+patch)
 field=re.search(r'value\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;',match[1],re.S)
 if field:
  values=list(map(float,field[2].split()))
  if len(values)!=int(field[1]) or not all(math.isfinite(v) for v in values):raise ValueError('Invalid patch flux')
  return sum(values)
 uniform=re.search(r'value\s+uniform\s+([^;]+);',match[1])
 if uniform and float(uniform[1])==0:return 0.
 raise ValueError('Unsupported boundary flux')

def evaluate_case(root,metadata,mesh_name='coarse',source_raw=None):
 if mesh_name not in MESHES:raise ValueError('Unsupported bracket-flow mesh')
 root=Path(root);vectors=field_values(root/'1000/U',True);pressures=field_values(root/'1000/p');centres=cell_positions(root/'constant/polyMesh',len(vectors))
 if not 1000<=len(vectors)<=200000 or len(vectors)!=len(pressures) or len(vectors)!=len(centres):raise ValueError('Invalid field count')
 rows=[dict(zip(('x_m','y_m','z_m','u_m_s','v_m_s','w_m_s','p_kinematic_m2_s2'),[*c,*u,p])) for c,u,p in zip(centres,vectors,pressures)]
 mesh=(root/'checkMesh.log').read_text();surface=(root/'surfaceCheck.log').read_text();log=(root/'simpleFoam.log').read_text()
 residuals={key:[float(x) for x in re.findall(r'Solving for '+key+r', Initial residual = ([^,\s]+)',log)] for key in ('Ux','Uy','Uz','p')}
 if any(len(v)<1000 for v in residuals.values()) or 'Time = 1000' not in log or '\nEnd\n' not in log:raise ValueError('Incomplete solver iteration history')
 last={k:v[-1] for k,v in residuals.items()};history=[{'iteration':i+1,'Ux':residuals['Ux'][i],'Uy':residuals['Uy'][i],'Uz':residuals['Uz'][i],'p':residuals['p'][i*3]} for i in range(1000)]
 continuity=[float(x) for x in re.findall(r'time step continuity errors : sum local = ([^,\s]+)',log)]
 phi=(root/'1000/phi').read_text();flux={name:boundary_flux(phi,name) for name in ('inlet','outlet','sides','bracket')};imbalance=abs(sum(flux.values()))/abs(flux['inlet'])
 max_nonorth=re.search(r'Mesh non-orthogonality Max:\s*([\d.eE+-]+)',mesh);max_skew=re.search(r'Max skewness\s*=\s*([\d.eE+-]+)',mesh)
 checks={'surface_closed':'Surface is closed' in surface,'mesh_quality':'Mesh OK.' in mesh,'finite_fields':all(math.isfinite(v) for r in rows for v in r.values()),'velocity_residual':max(last[k] for k in ('Ux','Uy','Uz'))<1e-5,'pressure_residual':last['p']<1e-4,'boundary_mass_balance':imbalance<1e-5,'final_local_continuity':bool(continuity) and continuity[-1]<1e-6}
 result={'mesh_name':mesh_name,'kind':'bracket_flow','validation_status':'exploratory_bracket_flow_checks_passed_not_engineering_validated' if all(checks.values()) else 'exploratory_bracket_flow_checks_need_attention','backend':'OpenFOAM 1912 · snappyHexMesh / simpleFoam · laminar SIMPLE','inputs':dict(INPUTS,background_cells=MESHES[mesh_name]),'source':metadata,'cells':len(rows),'reynolds_length_60mm':6.,'mesh':{'maximum_nonorthogonality_degrees':float(max_nonorth[1]) if max_nonorth else None,'maximum_skewness':float(max_skew[1]) if max_skew else None,'surface_refinement_level':3,'near_surface_nominal_cell_m':max(.36/MESHES[mesh_name][0],.21/MESHES[mesh_name][1],.24/MESHES[mesh_name][2])/8,'prism_layers':False},'residuals':last,'residual_history':history,'boundary_flux_m3_s':flux,'relative_boundary_mass_imbalance':imbalance,'final_local_continuity_error':continuity[-1] if continuity else None,'checks':checks,'tolerances':{'velocity_initial_residual':1e-5,'pressure_initial_residual':1e-4,'relative_boundary_mass_imbalance':1e-5,'final_local_continuity_error':1e-6},'field':rows,'limits':LIMITS}

 if source_raw is not None:
  from kcee.flow_bores import bore_checks
  result['bore_verification']=bore_checks(source_raw,root/'constant/polyMesh')
  from kcee.flow_sampling import sample_probes
  result['fixed_probes']=sample_probes(rows,root/'constant/polyMesh')
  result['mesh']['wake_refinement']={'min_m':[.06,-.005,-.015],'max_m':[.16,.035,.065],'level':2}
  result['inputs']['wake_refinement']=result['mesh']['wake_refinement']
 return result

def run_payload(raw,mesh_name='coarse'):
 import shutil
 with tempfile.TemporaryDirectory(prefix='kcee-bracket-flow-') as tmp:
  root=Path(tmp);metadata=make_case(root,raw,mesh_name);failure=None
  (root/'runtime.json').write_text(json.dumps({'package':subprocess.check_output(['dpkg-query','-W','-f=${Version}','openfoam'],text=True),'binaries_sha256':{name:hashlib.sha256(Path(shutil.which(name)).read_bytes()).hexdigest() for name in ('snappyHexMesh','simpleFoam','checkMesh','surfaceCheck')}}))
  try:
   command(root,'surfaceCheck',['constant/triSurface/bracket.stl']);command(root,'blockMesh');command(root,'snappyHexMesh',['-overwrite']);command(root,'checkMesh');command(root,'simpleFoam',timeout=480);result=evaluate_case(root,metadata,mesh_name,raw)
  except Exception as error:
   failure=str(error)[:2000];result=None;(root/'job.log').write_text(failure+'\n')
  buffer=io.BytesIO()
  with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
   for path in sorted(root.rglob('*')):
    if path.is_file():archive.write(path,path.relative_to(root).as_posix())
  data=buffer.getvalue()
  if len(data)>24*1024*1024:raise ValueError('Solver archive exceeds limit')
  return {'result':result,'error':failure,'archive_base64':base64.b64encode(data).decode(),'archive_sha256':hashlib.sha256(data).hexdigest()}
