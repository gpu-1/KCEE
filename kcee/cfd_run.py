"""Persist the verified channel-flow worker benchmark with source/artifact hashes."""
import hashlib,json,os,uuid
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from kcee.cfd import benchmark

def cfd_available():
 try:
  with urlopen(os.environ.get('CFD_URL','http://cfd:8007')+'/health',timeout=2) as response:return json.load(response)['status']=='ready'
 except Exception:return False

def run_cfd(root):
 with urlopen(Request(os.environ.get('CFD_URL','http://cfd:8007')+'/benchmark',data=b'',method='POST'),timeout=15) as response:flow=json.load(response)
 if flow!=benchmark() or not all(flow['checks'].values()):raise ValueError('CFD worker result reproduction failed')
 dest=Path(root)/str(uuid.uuid4());dest.mkdir(parents=True,exist_ok=False)
 result={'kind':'cfd_benchmark','validation_status':flow['validation_status'],'geometry_backend':'Illustrative channel envelope, not a 3D flow mesh','cfd':flow,'assumptions':flow['limits']}
 vertices=[(0,0,0),(200,0,0),(200,20,0),(0,20,0),(0,0,10),(200,0,10),(200,20,10),(0,20,10)];faces=[(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)];lines=['solid channel_envelope']
 for face in faces:lines+=['facet normal 0 0 0','outer loop']+['vertex '+' '.join(map(str,vertices[i])) for i in face]+['endloop','endfacet']
 (dest/'bracket.stl').write_text('\n'.join(lines+['endsolid channel_envelope']))
 for name,data in [('result.json',result),('requirements.json',flow['inputs']),('cfd.json',flow),('voice-summary.json',{'text':'Channel flow numerical verification complete. General CFD and engineering validation remain pending.','delivery':'artifact_only'})]:(dest/name).write_text(json.dumps(data,indent=2))
 (dest/'velocity.csv').write_text('y_m,velocity_m_s,analytical_velocity_m_s\n'+'\n'.join(','.join(str(row[k]) for k in ('y_m','velocity_m_s','analytical_velocity_m_s')) for row in flow['mesh_study'][-1]['profile'])+'\n')
 fine=flow['mesh_study'][-1]
 report=['# Plane Poiseuille CFD verification benchmark','','Numerical verification only; engineering validation remains pending.','',flow['method'],flow['analytical_solution'],'','## Inputs (SI)',json.dumps(flow['inputs'],indent=2),'','## Fine-grid results',f"Mean velocity: {fine['mean_velocity_m_s']} m/s",f"Flow per unit span: {fine['flow_per_span_m2_s']} m²/s",f"Reynolds number (hydraulic diameter 2H): {fine['reynolds_hydraulic_diameter']}",'','## Refinement','| Cells | Profile error (relative to exact peak) | Flow error | Momentum balance error |','|---|---|---|---|']
 for m in flow['mesh_study']:report.append(f"| {m['cells']} | {m['relative_profile_error']} | {m['relative_flow_error']} | {m['relative_momentum_balance_error']} |")
 report+=['','Observed orders: '+json.dumps(flow['observed_orders']),'','Checks: '+json.dumps(flow['checks']),'Tolerances: '+json.dumps(flow['tolerances']),'','## Limits',*['- '+s for s in flow['limits']],'','Analytical reference: '+flow['reference']]
 (dest/'report.md').write_text('\n'.join(report)+'\n')
 manifest={'schema_version':1,'kind':'cfd_benchmark','run_id':dest.name,'parent_design_id':None,'created_at':datetime.now(timezone.utc).isoformat(),'software_commit':None,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'solver_source_sha256':hashlib.sha256(Path(__file__).with_name('cfd.py').read_bytes()).hexdigest(),'validation_status':flow['validation_status'],'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}}
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2));return dest
