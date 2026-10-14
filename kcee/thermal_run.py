"""Persist worker verification separately from mechanical/bracket studies."""
import hashlib,json,os,uuid
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from kcee.thermal import benchmark

def thermal_available():
 try:
  with urlopen(os.environ.get('THERMAL_URL','http://thermal:8006')+'/health',timeout=2) as response:return json.load(response)['status']=='ready'
 except Exception:return False

def run_thermal(root):
 with urlopen(Request(os.environ.get('THERMAL_URL','http://thermal:8006')+'/benchmark',data=b'',method='POST'),timeout=15) as response:thermal=json.load(response)
 # Independent API-side reproduction rejects changed results or failed checks.
 if thermal!=benchmark() or not all(thermal['checks'].values()):raise ValueError('Thermal benchmark reproduction failed')
 dest=Path(root)/str(uuid.uuid4());dest.mkdir(parents=True,exist_ok=False)
 result={'kind':'thermal_benchmark','validation_status':thermal['validation_status'],'geometry_backend':'Rectangular 1D thermal bar','thermal':thermal,'assumptions':thermal['limits']}
 vertices=[(x,y,z) for x,y,z in ((0,0,0),(100,0,0),(100,10,0),(0,10,0),(0,0,10),(100,0,10),(100,10,10),(0,10,10))]
 faces=[(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
 lines=['solid thermal_bar']
 for face in faces:lines+=['facet normal 0 0 0','outer loop']+['vertex '+' '.join(map(str,vertices[i])) for i in face]+['endloop','endfacet']
 (dest/'bracket.stl').write_text('\n'.join(lines+['endsolid thermal_bar']))
 for name,data in [('result.json',result),('requirements.json',thermal['inputs']),('thermal.json',thermal),('voice-summary.json',{'text':'Thermal implementation benchmark complete. Bracket thermal validation remains pending.','delivery':'artifact_only'})]:(dest/name).write_text(json.dumps(data,indent=2))
 (dest/'temperature.csv').write_text('x_m,temperature_C,analytical_temperature_C\n'+'\n'.join(','.join(str(row[key]) for key in ('x_m','temperature_C','analytical_temperature_C')) for row in thermal['mesh_study'][-1]['profile'])+'\n')
 (dest/'report.md').write_text('# Steady 1D thermal verification benchmark\n\nThis is an implementation benchmark, not bracket thermal validation.\n\n'+json.dumps(thermal,indent=2))
 manifest={'schema_version':1,'kind':'thermal_benchmark','run_id':dest.name,'parent_design_id':None,'created_at':datetime.now(timezone.utc).isoformat(),'software_commit':None,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'solver_source_sha256':hashlib.sha256(Path(__file__).with_name('thermal.py').read_bytes()).hexdigest(),'validation_status':thermal['validation_status'],'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}}
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2));return dest
