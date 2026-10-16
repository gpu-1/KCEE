"""Reuse only exact, raw-reverified source recipes and sampling versions."""
import base64,hashlib,json
from pathlib import Path
from kcee.bracket_flow_run import verified_archive
from kcee.flow_sampling import DEFAULT,flow_version
from kcee.provenance import verify_directory

def reusable(root,parent,record,registry,mesh,domain='base',bore_level=4,version=DEFAULT,local_profile='baseline'):
 root=Path(root);offset=0;raw=(root/str(parent)/'bracket.stl').read_bytes()
 while True:
  entries=registry.list(100,offset)
  for item in entries:
   if item['kind']!='bracket_flow' or str(item['parent_id'])!=str(parent):continue
   path=root/str(item['id']);registry.verify(root,item['id']);manifest,digest=verify_directory(path);flow=json.loads((path/'cfd.json').read_text())
   if flow.get('mesh_name')!=mesh or flow.get('domain_name','base')!=domain or flow.get('inputs',{}).get('bore_refinement',{}).get('level')!=bore_level:continue
   if flow.get('inputs',{}).get('local_refinement_profile','baseline')!=local_profile:continue
   try:candidate_version=flow_version(flow)
   except ValueError:continue  # Older sampling recipes are not candidates for current workflows.
   if candidate_version!=version:continue
   if manifest.get('source_parent_manifest_sha256')!=record['manifest_sha256'] or not flow.get('checks') or not all(flow['checks'].values()) or not flow.get('bore_verification',{}).get('all_pass'):continue
   archive=(path/'cfd-artifacts.zip').read_bytes()
   try:verified_archive({'result':flow,'archive_base64':base64.b64encode(archive).decode(),'archive_sha256':hashlib.sha256(archive).hexdigest()},raw,mesh,domain,bore_level)
   except ValueError:continue
   return {'run_id':path.name,'manifest_sha256':digest,'flow':flow,'reused':True}
  if len(entries)<100:return None
  offset+=100
