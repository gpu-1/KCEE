"""Archived integration-point peaks and corner tetrahedron quality diagnostics."""
import math,zipfile
from kcee.fea import table
from kcee.energy import strain_energy_density

def tetra_quality(points):
    if len(points)!=4 or any(len(p)!=3 or not all(math.isfinite(x) for x in p) for p in points):raise ValueError('Invalid tetrahedron coordinates')
    a,b,c,d=points;u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];w=[d[i]-a[i] for i in range(3)]
    volume=(u[0]*(v[1]*w[2]-v[2]*w[1])-u[1]*(v[0]*w[2]-v[2]*w[0])+u[2]*(v[0]*w[1]-v[1]*w[0]))/6
    if not math.isfinite(volume) or volume<=0:raise ValueError('Non-positive tetrahedron volume')
    edges=sum(sum((points[i][k]-points[j][k])**2 for k in range(3)) for i in range(4) for j in range(i))
    return volume,12*(3*volume)**(2/3)/edges

def stress_records(rows,element_ids):
    stresses=[];seen=set()
    for row in rows:
        if len(row)!=8 or not all(math.isfinite(x) for x in row):raise ValueError('Invalid integration-point stress values')
        eid,ip=int(row[0]),int(row[1])
        if row[0]!=eid or row[1]!=ip or eid not in element_ids or ip not in (1,2,3,4) or (eid,ip) in seen:raise ValueError('Invalid or duplicate stress identity')
        seen.add((eid,ip));sx,sy,sz,xy,xz,yz=row[2:8]
        vm=math.sqrt(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(xy*xy+xz*xz+yz*yz))
        if not math.isfinite(vm):raise ValueError('Non-finite stress magnitude')
        stresses.append((vm,eid,ip))
    if seen!={(eid,ip) for eid in element_ids for ip in (1,2,3,4)}:raise ValueError('Incomplete C3D10 integration-point stresses')
    return stresses

def displacement_records(rows,node_ids):
    """Require one finite three-component displacement per reported mesh node."""
    displacements={}
    for row in rows:
        if len(row)!=4 or not all(math.isfinite(value) for value in row):
            raise ValueError('Invalid nodal displacement values')
        node=int(row[0])
        if row[0]!=node or node not in node_ids or node in displacements:
            raise ValueError('Invalid or duplicate displacement identity')
        displacements[node]=row[1:4]
    return displacements

def regional_peaks(stresses,centers):
    def distance(point,bounds):
        return math.sqrt(sum((value-min(max(value,low),high))**2 for value,(low,high) in zip(point,bounds)))
    distances={eid:min(distance(center,((0,0),(0,30),(3.5,40))),distance(center,((55,60),(0,30),(3.5,3.5)))) for eid,center in centers.items()}
    rows=[]
    for gap in (1,2,3):
        included=[row for row in stresses if distances[row[1]]>=gap]
        peak=max(included) if included else None
        rows.append({'centroid_exclusion_distance_mm':gap,'included_elements':len({row[1] for row in included}),'maximum_von_mises_MPa':peak[0] if peak else None,'peak_element_id':peak[1] if peak else None})
    return rows

def diagnose(archive,mesh_name="mesh-1.5"):
    if mesh_name not in ("mesh-2.5","mesh-1.8","mesh-1.5"):raise ValueError("Unsupported bracket mesh")
    with zipfile.ZipFile(archive) as z:
        deck=z.read(mesh_name+'/bracket.inp').decode();data=z.read(mesh_name+'/bracket.dat').decode()
    nodes={};elements={};loads=[];material=None;section=None
    for line in deck.splitlines():
        if line.startswith('*'):section='nodes' if line=='*NODE' else 'elements' if line.startswith('*ELEMENT,') else 'loads' if line=='*CLOAD' else 'elastic' if line=='*ELASTIC' else None
        elif section=='nodes':values=line.split(',');nodes[int(values[0])]=list(map(float,values[1:4]))
        elif section=='elements':values=list(map(int,line.split(',')));elements[values[0]]=values[1:]
        elif section=='loads':values=line.split(',');loads.append((int(values[0]),int(values[1]),float(values[2])))
        elif section=='elastic':material=tuple(map(float,line.split(',')[:2]))
    quality={eid:tetra_quality([nodes[n] for n in e[:4]]) for eid,e in elements.items()}
    stress_rows=table(data,'stresses');stresses=stress_records(stress_rows,set(elements))
    if material is None or not loads:raise ValueError('Missing elastic material or applied loads')
    energy=sum(strain_energy_density(row[2:8],*material)*quality[int(row[0])][0]/4 for row in stress_rows)
    displacements=displacement_records(table(data,'displacements'),set(nodes))
    if any(node not in displacements or dof not in (1,2,3) or not math.isfinite(force) for node,dof,force in loads):raise ValueError('Incomplete load displacement data')
    work=sum(force*displacements[node][dof-1] for node,dof,force in loads)
    if not math.isfinite(work) or work<=0:raise ValueError('Invalid external work')
    energy_error=abs(energy/(work/2)-1)
    centers={eid:[sum(nodes[n][j] for n in e[:4])/4 for j in range(3)] for eid,e in elements.items()}
    peaks=[]
    for stress,eid,ip in sorted(stresses,reverse=True)[:10]:
        center=[sum(nodes[n][j] for n in elements[eid][:4])/4 for j in range(3)]
        peaks.append({'von_mises_MPa':stress,'element_id':eid,'integration_point':ip,'element_corner_centroid_mm':center,'element_volume_mm3':quality[eid][0],'corner_mean_ratio_quality':quality[eid][1]})
    qualities=sorted(q for volume,q in quality.values())
    return {'energy_consistency':{'strain_energy_N_mm':energy,'half_load_work_N_mm':work/2,'relative_error':energy_error,'passes_demo_tolerance':energy_error<.001,'relative_tolerance':.001,'method':'Four equal-weight C3D10 integration points; isotropic linear elasticity; zero prescribed support displacement'},'regional_peaks':regional_peaks(stresses,centers),'regional_note':'Element centroid exclusion from nominal rear clamp and load rectangles; not exact integration-point distance, convergence or an allowable','elements':len(elements),'minimum_corner_quality':qualities[0],'one_percentile_corner_quality':qualities[int(.01*(len(qualities)-1))],'median_corner_quality':qualities[len(qualities)//2],'top_integration_point_stresses':peaks,'limitations':['Reported locations are element corner centroids, not exact integration-point coordinates','Quality describes straight corner tetrahedra, not a full quadratic Jacobian assessment','Peak location and quality do not establish stress convergence or physical validity']}

def regional_refinement(archive,fine=None):
    studies=[]
    for size in (2.5,1.8,1.5):
        result=fine if size==1.5 and fine is not None else diagnose(archive,'mesh-'+str(size))
        studies.append({'target_size_mm':size,'elements':result['elements'],'global_peak_MPa':result['top_integration_point_stresses'][0]['von_mises_MPa'],'regional_peaks':result['regional_peaks'],'energy_consistency':result['energy_consistency']})
    changes=[]
    for previous,current in zip(studies[-2]['regional_peaks'],studies[-1]['regional_peaks']):
        a,b=previous['maximum_von_mises_MPa'],current['maximum_von_mises_MPa']
        changes.append({'centroid_exclusion_distance_mm':current['centroid_exclusion_distance_mm'],'relative_last_peak_change':abs(b/a-1) if a and b is not None else None})
    a,b=(study['energy_consistency']['strain_energy_N_mm'] for study in studies[-2:])
    energy_change=abs(b/a-1) if a>0 else None
    return {'last_energy_change':energy_change,'mesh_study':studies,'last_changes':changes,'status':'measured_not_stress_convergence_acceptance'}
