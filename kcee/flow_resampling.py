"""Immutable, raw-verified postprocessing changes; no new solver execution."""
import base64,hashlib,io,json,shutil,tempfile,uuid,zipfile
from pathlib import Path
from kcee.bracket_flow import apply_sampling,cell_positions
from kcee.bracket_flow_run import verified_archive,save_completed
from kcee.flow_sampling import COMPACT,flow_version,sampling_spec
from kcee.provenance import verify_directory

def resample_archive(payload,raw,mesh,domain='base',bore_level=4,target=COMPACT):
 sampling_spec(target)
 old,archive=verified_archive(payload,raw,mesh,domain,bore_level)
 if flow_version(old)==target:raise ValueError('Source already uses the requested sampling version')
 with zipfile.ZipFile(io.BytesIO(archive)) as source,tempfile.TemporaryDirectory() as d:
  root=Path(d)
  for name in ('points','faces','owner','neighbour','boundary'):(root/name).write_bytes(source.read('constant/polyMesh/'+name))
  flow=dict(old,inputs=dict(old['inputs']));apply_sampling(flow,cell_positions(root,old['cells']),root,target)
  buffer=io.BytesIO()
  with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as dest:
   for name in source.namelist():
    if name!='sampling.json':dest.writestr(name,source.read(name))
   dest.writestr('sampling.json',json.dumps(sampling_spec(target),sort_keys=True))
  data=buffer.getvalue()
 # Check the new production result against the raw archive under its declared version.
 result,data=verified_archive({'result':flow,'archive_base64':base64.b64encode(data).decode(),'archive_sha256':hashlib.sha256(data).hexdigest()},raw,mesh,domain,bore_level)
 return result,data

def resample_source(root,parent,record,source_id,registry,target=COMPACT):
 root=Path(root);registry.verify(root,parent);registry.verify(root,source_id);source=root/str(source_id);manifest,digest=verify_directory(source)
 if manifest.get('kind')!='bracket_flow' or manifest.get('parent_design_id')!=str(parent) or manifest.get('source_parent_manifest_sha256')!=record['manifest_sha256']:raise ValueError('Resampling source parent identity differs')
 original=json.loads((source/'cfd.json').read_text());archive=(source/'cfd-artifacts.zip').read_bytes();sha=hashlib.sha256(archive).hexdigest();mesh=original['mesh_name'];domain=original.get('domain_name','base');level=original['inputs']['bore_refinement']['level']
 flow,data=resample_archive({'result':original,'archive_base64':base64.b64encode(archive).decode(),'archive_sha256':sha},(root/str(parent)/'bracket.stl').read_bytes(),mesh,domain,level,target)
 dest=root/str(uuid.uuid4());dest.mkdir()
 for name in ('requirements.json','bracket.stl','geometry-request.json','geometry.json'):shutil.copy2(root/str(parent)/name,dest/name)
 origin={'run_id':str(source_id),'manifest_sha256':digest,'solver_archive_sha256':sha,'sampling_version':flow_version(original),'operation':'recomputed_probes_from_verified_unchanged_solver_fields','solver_reexecuted':False}
 save_completed(dest,root,parent,record,flow,data,origin);registry.register(dest);registry.verify(root,dest.name);return dest
