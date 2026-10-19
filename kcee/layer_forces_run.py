"""Fixed four-case wall-layer sensitivity study with native load replay."""
from pathlib import Path
import base64,hashlib
from kcee.flow_sources import reusable
from kcee.flow_forces_run import source
from kcee.bracket_flow_run import run_bracket_flow
from kcee.native_forces_run import call,summarize,save
from kcee.cfd_control import checkpoint,registered
RECIPES=[('medium','wake-below-v1'),('fine','wake-below-v1'),('medium','wall-layers-v1'),('fine','wall-layers-v1')]
def run_study(root,identifier,registry):
 root=Path(root);registry.verify(root,identifier);record=registry.get(identifier)
 parent=record['parent_id'] if record['manifest'].get('kind')=='bracket_flow' else identifier
 registry.verify(root,parent);record=registry.get(parent);sources=[]
 for mesh,profile in RECIPES:
  checkpoint('layer_source',mesh=mesh,domain='far')
  s=reusable(root,parent,record,registry,mesh,'far',local_profile=profile)
  if s is None:
   dest=run_bracket_flow(root,parent,record,mesh,'far',4,'compact-radius-v1',profile)
   registry.register(dest);registered(dest.name);s=source(root,dest.name,registry)
  sources.append(s)
 blobs={'benchmark.zip':call('/native-force-benchmark',{})}
 for s in sources:
  f=s['flow'];p=root/s['run_id'];archive=(p/'cfd-artifacts.zip').read_bytes();checkpoint('native_force_postprocess',mesh=f['mesh_name'],domain='far')
  blobs[s['run_id']+'.zip']=call('/native-forces',{'archive_base64':base64.b64encode(archive).decode(),'archive_sha256':hashlib.sha256(archive).hexdigest(),'stl_base64':base64.b64encode((p/'bracket.stl').read_bytes()).decode(),'mesh_name':f['mesh_name'],'domain_name':'far','bore_level':4,'local_profile':f['inputs']['local_refinement_profile']})
 data=summarize(root,sources,blobs);dest=save(root,parent,record,data,blobs)
 return dest
