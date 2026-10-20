"""Source-bound display mesh for verified regional wall-load diagnostics."""
import hashlib,json,math,re,tempfile,zipfile
from pathlib import Path
from kcee.regional_forces import audit,region,NAMES
from kcee.native_forces import source_members,unpack,boundary_values,mesh_patch
VERSION='native-regional-wall-view-v1'
def triangulate(points,faces,wall,centres,expected_counts):
 if not 0<len(wall)<=100000 or len(wall)!=len(centres) or len(expected_counts)!=len(NAMES):raise ValueError('Invalid regional wall size')
 positions=[];triangles=[];regions=[];identities=[];mapping={};counts=[0]*len(NAMES);seen=set()
 for (face,owner,sf),c in zip(wall,centres):
  if face in seen or not 0<=face<len(faces):raise ValueError('Invalid wall face identity')
  seen.add(face);polygon=faces[face];rid=region(c);counts[rid]+=1
  if not 3<=len(polygon)<=32 or len(set(polygon))!=len(polygon):raise ValueError('Invalid wall polygon')
  vertices=[]
  for v in polygon:
   if not 0<=v<len(points) or len(points[v])!=3 or not all(math.isfinite(x) for x in points[v]):raise ValueError('Invalid wall vertex')
   if v not in mapping:mapping[v]=len(positions);positions.append([x*1000 for x in points[v]])
   vertices.append(mapping[v])
  for i in range(1,len(vertices)-1):
   triangles.append([vertices[0],vertices[i],vertices[i+1]]);regions.append(rid);identities.append(face)
   if len(triangles)>250000:raise ValueError('Regional display mesh exceeds limit')
 if counts!=expected_counts:raise ValueError('Display face regions differ from integrated regions')
 return {'positions_mm':positions,'triangles':triangles,'triangle_regions':regions,'triangle_source_faces':identities,'region_face_counts':counts,'wall_faces':len(wall),'units':'mm','limits':'Fan triangles display the saved fluid wall polygons. Every triangle inherits its parent native face-centre region. Triangles do not redefine integration areas, stress values or exact bore boundaries. Colors identify neighborhoods, not stress or engineering acceptance.'}

def surface(root,identifier,source_id,registry):
 from kcee.bracket_flow import mesh_list
 root=Path(root);registry.verify(root,identifier);saved=json.loads((root/str(identifier)/'cfd.json').read_text())
 if str(source_id) not in [s['run_id'] for s in saved.get('studies',[])]:raise ValueError('Select a source case from this native report')
 data=audit(root,identifier,registry);case=next(c for c in data['cases'] if c['run_id']==str(source_id));p=root/str(source_id);flow=json.loads((p/'cfd.json').read_text());time=3000 if 'force_history' in flow else 1500
 members=source_members((p/'cfd-artifacts.zip').read_bytes(),time)
 with zipfile.ZipFile(root/str(identifier)/'native-forces.zip') as z:files=unpack(z.read(str(source_id)+'.zip'))
 with tempfile.TemporaryDirectory() as tmp:
  path=Path(tmp)
  for n,v in members.items():q=path/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(v)
  meshroot=path/'constant/polyMesh';wall=mesh_patch(meshroot,'bracket');centres=boundary_values(files['wall-centres.foam'],len(wall),3)
  _,text=mesh_list(meshroot/'points');points=[list(map(float,p.split())) for p in re.findall(r'\(([^()]*)\)',text)]
  _,text=mesh_list(meshroot/'faces');faces=[list(map(int,p.split())) for p in re.findall(r'\d+\(([^()]*)\)',text)]
  display=triangulate(points,faces,wall,centres,[r['faces'] for r in case['regions']])
 return {'schema':VERSION,'report_run_id':str(identifier),'report_manifest_sha256':data['report_manifest_sha256'],'source':case,'regional_method':data['schema'],'regional_implementation_sha256':data['implementation_sha256'],'display_implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'regions':list(NAMES),'surface':display,'checks':{'native_evidence_reproduced':True,'region_face_counts_match':True},'engineering_acceptance':'pending'}
