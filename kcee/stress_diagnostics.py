"""Archived integration-point peaks and corner tetrahedron quality diagnostics."""
import math,zipfile
from kcee.fea import table

def tetra_quality(points):
    a,b,c,d=points;u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];w=[d[i]-a[i] for i in range(3)]
    volume=(u[0]*(v[1]*w[2]-v[2]*w[1])-u[1]*(v[0]*w[2]-v[2]*w[0])+u[2]*(v[0]*w[1]-v[1]*w[0]))/6
    if volume<=0:raise ValueError('Non-positive tetrahedron volume')
    edges=sum(sum((points[i][k]-points[j][k])**2 for k in range(3)) for i in range(4) for j in range(i))
    return volume,12*(3*volume)**(2/3)/edges

def diagnose(archive):
    with zipfile.ZipFile(archive) as z:
        deck=z.read('mesh-1.5/bracket.inp').decode();data=z.read('mesh-1.5/bracket.dat').decode()
    nodes={};elements={};section=None
    for line in deck.splitlines():
        if line.startswith('*'):section='nodes' if line=='*NODE' else 'elements' if line.startswith('*ELEMENT,') else None
        elif section=='nodes':values=line.split(',');nodes[int(values[0])]=list(map(float,values[1:4]))
        elif section=='elements':values=list(map(int,line.split(',')));elements[values[0]]=values[1:]
    quality={eid:tetra_quality([nodes[n] for n in e[:4]]) for eid,e in elements.items()}
    stresses=[]
    for row in table(data,'stresses'):
        sx,sy,sz,xy,xz,yz=row[2:8];vm=math.sqrt(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(xy*xy+xz*xz+yz*yz));stresses.append((vm,int(row[0]),int(row[1])))
    peaks=[]
    for stress,eid,ip in sorted(stresses,reverse=True)[:10]:
        center=[sum(nodes[n][j] for n in elements[eid][:4])/4 for j in range(3)]
        peaks.append({'von_mises_MPa':stress,'element_id':eid,'integration_point':ip,'element_corner_centroid_mm':center,'element_volume_mm3':quality[eid][0],'corner_mean_ratio_quality':quality[eid][1]})
    qualities=sorted(q for volume,q in quality.values())
    return {'elements':len(elements),'minimum_corner_quality':qualities[0],'one_percentile_corner_quality':qualities[int(.01*(len(qualities)-1))],'median_corner_quality':qualities[len(qualities)//2],'top_integration_point_stresses':peaks,'limitations':['Reported locations are element corner centroids, not exact integration-point coordinates','Quality describes straight corner tetrahedra, not a full quadratic Jacobian assessment','Peak location and quality do not establish stress convergence or physical validity']}
