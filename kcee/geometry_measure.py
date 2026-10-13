"""STL plane sections for nominal default bracket hole measurements."""
import math,struct
from pathlib import Path

def hole_sections(path,section_mm=1.75):
    if not math.isfinite(section_mm) or not 0<section_mm<3.5:raise ValueError('Section must lie inside the default bracket thickness')
    raw=Path(path).read_bytes();count=struct.unpack_from('<I',raw,80)[0]
    if len(raw)!=84+50*count:raise ValueError('Invalid binary STL')
    triangles=[]
    for i in range(count):
        values=struct.unpack_from('<12fH',raw,84+50*i);triangles.append([values[j:j+3] for j in (3,6,9)])
    rows=[]
    for name,axis,center in [('base-1',2,(33,15)),('base-2',2,(48,15)),('upright-1',0,(15,16)),('upright-2',0,(15,30))]:
        transverse=[j for j in range(3) if j!=axis];segments=[]
        for triangle in triangles:
            hits=[]
            for a,b in zip(triangle,triangle[1:]+triangle[:1]):
                da,db=a[axis]-section_mm,b[axis]-section_mm
                if da*db<0:
                    t=da/(da-db);hits.append(tuple(a[j]+t*(b[j]-a[j])-center[k] for k,j in enumerate(transverse)))
                elif da==0:hits.append(tuple(a[j]-center[k] for k,j in enumerate(transverse)))
            hits=list(dict.fromkeys(hits))
            if len(hits)==2 and all(math.hypot(*p)<4 for p in hits):segments.append(hits)
        if not segments:raise ValueError('No bore section found: '+name)
        radii=[]
        for a,b in segments:
            u=[b[j]-a[j] for j in range(2)];den=sum(x*x for x in u)
            t=max(0,min(1,-sum(a[j]*u[j] for j in range(2))/den)) if den else 0
            radii.extend((math.hypot(*a),math.hypot(*b),math.hypot(*(a[j]+t*u[j] for j in range(2)))))
        rows.append({'hole':name,'section_axis':axis,'section_mm':section_mm,'nominal_diameter_mm':5,'minimum_radial_diameter_mm':2*min(radii),'maximum_radial_diameter_mm':2*max(radii),'section_segments':len(segments)})
    return rows
