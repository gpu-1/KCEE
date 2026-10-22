"""Fixed fine-background hotspot refinement, retaining immutable baseline evidence."""
REGIONS=[{'name':'rootEdge','min_m':[-.001,.026,-.002],'max_m':[.008,.032,.009],'level':5},{'name':'uprightEdge','min_m':[-.001,-.002,.035],'max_m':[.006,.006,.043],'level':5}]
def refine_dictionary(text):
 for r in REGIONS:
  vec=lambda v:'('+' '.join(map(str,v))+')'
  text=text.replace('geometry {','geometry {'+r['name']+' {type searchableBox;min '+vec(r['min_m'])+';max '+vec(r['max_m'])+';} ',1)
  text=text.replace('refinementRegions {','refinementRegions {'+r['name']+' {mode inside;levels ((1e15 5));} ',1)
 return text

def run_study(root,identifier,registry):
 import base64,hashlib
 from pathlib import Path
 from kcee.flow_sources import reusable
 from kcee.flow_forces_run import source
 from kcee.bracket_flow_run import run_bracket_flow
 from kcee.native_forces_run import call,summarize,save
 from kcee.cfd_control import checkpoint,registered
 from kcee.force_history import FINE_PROFILE,HOTSPOT_PROFILE
 root=Path(root);registry.verify(root,identifier);record=registry.get(identifier);parent=record['parent_id'] if record['manifest'].get('kind')=='bracket_flow' else identifier
 registry.verify(root,parent);record=registry.get(parent);sources=[]
 for profile in (FINE_PROFILE,HOTSPOT_PROFILE):
  checkpoint('hotspot_source',mesh='fine',domain='far');s=reusable(root,parent,record,registry,'fine','far',bore_level=5,local_profile=profile)
  if s is None:
   dest=run_bracket_flow(root,parent,record,'fine','far',5,'compact-radius-v1',profile);registry.register(dest);registered(dest.name);s=source(root,dest.name,registry)
  sources.append(s)
 blobs={'benchmark.zip':call('/native-force-benchmark',{})}
 for s in sources:
  p=root/s['run_id'];archive=(p/'cfd-artifacts.zip').read_bytes();checkpoint('native_force_postprocess',mesh='fine',domain='far')
  blobs[s['run_id']+'.zip']=call('/native-forces',{'archive_base64':base64.b64encode(archive).decode(),'archive_sha256':hashlib.sha256(archive).hexdigest(),'stl_base64':base64.b64encode((p/'bracket.stl').read_bytes()).decode(),'mesh_name':'fine','domain_name':'far','bore_level':5,'local_profile':s['flow']['inputs']['local_refinement_profile']})
 data=summarize(root,sources,blobs);checkpoint('saving_hotspot_report');return save(root,parent,record,data,blobs)
