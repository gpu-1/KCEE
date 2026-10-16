"""Volume moments of the oriented, triangulated saved polyMesh boundary.

Polygon faces are triangulated from their vertex mean; each triangle forms a
signed tetrahedron with a cell-local reference. This handles concave cells
without replacing signed volumes with absolute values.
"""
import math,re
from pathlib import Path

def volume_centres(root,count):
 from kcee.bracket_flow import mesh_list,cell_positions
 root=Path(root);references=cell_positions(root,count)
 np,raw=mesh_list(root/'points');points=[tuple(map(float,v.split())) for v in re.findall(r'\(([^()]*)\)',raw)]
 nf,raw=mesh_list(root/'faces');faces=[list(map(int,v.split())) for v in re.findall(r'\d+\(([^()]*)\)',raw)]
 no,raw=mesh_list(root/'owner');owners=list(map(int,raw.split()));nn,raw=mesh_list(root/'neighbour');neighbours=list(map(int,raw.split()))
 if len(points)!=np or len(faces)!=nf or len(owners)!=nf or no!=nf or len(neighbours)!=nn or nn>nf:raise ValueError('Invalid centroid mesh addressing')
 volumes=[0.]*count;moments=[[0.,0.,0.] for _ in range(count)]
 for face_index,face in enumerate(faces):
  if len(face)<3 or any(v<0 or v>=np for v in face):raise ValueError('Invalid centroid face')
  vertices=[points[v] for v in face];fc=tuple(sum(v[k] for v in vertices)/len(vertices) for k in range(3))
  cells=[(owners[face_index],1)]
  if face_index<nn:cells.append((neighbours[face_index],-1))
  for cell,sign in cells:
   if not 0<=cell<count:raise ValueError('Invalid centroid cell')
   ref=references[cell];a=[fc[k]-ref[k] for k in range(3)]
   for i,b0 in enumerate(vertices):
    c0=vertices[(i+1)%len(vertices)];b=[b0[k]-ref[k] for k in range(3)];c=[c0[k]-ref[k] for k in range(3)]
    volume=sign*(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
    volumes[cell]+=volume
    for k in range(3):moments[cell][k]+=volume*(a[k]+b[k]+c[k])/4
 if any(not math.isfinite(v) or v<=1e-18 for v in volumes):raise ValueError('Nonpositive or nonfinite triangulated cell volume')
 centres=[tuple(ref[k]+moment[k]/volume for k in range(3)) for ref,moment,volume in zip(references,moments,volumes)]
 if not all(math.isfinite(v) for c in centres for v in c):raise ValueError('Nonfinite volume centroid')
 shifts=[math.dist(a,b) for a,b in zip(centres,references)]
 audit={'method':'oriented polygon-face fan signed tetrahedron volume moments; face fans use vertex means','cell_count':count,'minimum_cell_volume_m3':min(volumes),'total_fluid_volume_m3':sum(volumes),'maximum_vertex_mean_to_volume_centroid_m':max(shifts),'rms_vertex_mean_to_volume_centroid_m':math.sqrt(sum(x*x for x in shifts)/count),'position_basis':'triangulated_polyhedral_volume_centroids','limits':['Centroids refer to the triangulated saved polyhedron. Warped-face triangulation may differ from OpenFOAM native face moments.','This independent reconstruction is not a solver-native C field or proof of geometric/engineering accuracy.']}
 return centres,references,audit
