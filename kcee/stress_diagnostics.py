"""Archived integration-point peaks and corner tetrahedron quality diagnostics."""
import math,zipfile
from kcee.fea import table

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

def diagnose(archive):
    with zipfile.ZipFile(archive) as z:
        deck=z.read('mesh-1.5/bracket.inp').decode();data=z.read('mesh-1.5/bracket.dat').decode()
    nodes={};elements={};section=None
    for line in deck.splitlines():
        if line.startswith('*'):section='nodes' if line=='*NODE' else 'elements' if line.startswith('*ELEMENT,') else None
        elif section=='nodes':values=line.split(',');nodes[int(values[0])]=list(map(float,values[1:4]))
        elif section=='elements':values=list(map(int,line.split(',')));elements[values[0]]=values[1:]
    quality={eid:tetra_quality([nodes[n] for n in e[:4]]) for eid,e in elements.items()}
    stresses=stress_records(table(data,'stresses'),set(elements))
    centers={eid:[sum(nodes[n][j] for n in e[:4])/4 for j in range(3)] for eid,e in elements.items()}
    peaks=[]
    for stress,eid,ip in sorted(stresses,reverse=True)[:10]:
        center=[sum(nodes[n][j] for n in elements[eid][:4])/4 for j in range(3)]
        peaks.append({'von_mises_MPa':stress,'element_id':eid,'integration_point':ip,'element_corner_centroid_mm':center,'element_volume_mm3':quality[eid][0],'corner_mean_ratio_quality':quality[eid][1]})
    qualities=sorted(q for volume,q in quality.values())
    return {'regional_peaks':regional_peaks(stresses,centers),'regional_note':'Element centroid exclusion from nominal rear clamp and load rectangles; not exact integration-point distance, convergence or an allowable','elements':len(elements),'minimum_corner_quality':qualities[0],'one_percentile_corner_quality':qualities[int(.01*(len(qualities)-1))],'median_corner_quality':qualities[len(qualities)//2],'top_integration_point_stresses':peaks,'limitations':['Reported locations are element corner centroids, not exact integration-point coordinates','Quality describes straight corner tetrahedra, not a full quadratic Jacobian assessment','Peak location and quality do not establish stress convergence or physical validity']}
