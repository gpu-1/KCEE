#!/usr/bin/env python3
"""Finalize a matched CFD bore study with native exporter audits and registry checks.

Run from the project root after creating the two level-5 source cases through
POST /runs/{parent}/flow with mesh_name medium/fine, domain_name far, bore_level 5.
Existing source cases are never overwritten or solved again by this command.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.provenance import verify_directory

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--combined',required=True);parser.add_argument('--medium-refined',required=True);parser.add_argument('--fine-refined',required=True);args=parser.parse_args()
 root=Path(__file__).resolve().parents[1];runs=root/'runs';combined=runs/args.combined;cm,_=verify_directory(combined)
 if cm.get('kind')!='bracket_flow_combined':raise ValueError('Use a combined verification source')
 parent=cm['parent_design_id'];baseline=json.loads((combined/'cfd.json').read_text())['mesh_study']['studies'][1:];sources=[];audits={};out=root/'.local/verification/pressure-native';out.mkdir(parents=True,exist_ok=True)
 for run_id in [s['run_id'] for s in baseline]+[args.medium_refined,args.fine_refined]:
  path=runs/run_id;manifest,digest=verify_directory(path)
  if manifest.get('kind')!='bracket_flow' or manifest['parent_design_id']!=parent:raise ValueError('Pressure source parent differs')
  if run_id in [s['run_id'] for s in baseline] and digest!=next(s['manifest_sha256'] for s in baseline if s['run_id']==run_id):raise ValueError('Baseline identity differs')
  flow=json.loads((path/'cfd.json').read_text());flow.pop('field');raw=(path/'cfd-artifacts.zip').read_bytes();sha=hashlib.sha256(raw).hexdigest()
  cache=out/(run_id+'-native.json')
  if cache.exists() and cache.stat().st_size and json.loads(cache.read_text()).get('schema')=='kcee.native-centre-stencil-audit.v1':
   audit=json.loads(cache.read_text())
   if audit['source_archive_sha256']!=sha:raise ValueError('Cached native audit source differs')
  else:
   proc=subprocess.run(['docker','compose','exec','-T','cfd','python','-m','kcee.flow_native'],input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=root,timeout=240,check=True);audit=json.loads(proc.stdout);cache.write_text(json.dumps(audit,indent=2))
  sources.append({'run_id':run_id,'manifest_sha256':digest,'archive_sha256':sha,'flow':flow});audits[run_id]=audit
 bundle={'parent':parent,'combined':args.combined,'sources':sources,'audits':audits}
 code="""import sys,json,hashlib,base64
from pathlib import Path
from kcee.registry import Registry
from kcee.flow_pressure import save
from kcee.flow_native import validate_audit
from kcee.bracket_flow_run import verified_archive
from kcee.provenance import verify_directory
b=json.load(sys.stdin);root=Path('/data/runs');registry=Registry();registry.verify(root,b['combined']);registry.verify(root,b['parent']);record=registry.get(b['parent'])
for s in b['sources']:
 registry.verify(root,s['run_id']);p=root/s['run_id'];m,d=verify_directory(p);f=json.loads((p/'cfd.json').read_text());raw=(p/'cfd-artifacts.zip').read_bytes();verified_archive({'result':f,'archive_base64':base64.b64encode(raw).decode(),'archive_sha256':hashlib.sha256(raw).hexdigest()},(root/b['parent']/'bracket.stl').read_bytes(),f['mesh_name'],'far',f['inputs']['bore_refinement']['level']);validate_audit(b['audits'][s['run_id']],f);f.pop('field')
 if d!=s['manifest_sha256'] or f!=s['flow'] or m['source_parent_manifest_sha256']!=record['manifest_sha256'] or hashlib.sha256((p/'cfd-artifacts.zip').read_bytes()).hexdigest()!=s['archive_sha256']:raise ValueError('Source identity differs')
p=save(root,b['parent'],record,b['sources'],b['audits']);registry.register(p);registry.verify(root,p.name);print(json.dumps({'run_id':p.name,'checks':json.loads((p/'cfd.json').read_text())['checks']}))
"""
 proc=subprocess.run(['docker','compose','exec','-T','api','python','-c',code],input=json.dumps(bundle).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=root,timeout=600,check=True)
 result=json.loads(proc.stdout);(out/'pressure-response.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
