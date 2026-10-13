"""Verify a real, recorded bracket analysis through the running local API."""
import argparse,json,math
from urllib.request import Request,urlopen
parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);parser.add_argument('--analysis-run-id');parser.add_argument('--base-url',default='http://localhost:8000');args=parser.parse_args()
def request(path,method='GET'):
    with urlopen(Request(args.base_url+path,method=method,data=b'' if method=='POST' else None),timeout=340) as response:return json.load(response)
parent=request('/runs/'+args.run_id)
created={'run_id':args.analysis_run_id} if args.analysis_run_id else request('/runs/'+args.run_id+'/structural','POST');record=request('/runs/'+created['run_id'])
assert record['parent_id']==args.run_id
assert record['manifest']['source_parent_manifest_sha256']==parent['manifest_sha256']
assert request('/runs/'+created['run_id']+'/verify')['integrity']=='verified'
result=request('/artifacts/'+created['run_id']+'/result.json');fea=result['fea']
assert result['kind']=='bracket_structural'
assert fea['source_stl_sha256']==parent['manifest']['artifacts']['bracket.stl']
assert all(fea['checks'].values()) and len(fea['mesh_study'])==3
assert all(math.isfinite(row['tip_deflection_mm']) for row in fea['mesh_study'])
assert record['validation_status']=='numerical_checks_passed_not_engineering_validated'
print(json.dumps({'run_id':created['run_id'],'parent_id':args.run_id,'fine_mesh':fea['mesh_study'][-1],'checks':fea['checks'],'status':record['validation_status']},indent=2))
