"""Positive-weight, wall-visible tetrahedral interpolation of saved cell fields.

Position basis is supplied by the caller; it is recorded for every probe.
No nearest-cell fallback and no extrapolation outside a supporting tetrahedron.
"""
import itertools, math
from kcee.flow_bores import wall_triangles
PROBES=[('upstream',(-.03,.015,.020)),('wake',(.08,.015,.020)),('far wake',(.12,.015,.020)),('above',(.03,.015,.060)),('below',(.03,.015,-.020)),('base bore 1',(.033,.015,.00175)),('base bore 2',(.048,.015,.00175)),('upright bore 1',(.00175,.015,.016)),('upright bore 2',(.00175,.015,.030))]
POSITION=('x_m','y_m','z_m');VALUES=('u_m_s','v_m_s','w_m_s','p_kinematic_m2_s2')
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def weights(point,vertices):
 a,b,c=(sub(vertices[i],vertices[3]) for i in range(3));q=sub(point,vertices[3]);det=dot(a,cross(b,c))
 scale=max(math.sqrt(dot(v,v)) for v in (a,b,c))
 if abs(det)<=1e-10*scale**3:return None
 w=[dot(q,cross(b,c))/det,dot(a,cross(q,c))/det,dot(a,cross(b,q))/det];w.append(1-sum(w))
 return w if min(w)>=-1e-10 and max(w)<=1+1e-10 else None

def blocked(point,end,triangles):
 direction=sub(end,point)
 for tri,lo,hi in triangles:
  if any(max(point[k],end[k])<lo[k]-1e-12 or min(point[k],end[k])>hi[k]+1e-12 for k in range(3)):continue
  a,b,c=tri;e1=sub(b,a);e2=sub(c,a);h=cross(direction,e2);det=dot(e1,h)
  if abs(det)<1e-18:continue
  s=sub(point,a);u=dot(s,h)/det
  if u < -1e-9 or u > 1+1e-9:continue
  q=cross(s,e1);v=dot(direction,q)/det;t=dot(e2,q)/det
  if v>=-1e-9 and u+v<=1+1e-9 and 1e-8<t<1-1e-8:return True
 return False

def interpolate(field,point,triangles=()):
 if not field or not all(math.isfinite(v) for v in point):raise ValueError('Invalid probe field or point')
 ordered=sorted(enumerate(field),key=lambda item:sum((item[1][k]-v)**2 for k,v in zip(POSITION,point)))[:256]
 candidates=[];octants={}
 for index,row in ordered:
  pos=tuple(row[k] for k in POSITION)
  octant=tuple(pos[k]>=point[k] for k in range(3))
  if octants.get(octant,0)>=2:continue
  if not blocked(point,pos,triangles):
   candidates.append((index,row,pos));octants[octant]=octants.get(octant,0)+1
  if len(candidates)==16:break
 for support in itertools.combinations(candidates,4):
  w=weights(point,[s[2] for s in support])
  if w is None:continue
  # Remove tiny round-off negatives; positive normalized weights prevent overshoot.
  w=[max(0.,v) for v in w];total=sum(w);w=[v/total for v in w]
  values=[sum(v*s[1][key] for v,s in zip(w,support)) for key in VALUES]
  if not all(math.isfinite(v) for v in values):raise ValueError('Nonfinite interpolated probe')
  return {'available':True,'requested_position_m':list(point),'sample_position_m':list(point),'distance_m':0.,'method':'wall-visible positive tetrahedral interpolation','support_cell_indices':[s[0] for s in support],'support_positions_m':[list(s[2]) for s in support],'weights':w,'support_distances_m':[math.dist(point,s[2]) for s in support],'maximum_support_distance_m':max(math.dist(point,s[2]) for s in support),'velocity_m_s':values[:3],'speed_m_s':math.sqrt(sum(v*v for v in values[:3])),'kinematic_pressure_m2_s2':values[3]}
 raise ValueError('No enclosing wall-visible tetrahedron for fixed probe '+str(point))

def sample_probes(field,mesh_root,position_basis="mesh_vertex_averages"):
 triangles=[(t,tuple(min(p[k] for p in t) for k in range(3)),tuple(max(p[k] for p in t) for k in range(3))) for t in wall_triangles(mesh_root)]
 rows=[]
 for name,point in PROBES:
  try:rows.append(dict(interpolate(field,point,triangles),name=name,position_basis=position_basis))
  except ValueError as error:rows.append({'name':name,'requested_position_m':list(point),'available':False,'reason':str(error)})
 return rows
