"""Audit exported OpenFOAM decomposition centres; never call a partial export full C."""
import math,re

def decomposition_centres(text,original_points,cell_count):
 if len(text)>96*1024*1024 or 'ASCII' not in text[:150] or 'DATASET UNSTRUCTURED_GRID' not in text[:200]:raise ValueError('Use bounded ASCII legacy VTK')
 def section(pattern):
  match=re.search(pattern,text)
  if not match:raise ValueError('Missing VTK section')
  return match,text[match.end():].split()
 match,tokens=section(r'\bPOINTS\s+(\d+)\s+float\s+');n=int(match[1])
 if not original_points<=n<=original_points+cell_count:raise ValueError('Unexpected decomposition point count')
 values=list(map(float,tokens[:3*n]));points=[values[i:i+3] for i in range(0,len(values),3)]
 if len(points)!=n or not all(math.isfinite(v) for v in values):raise ValueError('Invalid VTK coordinates')
 match,tokens=section(r'\bCELLS\s+(\d+)\s+(\d+)\s+');nc=int(match[1]);total=int(match[2]);connectivity=list(map(int,tokens[:total]));cells=[];offset=0
 for _ in range(nc):
  size=connectivity[offset];cell=connectivity[offset+1:offset+1+size];offset+=size+1
  if size not in (4,5,6,8) or len(cell)!=size or any(i<0 or i>=n for i in cell):raise ValueError('Invalid VTK connectivity')
  cells.append(cell)
 if offset!=total:raise ValueError('Invalid VTK connectivity length')
 match,tokens=section(r'\bcellID\s+1\s+(\d+)\s+int\s+');ids=list(map(int,tokens[:int(match[1])]))
 if len(ids)!=nc or int(match[1])!=nc or any(i<0 or i>=cell_count for i in ids) or set(ids)!=set(range(cell_count)):raise ValueError('Invalid native cell IDs')
 centres={};point_owners={}
 for vertices,cell in zip(cells,ids):
  for point in vertices:
   if point<original_points:continue
   if point in point_owners and point_owners[point]!=cell:raise ValueError('Decomposition centre shared by different cells')
   if cell in centres and centres[cell]!=points[point]:raise ValueError('Multiple centres for one native cell')
   point_owners[point]=cell;centres[cell]=points[point]
 if len(point_owners)!=n-original_points:raise ValueError('Unreferenced decomposition centres')
 return centres

def audit(text,original_points,flow):
 centres=decomposition_centres(text,original_points,flow['cells']);field=flow['field']
 if not centres:raise ValueError('No native decomposition centres exported')
 shifts=[math.dist(pos,[field[i][k] for k in ('x_m','y_m','z_m')]) for i,pos in centres.items()]
 return {'method':'OpenFOAM foamToVTK -legacy -ascii -poly-decomp -no-point-data -with-ids; added centre points mapped through native cellID', 'native_centres_exported':len(centres),'total_cells':flow['cells'],'coverage_fraction':len(centres)/flow['cells'],'maximum_difference_m':max(shifts),'rms_difference_m':math.sqrt(sum(x*x for x in shifts)/len(shifts)),'probe_support_coverage':[{'name':p['name'],'native_support_cells_exported':sum(i in centres for i in p.get('support_cell_indices',[])),'support_cells':len(p.get('support_cell_indices',[]))} for p in flow['fixed_probes']], 'limits':['Only cells decomposed by the native VTK exporter expose their centres; standard cells are omitted. This is a partial geometry audit, not a complete native C field or native probe interpolation.', 'ASCII float export has limited precision. Differences include export rounding and geometry algorithms; no pressure error bound is inferred.']}


def audit_archive(data):
 """Run a fixed native exporter against bounded, selected archive members only."""
 import hashlib,io,json,shutil,subprocess,tempfile,zipfile
 from pathlib import Path
 from kcee.bracket_flow import mesh_list
 from kcee.flow_centres import volume_centres
 from kcee.flow_sampling import sample_probes,sampling_spec,LEGACY,COMPACT
 from kcee.openfoam_vortex import field_values,header
 if len(data)>36*1024*1024:raise ValueError('Native audit archive too large')
 with zipfile.ZipFile(io.BytesIO(data)) as z,tempfile.TemporaryDirectory(prefix='kcee-native-') as d:
  names=z.namelist()
  if len(names)!=len(set(names)) or len(names)>200 or sum(i.file_size for i in z.infolist())>192*1024*1024 or any(n.startswith('/') or '..' in n.split('/') for n in names):raise ValueError('Unsafe native audit archive')
  declared=json.loads(z.read('sampling.json')) if 'sampling.json' in names else sampling_spec(LEGACY)
  version=declared.get('version')
  if declared!=sampling_spec(version):raise ValueError('Native audit sampling declaration differs')
  root=Path(d)
  for name in ['1500/U','1500/p']+['constant/polyMesh/'+n for n in ('points','faces','owner','neighbour','boundary')]:
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
  (root/'system').mkdir();(root/'system/controlDict').write_text(header('controlDict')+'application foamToVTK;startFrom startTime;startTime 1500;stopAt endTime;endTime 1500;deltaT 1;writeControl timeStep;writeInterval 1;writeFormat ascii;writePrecision 14;runTimeModifiable false;')
  (root/'system/fvSchemes').write_text(header('fvSchemes')+'ddtSchemes {default steadyState;} gradSchemes {default Gauss linear;} divSchemes {default none;} laplacianSchemes {default Gauss linear corrected;} interpolationSchemes {default linear;} snGradSchemes {default corrected;}')
  (root/'system/fvSolution').write_text(header('fvSolution')+'solvers {}')
  args=['foamToVTK','-case',str(root),'-legacy','-ascii','-poly-decomp','-no-boundary','-no-point-data','-noFunctionObjects','-with-ids','-fields','(U p)','-time','1500']
  proc=subprocess.run(args,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120,text=True)
  if proc.returncode:raise ValueError('Native VTK export failed: '+proc.stdout[-1500:])
  files=list((root/'VTK').glob('*.vtk'))
  if len(files)!=1:raise ValueError('Expected one native VTK volume')
  raw=files[0].read_bytes();text=raw.decode();u=field_values(root/'1500/U',True);p=field_values(root/'1500/p');
  if not 1000<=len(u)<=250000 or len(u)!=len(p):raise ValueError('Invalid native audit field counts')
  centres,_,_=volume_centres(root/'constant/polyMesh',len(u))
  rows=[dict(zip(('x_m','y_m','z_m','u_m_s','v_m_s','w_m_s','p_kinematic_m2_s2'),[*c,*v,q])) for c,v,q in zip(centres,u,p)]
  np,_=mesh_list(root/'constant/polyMesh/points');flow={'cells':len(rows),'field':rows,'fixed_probes':sample_probes(rows,root/'constant/polyMesh','triangulated_polyhedral_volume_centroids',compact=version==COMPACT)}
  compact=sample_probes(rows,root/'constant/polyMesh','triangulated_polyhedral_volume_centroids',compact=True)
  if not all(p['available'] for p in flow['fixed_probes']+compact):raise ValueError('Missing original or compact stencil probes')
  original=flow['fixed_probes'];changes=[{'name':a['name'],'referenced_pressure_change_m2_s2':(b['kinematic_pressure_m2_s2']-compact[0]['kinematic_pressure_m2_s2'])-(a['kinematic_pressure_m2_s2']-original[0]['kinematic_pressure_m2_s2']),'velocity_vector_change_m_s':math.dist(a['velocity_m_s'],b['velocity_m_s'])} for a,b in zip(original,compact)]
  result=audit(text,np,flow);result['schema']='kcee.native-centre-stencil-audit.v1';result['stencil_audit']={'source_sampling_version':version,'method':'Same fields, centroid positions and wall visibility; select the enclosing tetrahedron with minimum maximum support radius, then minimum summed support distances, from the same bounded candidate pool. Diagnostic only; saved production probes are unchanged. This is custom interpolation, not native OpenFOAM sampling.','compact_probes':compact,'probe_changes':changes,'maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale':max(abs(p['referenced_pressure_change_m2_s2']) for p in changes)/.00005,'maximum_velocity_change_normalized_by_inlet':max(p['velocity_vector_change_m_s'] for p in changes)/.01}
  result.update({'source_archive_sha256':hashlib.sha256(data).hexdigest(),'native_export_sha256':hashlib.sha256(raw).hexdigest(),'exporter_sha256':hashlib.sha256(Path(shutil.which('foamToVTK')).read_bytes()).hexdigest(),'exporter_log':proc.stdout,'exported_centres_m':decomposition_centres(text,np,len(rows))})
  return result

def close(a,b):return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-15)

def validate_audit(data,flow):
 """Recompute all reported audit arithmetic against the immutable source field."""
 centres={int(k):v for k,v in data['exported_centres_m'].items()}
 if not centres or len(centres)!=data['native_centres_exported'] or data['total_cells']!=flow['cells'] or data['coverage_fraction']!=len(centres)/flow['cells']:raise ValueError('Invalid native coverage')
 if any(i<0 or i>=flow['cells'] or len(p)!=3 or not all(math.isfinite(v) for v in p) for i,p in centres.items()):raise ValueError('Invalid native centre records')
 shifts=[math.dist(p,[flow['field'][i][k] for k in ('x_m','y_m','z_m')]) for i,p in centres.items()]
 if not close(data['maximum_difference_m'],max(shifts)) or not close(data['rms_difference_m'],math.sqrt(sum(x*x for x in shifts)/len(shifts))):raise ValueError('Native audit arithmetic differs')
 expected=[{'name':p['name'],'native_support_cells_exported':sum(i in centres for i in p.get('support_cell_indices',[])),'support_cells':len(p.get('support_cell_indices',[]))} for p in flow['fixed_probes']]
 if data['probe_support_coverage']!=expected:raise ValueError('Native probe coverage differs')
 if 'stencil_audit' in data:
  from kcee.flow_sampling import PROBES
  probes=data['stencil_audit']['compact_probes'];original=flow['fixed_probes']
  if [(p['name'],p['requested_position_m']) for p in probes]!=[(n,list(p)) for n,p in PROBES]:raise ValueError('Compact probe coordinates differ')
  for p in probes:
   weights=p['weights'];indices=p['support_cell_indices']
   if len(weights)!=4 or len(indices)!=4 or any(type(i) is not int or i<0 or i>=flow['cells'] for i in indices) or len(set(indices))!=4 or not all(math.isfinite(w) for w in weights) or min(weights)<0 or abs(sum(weights)-1)>1e-12:raise ValueError('Invalid compact support weights')
   values=[flow['field'][i] for i in indices]
   if p['support_positions_m']!=[[r[k] for k in ('x_m','y_m','z_m')] for r in values]:raise ValueError('Compact support positions differ')
   if any(abs(sum(w*pos[k] for w,pos in zip(weights,p['support_positions_m']))-p['requested_position_m'][k])>1e-10 for k in range(3)):raise ValueError('Compact weights do not reconstruct the probe')
   distances=[math.dist(p['requested_position_m'],pos) for pos in p['support_positions_m']]
   if len(p['support_distances_m'])!=len(distances) or not all(close(a,b) for a,b in zip(p['support_distances_m'],distances)) or not close(p['maximum_support_distance_m'],max(distances)):raise ValueError('Compact support distances differ')
   for k,key in enumerate(('u_m_s','v_m_s','w_m_s','p_kinematic_m2_s2')):
    expected=sum(w*r[key] for w,r in zip(weights,values));actual=p['velocity_m_s'][k] if k<3 else p['kinematic_pressure_m2_s2']
    if actual!=expected:raise ValueError('Compact interpolation differs from source fields')
  changes=[{'name':a['name'],'referenced_pressure_change_m2_s2':(b['kinematic_pressure_m2_s2']-probes[0]['kinematic_pressure_m2_s2'])-(a['kinematic_pressure_m2_s2']-original[0]['kinematic_pressure_m2_s2']),'velocity_vector_change_m_s':math.dist(a['velocity_m_s'],b['velocity_m_s'])} for a,b in zip(original,probes)]
  a=data['stencil_audit']
  if len(a['probe_changes'])!=len(changes) or any(x['name']!=y['name'] or not close(x['referenced_pressure_change_m2_s2'],y['referenced_pressure_change_m2_s2']) or not close(x['velocity_vector_change_m_s'],y['velocity_vector_change_m_s']) for x,y in zip(a['probe_changes'],changes)) or not close(a['maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale'],max(abs(p['referenced_pressure_change_m2_s2']) for p in changes)/.00005) or not close(a['maximum_velocity_change_normalized_by_inlet'],max(p['velocity_vector_change_m_s'] for p in changes)/.01):raise ValueError('Compact stencil change arithmetic differs')
 for key in ('exporter_sha256','native_export_sha256','source_archive_sha256'):
  if not re.fullmatch('[a-f0-9]{64}',data[key]):raise ValueError('Invalid native evidence hash')
 return True

if __name__=='__main__':
 import sys,json
 print(json.dumps(audit_archive(sys.stdin.buffer.read())))
