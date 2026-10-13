"""Read-only source/mesh load-area tolerance sensitivity; changes no study settings."""
import argparse,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.fields import displacement_surface
from kcee.surface_load import strip_weights
from kcee.provenance import verify_directory
parser=argparse.ArgumentParser();parser.add_argument('directory');parser.add_argument('--manifest-sha256',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
directory=Path(args.directory);manifest,digest=verify_directory(directory,expected_digest=args.manifest_sha256)
raw=(directory/'bracket.stl').read_bytes();source=[]
for i in range(struct.unpack_from('<I',raw,80)[0]):
 values=struct.unpack_from('<12fH',raw,84+50*i);source.append([values[j:j+3] for j in (3,6,9)])
field=displacement_surface(directory/'fea-artifacts.zip');mesh=[[field['positions'][i] for i in triangle] for triangle in field['triangles']]
rows=[]
for tolerance in (.05,.1,.2,.35):
 areas=[]
 for triangles in (source,mesh):
  area=sum(strip_weights(corners)[0] for corners in triangles if max(abs(p[2]-3.5) for p in corners)<=tolerance);areas.append(area)
 rows.append({'top_face_tolerance_mm':tolerance,'source_strip_area_mm2':areas[0],'mesh_strip_area_mm2':areas[1],'relative_area_error':abs(areas[1]/areas[0]-1)})
report={'run_id':directory.name,'manifest_sha256':digest,'source_stl_sha256':manifest['artifacts']['bracket.stl'],'solver_archive_sha256':manifest['artifacts']['fea-artifacts.zip'],'rows':rows,'status':'diagnostic_only','limitations':['Original 0.05 mm study tolerance remains unchanged','Wider tolerances can include rounded or tilted surfaces and change the loading model','Mesh measurements use subdivided boundary triangles; tolerance inclusion can differ slightly from the original quadratic face mask','This measures selection sensitivity, not nearest-surface distance or mesher error convergence']}
with Path(args.output).open('x') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report,indent=2))
