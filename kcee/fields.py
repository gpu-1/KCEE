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
    displacement={};active=False
    for line in frd.splitlines():
        if line.startswith(' -4'):active=line[5:17].strip()=='DISP'
        elif active and line.startswith(' -3'):active=False
        elif active and line.startswith(' -1'):
            displacement[int(line[3:13])]=[float(line[start:start+12]) for start in (13,25,37)]
    faces={}
    # CalculiX C3D10 corner and edge ordering; outward orientation for positive tetrahedra.
    for e in elements:
        for indices in ((0,2,1,6,5,4),(0,1,3,4,8,7),(1,2,3,5,9,8),(2,0,3,6,7,9)):
            face=[e[i] for i in indices];key=tuple(sorted(face[:3]))
            if key in faces:faces[key]=None
            else:faces[key]=face
    triangles=[]
    for face in faces.values():
        if face is None:continue
        a,b,c,ab,bc,ca=face
        triangles.extend(((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)))
    ids=sorted({n for t in triangles for n in t});lookup={n:i for i,n in enumerate(ids)}
    if not ids or any(n not in displacement for n in ids):raise ValueError('Incomplete solver displacement field')
    positions=[nodes[n] for n in ids];vectors=[displacement[n] for n in ids]
    if not all(math.isfinite(x) for p in positions+vectors for x in p):raise ValueError('Non-finite solver field')
    return {'schema_version':1,'units':'mm','mesh':'fine C3D10 boundary, four linear triangles per quadratic face','positions':positions,'displacements':vectors,'triangles':[[lookup[n] for n in t] for t in triangles],'maximum_displacement_mm':max(math.sqrt(sum(x*x for x in p)) for p in vectors)}
