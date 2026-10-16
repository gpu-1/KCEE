"""Deterministic axial-ray bore checks on source triangles and actual fluid wall faces."""
import math,re,struct
from pathlib import Path
from kcee.bracket_flow import mesh_list
HOLES=[('base-1',2,(.033,.015)),('base-2',2,(.048,.015)),('upright-1',0,(.015,.016)),('upright-2',0,(.015,.030))]
OFFSETS=[(i*.0005,j*.0005) for j in range(-4,5) for i in range(-4,5) if (i*.0005)**2+(j*.0005)**2<=.00225**2]
OFFSETS += [(0.003*math.cos(2*math.pi*i/16),0.003*math.sin(2*math.pi*i/16)) for i in range(16)]
def source_triangles(raw):
 count=struct.unpack_from('<I',raw,80)[0]
 if len(raw)!=84+50*count:raise ValueError('Invalid source surface')
 return [[tuple(v*.001 for v in values[k:k+3]) for k in (3,6,9)] for values in (struct.unpack_from('<12fH',raw,84+i*50) for i in range(count))]
def wall_triangles(root):
 root=Path(root);n,text=mesh_list(root/'points');points=[tuple(map(float,p.split())) for p in re.findall(r'\(([^()]*)\)',text)]
 nf,text=mesh_list(root/'faces');faces=[list(map(int,p.split())) for p in re.findall(r'\d+\(([^()]*)\)',text)]
 boundary=(root/'boundary').read_text();patch=re.search(r'\bbracket\s*\{([^{}]*)\}',boundary,re.S)
 if not patch:raise ValueError('Missing actual bracket wall patch')
 count=int(re.search(r'nFaces\s+(\d+)',patch[1])[1]);start=int(re.search(r'startFace\s+(\d+)',patch[1])[1])
 if len(points)!=n or len(faces)!=nf or count<1 or start+count>nf:raise ValueError('Invalid wall addressing')
 result=[]
 for face in faces[start:start+count]:
  for i in range(1,len(face)-1):result.append([points[k] for k in (face[0],face[i],face[i+1])])
 return result

def open_rays(triangles,axis,center):
 transverse=[i for i in range(3) if i!=axis];candidates=[]
 for tri in triangles:
  if any(max(v[k] for v in tri)<center[j]-.003 or min(v[k] for v in tri)>center[j]+.003 for j,k in enumerate(transverse)):continue
  if max(v[axis] for v in tri)<-.001 or min(v[axis] for v in tri)>.0045:continue
  a,b,c=tri;x1,y1=(b[k]-a[k] for k in transverse);x2,y2=(c[k]-a[k] for k in transverse);det=x1*y2-x2*y1
  if abs(det)>1e-18:candidates.append((a,b,c,x1,y1,x2,y2,det))
 rays=[]
 for dx,dy in OFFSETS:
  point=(center[0]+dx,center[1]+dy);blocked=False
  for a,b,c,x1,y1,x2,y2,det in candidates:
   px=point[0]-a[transverse[0]];py=point[1]-a[transverse[1]];u=(px*y2-x2*py)/det;v=(x1*py-px*y1)/det
   if u>=-1e-9 and v>=-1e-9 and u+v<=1+1e-9:
    position=a[axis]+u*(b[axis]-a[axis])+v*(c[axis]-a[axis])
    if -.001<=position<=.0045:blocked=True;break
  rays.append(not blocked)
 return rays

def bore_checks(raw,mesh_root):
 source=source_triangles(raw);wall=wall_triangles(mesh_root);rows=[];center_index=OFFSETS.index((0.,0.))
 for name,axis,center in HOLES:
  a=open_rays(source,axis,center);b=open_rays(wall,axis,center);source_open=sum(a);blocked=sum(x and not y for x,y in zip(a,b));unexpected=sum(not x and y for x,y in zip(a,b))
  rows.append({'hole':name,'axis':'xyz'[axis],'sample_count':len(a),'source_open_rays':source_open,'mesh_open_rays':sum(b),'source_open_fraction':source_open/len(a),'mesh_open_fraction':sum(b)/len(b),'source_open_rays_blocked_by_mesh':blocked,'blocked_source_open_fraction':blocked/source_open if source_open else None,'unexpected_open_rays':unexpected,'source_center_open':a[center_index],'mesh_center_open':b[center_index],'passes_sampling_gate':source_open>0 and a[center_index] and b[center_index] and blocked/source_open<=.05 and unexpected/max(1,len(a)-source_open)<=.05})
 return {'method':'Axial line-segment intersection against source STL and triangulated actual bracket boundary faces. No cell-centre occupancy proxy.','ray_radius_m':.00225,'outer_control_ring_m':.003,'outer_control_rays':16,'ray_spacing_m':.0005,'axial_segment_m':[-.001,.0045],'rows':rows,'sampling_gate':{'maximum_blocked_source_open_fraction':.05,'maximum_unexpected_open_fraction_of_source_blocked':.05,'center_must_remain_open':True},'all_pass':all(r['passes_sampling_gate'] for r in rows),'limits':'Finite ray samples inside a 2.25 mm radius do not establish exact bore area, minimum diameter, hydraulic resistance or manufacturing acceptance. Facets are triangulated; edge hits count as blocked.'}
