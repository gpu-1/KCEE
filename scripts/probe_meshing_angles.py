"""Run inside the structural image to compare meshes without solving or accepting a run."""
import argparse,hashlib,json,tempfile
from pathlib import Path
from urllib.request import urlopen
from uuid import UUID
from kcee.bracket_fea import mesh
from kcee.surface_load import stl_strip_area
parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);parser.add_argument('--base-url',default='http://api:8000');args=parser.parse_args();run_id=str(UUID(args.run_id))
def fetch(path):
 with urlopen(args.base_url+path,timeout=15) as response:return response.read()
record=json.loads(fetch('/runs/'+run_id))
if json.loads(fetch('/runs/'+run_id+'/verify'))['integrity']!='verified':raise ValueError('Unverified run')
raw=fetch('/artifacts/'+run_id+'/bracket.stl');digest=hashlib.sha256(raw).hexdigest()
if digest!=record['manifest']['artifacts']['bracket.stl']:raise ValueError('Source hash mismatch')
report={'run_id':run_id,'source_stl_sha256':digest,'target_size_mm':1.5,'candidates':[],'status':'mesh_probe_not_engineering_acceptance'}
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);source=root/'source.stl';source.write_bytes(raw);source_area=stl_strip_area(source)
 for angle in (25,35,45):
  destination=root/str(angle);destination.mkdir()
  try:
   nodes,elements,fixed,loads,summary=mesh(source,destination,1.5,angle)
   report['candidates'].append({'angle_degrees':angle,'status':'meshed','summary':summary,'source_load_strip_area_mm2':source_area,'relative_source_patch_error':abs(summary['load_patch_area_mm2']/source_area-1)})
  except Exception as error:report['candidates'].append({'angle_degrees':angle,'status':'failed','error':str(error)})
print(json.dumps(report,indent=2))
