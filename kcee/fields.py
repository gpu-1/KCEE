"""Derive a quadratic surface preview from immutable CalculiX artifacts."""
import math,zipfile

def displacement_surface(archive):
    with zipfile.ZipFile(archive) as z:
        inp=z.read('mesh-1.5/bracket.inp').decode()
        frd=z.read('mesh-1.5/bracket.frd').decode()
    nodes={};elements=[];section=None
    for line in inp.splitlines():
        if line.startswith('*'):
            section='nodes' if line=='*NODE' else 'elements' if line.startswith('*ELEMENT,') else None
        elif section=='nodes':
            values=line.split(',');nodes[int(values[0])]=list(map(float,values[1:4]))
        elif section=='elements':elements.append(list(map(int,line.split(',')[1:])))
    displacement={};stress={};active=None
    for line in frd.splitlines():
        if line.startswith(' -4'):active=line[5:17].strip()
        elif active and line.startswith(' -3'):active=None
        elif active in ('DISP','STRESS') and line.startswith(' -1'):
            values=[float(line[start:start+12]) for start in (range(13,85,12) if active=='STRESS' else (13,25,37))]
            if active=='DISP':displacement[int(line[3:13])]=values
            else:
                sx,sy,sz,xy,yz,zx=values
                stress[int(line[3:13])]=math.sqrt(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(xy*xy+yz*yz+zx*zx))
    faces={};face_counts={};face_edges={};face_orientation={}
    # CalculiX C3D10 corner and edge ordering; outward orientation for positive tetrahedra.
    for e in elements:
        if len(e)!=10 or len(set(e))!=10 or any(n not in nodes for n in e):raise ValueError('Invalid C3D10 connectivity')
        a,b,c,d=[nodes[n] for n in e[:4]]
        u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];w=[d[i]-a[i] for i in range(3)]
        determinant=u[0]*(v[1]*w[2]-v[2]*w[1])-u[1]*(v[0]*w[2]-v[2]*w[0])+u[2]*(v[0]*w[1]-v[1]*w[0])
        if not math.isfinite(determinant) or determinant<=0:raise ValueError('Non-positive tetrahedron volume')
        for indices in ((0,2,1,6,5,4),(0,1,3,4,8,7),(1,2,3,5,9,8),(2,0,3,6,7,9)):
            face=[e[i] for i in indices];key=tuple(sorted(face[:3]))
            face_counts[key]=face_counts.get(key,0)+1
            if face_counts[key]>2:raise ValueError('Non-manifold volume mesh')
            edges={tuple(sorted((face[i],face[(i+1)%3]))):face[3+i] for i in range(3)}
            if key in faces:
                if edges!=face_edges[key]:raise ValueError('Shared-face midside mismatch')
                previous=face_orientation[key];reverse=[previous[0],previous[2],previous[1]]
                if not any(face[:3]==reverse[i:]+reverse[:i] for i in range(3)):raise ValueError('Shared-face orientation mismatch')
                faces[key]=None
            else:
                face_edges[key]=edges;face_orientation[key]=face[:3]
                faces[key]=face
    triangles=[]
    for face in faces.values():
        if face is None:continue
        a,b,c,ab,bc,ca=face
        triangles.extend(((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)))
    ids=sorted({n for t in triangles for n in t});lookup={n:i for i,n in enumerate(ids)}
    if not ids or any(n not in displacement for n in ids):raise ValueError('Incomplete solver displacement field')
    positions=[nodes[n] for n in ids];vectors=[displacement[n] for n in ids]
    if not all(math.isfinite(x) for p in positions+vectors for x in p):raise ValueError('Non-finite solver field')
    if stress and any(n not in stress for n in ids):raise ValueError('Incomplete solver stress field')
    stress_values=[stress[n] for n in ids] if stress else None
    if stress_values is not None and not all(math.isfinite(x) for x in stress_values):raise ValueError('Non-finite stress field')
    return {'von_mises_MPa':stress_values,'maximum_surface_von_mises_MPa':max(stress_values) if stress_values else None,'stress_method':'CalculiX extrapolated/averaged nodal stresses; not integration-point peaks or converged allowables','schema_version':1,'units':'mm','mesh':'fine C3D10 boundary, four linear triangles per quadratic face','positions':positions,'displacements':vectors,'triangles':[[lookup[n] for n in t] for t in triangles],'maximum_displacement_mm':max(math.sqrt(sum(x*x for x in p)) for p in vectors)}
