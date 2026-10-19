"""Three fixed wall/bore refinements with native load settling and replay."""
import base64,hashlib
from pathlib import Path
from kcee.flow_sources import reusable
from kcee.flow_forces_run import source
from kcee.bracket_flow_run import run_bracket_flow
from kcee.native_forces_run import call,summarize,save
from kcee.cfd_control import checkpoint,registered
from kcee.force_history import PROFILE
def run_study(root,identifier,registry):
 root=Path(root);registry.verify(root,identifier);record=registry.get(identifier)
 parent=record['parent_id'] if record['manifest'].get('kind')=='bracket_flow' else identifier
 registry.verify(root,parent);record=registry.get(parent);sources=[]
 for mesh in ('coarse','medium','fine'):
  checkpoint('force_history_source',mesh=mesh,domain='far')
  s=reusable(root,parent,record,registry,mesh,'far',bore_level=5,local_profile=PROFILE)
  if s is None:
   dest=run_bracket_flow(root,parent,record,mesh,'far',5,'compact-radius-v1',PROFILE);registry.register(dest);registered(dest.name);s=source(root,dest.name,registry)
  sources.append(s)
 blobs={'benchmark.zip':call('/native-force-benchmark',{})}
 for s in sources:
  f=s['flow'];p=root/s['run_id'];archive=(p/'cfd-artifacts.zip').read_bytes();checkpoint('native_force_postprocess',mesh=f['mesh_name'],domain='far')
  blobs[s['run_id']+'.zip']=call('/native-forces',{'archive_base64':base64.b64encode(archive).decode(),'archive_sha256':hashlib.sha256(archive).hexdigest(),'stl_base64':base64.b64encode((p/'bracket.stl').read_bytes()).decode(),'mesh_name':f['mesh_name'],'domain_name':'far','bore_level':5,'local_profile':PROFILE})
 data=summarize(root,sources,blobs);checkpoint('saving_native_force_report');return save(root,parent,record,data,blobs)
