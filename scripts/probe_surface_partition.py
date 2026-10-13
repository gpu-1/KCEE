"""Run inside the structural image: read-only STL surface partition diagnostics."""
import argparse,hashlib,json,math,tempfile
from pathlib import Path
from urllib.request import urlopen
import gmsh
parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);parser.add_argument('--base-url',default='http://api:8000');args=parser.parse_args()
from uuid import UUID
run_id=str(UUID(args.run_id))
def read(path):
 with urlopen(args.base_url+path,timeout=15) as response:return response.read()
record=json.loads(read('/runs/'+run_id))
if json.loads(read('/runs/'+run_id+'/verify'))['integrity']!='verified':raise ValueError('Run integrity failure')
raw=read('/artifacts/'+run_id+'/bracket.stl');digest=hashlib.sha256(raw).hexdigest()
if digest!=record['manifest']['artifacts']['bracket.stl']:raise ValueError('STL hash mismatch')
report={'run_id':run_id,'source_stl_sha256':digest,'gmsh_version':None,'partitions':[]}
with tempfile.TemporaryDirectory() as tmp:
 path=Path(tmp)/'source.stl';path.write_bytes(raw)
 for angle in (20,30):
  gmsh.initialize();gmsh.option.setNumber('General.Terminal',0)
  try:
   gmsh.merge(str(path));gmsh.model.mesh.classifySurfaces(math.radians(angle),True,True,math.pi)
   candidates=[];planes=[]
   for dim,tag in gmsh.model.getEntities(2):
    tags,coords,_=gmsh.model.mesh.getNodes(2,tag,True);points=[coords[i:i+3] for i in range(0,len(coords),3)]
    if not points:continue
    zs=[p[2] for p in points]
    if max(zs)-min(zs)<1e-4 and abs(sum(zs)/len(zs)-3.5)<.05:planes.append(tag)
    if any(p[0]>=55 and abs(p[2]-3.5)<.05 for p in points):candidates.append({'surface_id':tag,'nodes':len(points),'z_min_mm':min(zs),'z_max_mm':max(zs),'z_span_mm':max(zs)-min(zs)})
   report['gmsh_version']=gmsh.option.getString('General.Version');report['partitions'].append({'angle_degrees':angle,'planar_top_surface_ids':planes,'top_region_candidate_surfaces':candidates})
  finally:gmsh.finalize()
report['limitations']=['Surface membership includes boundary nodes','This probes classification only; no solver geometry is changed','Planarity threshold is a diagnostic 0.0001 mm, not manufacturing acceptance']
print(json.dumps(report,indent=2))
