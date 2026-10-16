"""Recompute a historical combined CFD study with versioned compact sampling.

Run inside the API environment. Five unique raw cases are verified and replayed;
new source/domain/combined runs are registered. No PDE solve is repeated.
"""
import argparse,json,sys
from pathlib import Path
from uuid import UUID

def rebuild(root,combined_id,registry):
 from kcee.provenance import verify_directory
 from kcee.flow_resampling import resample_source
 from kcee.flow_domain import save as save_domain
 from kcee.flow_combined import save as save_combined
 root=Path(root);combined_id=str(UUID(str(combined_id)));registry.verify(root,combined_id);path=root/combined_id;manifest,_=verify_directory(path)
 if manifest.get('kind')!='bracket_flow_combined':raise ValueError('Use a combined CFD verification source')
 parent=manifest['parent_design_id'];registry.verify(root,parent);record=registry.get(parent)
 if manifest['source_parent_manifest_sha256']!=record['manifest_sha256']:raise ValueError('Combined parent identity differs')
 original=json.loads((path/'cfd.json').read_text());domain=original['domain_comparison'];registry.verify(root,domain['run_id']);_,digest=verify_directory(root/domain['run_id'])
 if digest!=domain['manifest_sha256'] or json.loads((root/domain['run_id']/'cfd.json').read_text())!=domain['data']:raise ValueError('Original domain evidence differs')
 rows=domain['data']['studies']+original['mesh_study']['studies'];expected={}
 for s in rows:
  if s['run_id'] in expected and expected[s['run_id']]!=s['manifest_sha256']:raise ValueError('Shared source identity differs')
  expected[s['run_id']]=s['manifest_sha256']
 mapping={}
 for old,digest in expected.items():
  registry.verify(root,old);_,actual=verify_directory(root/old)
  if actual!=digest:raise ValueError('Original source digest differs')
  dest=resample_source(root,parent,record,old,registry);mapping[old]=dest.name;print('Recomputed '+old+' → '+dest.name,file=sys.stderr,flush=True)
 def sources(rows):
  out=[]
  for row in rows:
   p=root/mapping[row['run_id']];registry.verify(root,p.name);_,digest=verify_directory(p);out.append({'run_id':p.name,'manifest_sha256':digest,'flow':json.loads((p/'cfd.json').read_text()),'reused':True})
  return out
 dp=save_domain(root,parent,record,sources(domain['data']['studies']));registry.register(dp);registry.verify(root,dp.name);_,digest=verify_directory(dp)
 cp=save_combined(root,parent,record,sources(original['mesh_study']['studies']),{'run_id':dp.name,'manifest_sha256':digest,'data':json.loads((dp/'cfd.json').read_text())});registry.register(cp);registry.verify(root,cp.name)
 return {'operation':'recomputed_compact_sampling_from_verified_solver_fields','source_combined_run_id':combined_id,'sampling_version':'compact-radius-v1','solver_reexecuted':False,'source_mapping':mapping,'domain_run_id':dp.name,'combined_run_id':cp.name}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runs-dir',default='/data/runs');p.add_argument('--combined',required=True);a=p.parse_args()
 from kcee.registry import Registry
 print(json.dumps(rebuild(a.runs_dir,a.combined,Registry()),indent=2),flush=True)
if __name__=='__main__':main()
