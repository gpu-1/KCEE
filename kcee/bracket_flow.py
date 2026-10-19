"""Exploratory external laminar OpenFOAM flow around a bounded native bracket STL."""
import base64,hashlib,io,json,math,re,struct,subprocess,tempfile,zipfile
from pathlib import Path
from kcee.openfoam_vortex import header,field_values
from kcee.flow_sampling import LEGACY,COMPACT,DEFAULT,sampling_spec
INPUTS={'inlet_velocity_m_s':.01,'kinematic_viscosity_m2_s':.0001,'density_kg_m3':1.,'domain_min_m':[-.12,-.09,-.10],'domain_max_m':[.24,.12,.14],'background_cells':[24,14,16],'surface_refinement_level':3,'maximum_iterations':1500,'mesh_smoothing':{'n_smooth_patch':5,'n_smooth_scale':8}}
LIMITS=['Exploratory steady laminar external flow at Reynolds number 6 based on 60 mm and inlet speed; not realistic service conditions.','Single mesh, no prism layers; thin walls, bores and root details may be under-resolved. No mesh/domain convergence or force acceptance.','Uniform +x inlet, zero kinematic pressure outlet, slip far-field sides and no-slip bracket. No mounting wall, bolts, contact, turbulence or thermal coupling.','OpenFOAM p is kinematic pressure in m²/s² at the outlet reference, not pressure in Pa.','Velocity and pressure are cell fields. Field positions use signed-volume centroids of triangulated saved mesh cells, independently reconstructed rather than solver-native exported centers. Engineering validation remains pending.']
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
DOMAIN_STEPS={'base':0,'expanded':4,'far':8,'outer':12}
FAR_MESHES={'coarse':[36,25,28],'medium':[48,36,38],'fine':[56,40,44]}
def domain_spec(mesh_name='coarse',domain_name='base'):
 if mesh_name not in MESHES or domain_name not in DOMAIN_STEPS:raise ValueError('Unsupported flow mesh or domain')
 if domain_name=='outer' and mesh_name=='fine':
  ref=domain_spec('medium','outer');cells=[65,49,53];lo=ref['domain_min_m'];hi=ref['domain_max_m']
  return {'domain_min_m':lo,'domain_max_m':hi,'background_cells':cells,'background_spacing_m':[(b-a)/n for a,b,n in zip(lo,hi,cells)]}
 if domain_name!='base' and mesh_name!='medium':
  if domain_name!='far':raise ValueError('Expanded domain uses the fixed medium resolution')
  reference=domain_spec('medium','far');cells=list(FAR_MESHES[mesh_name]);lo=reference['domain_min_m'];hi=reference['domain_max_m']
  return {'domain_min_m':lo,'domain_max_m':hi,'background_cells':cells,'background_spacing_m':[(b-a)/n for a,b,n in zip(lo,hi,cells)]}
 lo=list(INPUTS['domain_min_m']);hi=list(INPUTS['domain_max_m']);cells=list(MESHES[mesh_name]);steps=DOMAIN_STEPS[domain_name]
 spacing=[(b-a)/n for a,b,n in zip(lo,hi,cells)]
 return {'domain_min_m':[a-steps*h for a,h in zip(lo,spacing)],'domain_max_m':[b+steps*h for b,h in zip(hi,spacing)],'background_cells':[n+2*steps for n in cells],'background_spacing_m':spacing}

LOCAL_PROFILE='wake-below-v1'
LOCAL_REGIONS=[{'name':'targetWake','min_m':[.065,-.002,.002],'max_m':[.135,.032,.038],'level':3},{'name':'targetBelow','min_m':[.015,.003,-.030],'max_m':[.045,.027,-.010],'level':3}]
def validate_profile(profile,mesh,domain,bore_level):
 if profile not in ('baseline',LOCAL_PROFILE):raise ValueError('Unsupported local CFD refinement profile')
 if profile==LOCAL_PROFILE and (mesh not in ('medium','fine') or domain not in ('far','outer') or bore_level!=4):raise ValueError('Targeted refinement uses medium/fine far-domain or medium/fine outer-domain cases with bore level 4')

def make_case(root,raw,mesh_name='coarse',domain_name='base',bore_level=4,local_profile='baseline'):
 validate_profile(local_profile,mesh_name,domain_name,bore_level)
 if type(bore_level) is not int or bore_level not in (4,5):raise ValueError('Bore level must be 4 or 5')
 spec=domain_spec(mesh_name,domain_name)
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
geometry {bracket.stl {type triSurfaceMesh;name bracket;} wake {type searchableBox;min (0.06 -0.005 -0.015);max (0.16 0.035 0.065);} bore1 {type searchableSphere;centre (0.033 0.015 0.00175);radius 0.005;} bore2 {type searchableSphere;centre (0.048 0.015 0.00175);radius 0.005;} bore3 {type searchableSphere;centre (0.00175 0.015 0.016);radius 0.005;} bore4 {type searchableSphere;centre (0.00175 0.015 0.030);radius 0.005;}}
castellatedMeshControls {maxLocalCells 150000; maxGlobalCells 200000;minRefinementCells 0;maxLoadUnbalance 0.1;nCellsBetweenLevels 3;features ();refinementSurfaces {bracket {level (3 3);patchInfo {type wall;}}} resolveFeatureAngle 30;refinementRegions {wake {mode inside;levels ((1e15 2));} bore1 {mode inside;levels ((1e15 4));} bore2 {mode inside;levels ((1e15 4));} bore3 {mode inside;levels ((1e15 4));} bore4 {mode inside;levels ((1e15 4));}};locationInMesh (-0.111 -0.081 -0.091);allowFreeStandingZoneFaces true;}
snapControls {nSmoothPatch 5;tolerance 2.0;nSolveIter 30;nRelaxIter 5;nFeatureSnapIter 10;implicitFeatureSnap true;explicitFeatureSnap false;multiRegionFeatureSnap false;}
addLayersControls {relativeSizes true;layers {};expansionRatio 1.0;finalLayerThickness 0.3;minThickness 0.1;nGrow 0;featureAngle 60;nRelaxIter 3;nSmoothSurfaceNormals 1;nSmoothNormals 3;nSmoothThickness 10;maxFaceThicknessRatio 0.5;maxThicknessToMedialRatio 0.3;minMedianAxisAngle 90;nBufferCellsNoExtrude 0;nLayerIter 50;}
meshQualityControls {maxNonOrtho 65;maxBoundarySkewness 20;maxInternalSkewness 4;maxConcave 80;minVol 1e-16;minTetQuality 1e-15;minArea -1;minTwist 0.02;minDeterminant 0.001;minFaceWeight 0.05;minVolRatio 0.01;minTriangleTwist -1;nSmoothScale 8;errorReduction 0.75;}
mergeTolerance 1e-6;
''')
 write('system/controlDict',header('controlDict')+'''application simpleFoam;startFrom startTime;startTime 0;stopAt endTime;endTime 1500;deltaT 1;writeControl timeStep;writeInterval 1500;purgeWrite 0;writeFormat ascii;writePrecision 14;writeCompression off;timeFormat general;timePrecision 8;runTimeModifiable false;
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
 if domain_name!='base':
  lo=spec['domain_min_m'];hi=spec['domain_max_m'];vertices=[(lo[0],lo[1],lo[2]),(hi[0],lo[1],lo[2]),(hi[0],hi[1],lo[2]),(lo[0],hi[1],lo[2]),(lo[0],lo[1],hi[2]),(hi[0],lo[1],hi[2]),(hi[0],hi[1],hi[2]),(lo[0],hi[1],hi[2])]
  path=root/'system/blockMeshDict';text=path.read_text();text=re.sub(r'vertices \(.*?\);', 'vertices ('+' '.join('('+' '.join(format(x,'.15g') for x in v)+')' for v in vertices)+');',text,flags=re.S)
  text=text.replace('('+' '.join(map(str,MESHES[mesh_name]))+')','('+' '.join(map(str,spec['background_cells']))+')');path.write_text(text)
 if domain_name=='far' and mesh_name=='fine':
  path=root/'system/snappyHexMeshDict';path.write_text(path.read_text().replace('maxLocalCells 150000','maxLocalCells 200000'))
 if bore_level==5:
  path=root/'system/snappyHexMeshDict';path.write_text(path.read_text().replace('levels ((1e15 4))','levels ((1e15 5))').replace('maxLocalCells 150000','maxLocalCells 250000').replace('maxLocalCells 200000','maxLocalCells 250000').replace('maxGlobalCells 200000','maxGlobalCells 250000'))
 if local_profile==LOCAL_PROFILE:
  path=root/'system/snappyHexMeshDict';text=path.read_text()
  for region in LOCAL_REGIONS:
   vec=lambda values:'('+' '.join(map(str,values))+')'
   text=text.replace('geometry {','geometry {'+region['name']+' {type searchableBox;min '+vec(region['min_m'])+';max '+vec(region['max_m'])+';} ',1)
   text=text.replace('refinementRegions {','refinementRegions {'+region['name']+' {mode inside;levels ((1e15 3));} ',1)
  text=text.replace('maxLocalCells 150000','maxLocalCells 250000').replace('maxLocalCells 200000','maxLocalCells 250000').replace('maxGlobalCells 200000','maxGlobalCells 250000');path.write_text(text)
 if mesh_name=='fine' and domain_name=='outer':
  path=root/'system/snappyHexMeshDict';path.write_text(path.read_text().replace('maxLocalCells 250000','maxLocalCells 350000').replace('maxLocalCells 150000','maxLocalCells 350000').replace('maxGlobalCells 250000','maxGlobalCells 350000').replace('maxGlobalCells 200000','maxGlobalCells 350000'))
 return metadata

def command(root,name,args=(),timeout=180):
 from kcee.cfd_control import run_logged
 proc=run_logged([name,'-case',str(root),*args],root,name,timeout)
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

def mesh_total_volume(log):
 match=re.search(r'Total volume\s*=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)',log)
 if not match or not math.isfinite(float(match[1])) or float(match[1])<=0:raise ValueError('Missing positive OpenFOAM total volume')
 return float(match[1])

def evaluate_case(root,metadata,mesh_name='coarse',source_raw=None,domain_name='base',bore_level=4,sampling_version=LEGACY,local_profile='baseline'):
 validate_profile(local_profile,mesh_name,domain_name,bore_level)
 sampling_spec(sampling_version)
 if type(bore_level) is not int or bore_level not in (4,5):raise ValueError('Bore level must be 4 or 5')
 spec=domain_spec(mesh_name,domain_name)
 if mesh_name not in MESHES:raise ValueError('Unsupported bracket-flow mesh')
 root=Path(root);vectors=field_values(root/'1500/U',True);pressures=field_values(root/'1500/p');from kcee.flow_centres import volume_centres
 centres,vertex_means,position_audit=volume_centres(root/'constant/polyMesh',len(vectors))
 if not 1000<=len(vectors)<=(350000 if mesh_name=='fine' and domain_name=='outer' else 250000 if bore_level==5 or local_profile==LOCAL_PROFILE else 200000) or len(vectors)!=len(pressures) or len(vectors)!=len(centres):raise ValueError('Invalid field count')
 rows=[dict(zip(('x_m','y_m','z_m','u_m_s','v_m_s','w_m_s','p_kinematic_m2_s2'),[*c,*u,p])) for c,u,p in zip(centres,vectors,pressures)]
 mesh=(root/'checkMesh.log').read_text();surface=(root/'surfaceCheck.log').read_text();log=(root/'simpleFoam.log').read_text()
 residuals={key:[float(x) for x in re.findall(r'Solving for '+key+r', Initial residual = ([^,\s]+)',log)] for key in ('Ux','Uy','Uz','p')}
 if any(len(v)<1500 for v in residuals.values()) or 'Time = 1500' not in log or '\nEnd\n' not in log:raise ValueError('Incomplete solver iteration history')
 last={k:v[-1] for k,v in residuals.items()};history=[{'iteration':i+1,'Ux':residuals['Ux'][i],'Uy':residuals['Uy'][i],'Uz':residuals['Uz'][i],'p':residuals['p'][i*3]} for i in range(1500)]
 continuity=[float(x) for x in re.findall(r'time step continuity errors : sum local = ([^,\s]+)',log)]
 phi=(root/'1500/phi').read_text();flux={name:boundary_flux(phi,name) for name in ('inlet','outlet','sides','bracket')};imbalance=abs(sum(flux.values()))/abs(flux['inlet'])
 native_volume=mesh_total_volume(mesh)
 position_audit['openfoam_total_fluid_volume_m3']=native_volume
 position_audit['relative_total_volume_difference']=abs(position_audit['total_fluid_volume_m3']-native_volume)/native_volume
 position_audit['relative_total_volume_tolerance']=1e-6
 max_nonorth=re.search(r'Mesh non-orthogonality Max:\s*([\d.eE+-]+)',mesh);max_skew=re.search(r'Max skewness\s*=\s*([\d.eE+-]+)',mesh)
 checks={'reconstructed_volume_agreement':position_audit['relative_total_volume_difference']<1e-6,'surface_closed':'Surface is closed' in surface,'mesh_quality':'Mesh OK.' in mesh,'finite_fields':all(math.isfinite(v) for r in rows for v in r.values()),'velocity_residual':max(last[k] for k in ('Ux','Uy','Uz'))<1e-5,'pressure_residual':last['p']<1e-4,'boundary_mass_balance':imbalance<1e-5,'final_local_continuity':bool(continuity) and continuity[-1]<1e-6}
 result={'mesh_name':mesh_name,'kind':'bracket_flow','validation_status':'exploratory_bracket_flow_checks_passed_not_engineering_validated' if all(checks.values()) else 'exploratory_bracket_flow_checks_need_attention','backend':'OpenFOAM 1912 · snappyHexMesh / simpleFoam · laminar SIMPLE','inputs':dict(INPUTS,**{k:v for k,v in spec.items() if k!='background_spacing_m'}),'source':metadata,'cells':len(rows),'reynolds_length_60mm':6.,'mesh':{'maximum_nonorthogonality_degrees':float(max_nonorth[1]) if max_nonorth else None,'maximum_skewness':float(max_skew[1]) if max_skew else None,'surface_refinement_level':3,'near_surface_nominal_cell_m':max(spec['background_spacing_m'])/8,'prism_layers':False},'residuals':last,'residual_history':history,'boundary_flux_m3_s':flux,'relative_boundary_mass_imbalance':imbalance,'final_local_continuity_error':continuity[-1] if continuity else None,'checks':checks,'tolerances':{'velocity_initial_residual':1e-5,'pressure_initial_residual':1e-4,'relative_boundary_mass_imbalance':1e-5,'final_local_continuity_error':1e-6},'field':rows,'field_position_basis':'triangulated_polyhedral_volume_centroids','cell_position_audit':position_audit,'limits':LIMITS}

 if source_raw is not None:
  from kcee.flow_bores import bore_checks
  result['bore_verification']=bore_checks(source_raw,root/'constant/polyMesh')
  apply_sampling(result,vertex_means,root/'constant/polyMesh',sampling_version)
  result['mesh']['wake_refinement']={'min_m':[.06,-.005,-.015],'max_m':[.16,.035,.065],'level':2}
  result['inputs']['wake_refinement']=result['mesh']['wake_refinement']
  result['mesh']['bore_refinement']={'centres_m':[[.033,.015,.00175],[.048,.015,.00175],[.00175,.015,.016],[.00175,.015,.030]],'radius_m':.005,'level':bore_level,'nominal_cell_m':max(spec['background_spacing_m'])/(2**bore_level)}
  result['inputs']['bore_refinement']=result['mesh']['bore_refinement']
 if local_profile==LOCAL_PROFILE:
  result['inputs']['local_refinement_profile']=local_profile
  result['mesh']['targeted_refinement']={'regions':LOCAL_REGIONS,'nominal_cell_m':max(spec['background_spacing_m'])/8}
  result['inputs']['targeted_refinement']=result['mesh']['targeted_refinement']
 if domain_name!='base':result['domain_name']=domain_name
 return result

def apply_sampling(result,vertex_means,mesh_root,version):
 sampling_spec(version);rows=result['field']
 from kcee.flow_sampling import sample_probes
 result['fixed_probes']=sample_probes(rows,mesh_root,'triangulated_polyhedral_volume_centroids',compact=version==COMPACT)
 legacy=[dict(row,x_m=pos[0],y_m=pos[1],z_m=pos[2]) for row,pos in zip(rows,vertex_means)]
 legacy_probes=sample_probes(legacy,mesh_root,'mesh_vertex_averages',compact=version==COMPACT)
 result['sampling_audit']={'method':'Same solved fields and wall mesh; only field-location basis changes. This isolates sampling-position sensitivity from mesh/solver changes.','legacy_probes':legacy_probes,'probe_changes':[{"name":a['name'],"available":a['available'] and b['available'],**({'pressure_change_m2_s2':a['kinematic_pressure_m2_s2']-b['kinematic_pressure_m2_s2'],'pressure_change_normalized_by_inlet_dynamic_scale':abs(a['kinematic_pressure_m2_s2']-b['kinematic_pressure_m2_s2'])/.00005} if a['available'] and b['available'] else {})} for a,b in zip(result['fixed_probes'],legacy_probes)]}
 if version==COMPACT:result['inputs']['probe_sampling']=version;result['sampling']=sampling_spec(version)
 return result

def run_payload(raw,mesh_name='coarse',domain_name='base',bore_level=4,sampling_version=DEFAULT,local_profile='baseline'):
 from kcee.cfd_control import checkpoint
 checkpoint('preparing',case=mesh_name+' / '+domain_name)
 validate_profile(local_profile,mesh_name,domain_name,bore_level)
 if local_profile==LOCAL_PROFILE and sampling_version!=COMPACT:raise ValueError('Targeted refinement requires Compact v1 sampling')
 sampling_spec(sampling_version)
 import shutil
 with tempfile.TemporaryDirectory(prefix='kcee-bracket-flow-') as tmp:
  root=Path(tmp);metadata=make_case(root,raw,mesh_name,domain_name,bore_level,local_profile);failure=None
  (root/'sampling.json').write_text(json.dumps(sampling_spec(sampling_version),sort_keys=True))
  (root/'runtime.json').write_text(json.dumps({'package':subprocess.check_output(['dpkg-query','-W','-f=${Version}','openfoam'],text=True),'binaries_sha256':{name:hashlib.sha256(Path(shutil.which(name)).read_bytes()).hexdigest() for name in ('snappyHexMesh','simpleFoam','checkMesh','surfaceCheck')}}))
  try:
   command(root,'surfaceCheck',['constant/triSurface/bracket.stl']);command(root,'blockMesh');command(root,'snappyHexMesh',['-overwrite']);command(root,'checkMesh');command(root,'simpleFoam',timeout=900);from kcee.cfd_control import checkpoint;checkpoint('postprocessing');result=evaluate_case(root,metadata,mesh_name,raw,domain_name,bore_level,sampling_version,local_profile)
  except Exception as error:
   failure=str(error)[:2000];result=None;(root/'job.log').write_text(failure+'\n')
  buffer=io.BytesIO()
  with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
   for path in sorted(root.rglob('*')):
    if path.is_file():archive.write(path,path.relative_to(root).as_posix())
  data=buffer.getvalue()
  if len(data)>(48 if mesh_name=='fine' and domain_name=='outer' else 36)*1024*1024:raise ValueError('Solver archive exceeds limit')
  return {'result':result,'error':failure,'archive_base64':base64.b64encode(data).decode(),'archive_sha256':hashlib.sha256(data).hexdigest()}
