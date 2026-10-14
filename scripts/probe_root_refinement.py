"""Source-verified bounded local-root refinement; run in structural image."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from urllib.request import urlopen
from uuid import UUID
from kcee.bracket_fea import mesh,solve_mesh
from kcee.stress_diagnostics import diagnose
from kcee.surface_load import stl_strip_area
parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
run_id=str(UUID(args.run_id));output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
def fetch(path):
    with urlopen('http://api:8000'+path,timeout=20) as response:return response.read()
record=json.loads(fetch('/runs/'+run_id))
if record['manifest'].get('kind')!='bracket_structural' or json.loads(fetch('/runs/'+run_id+'/verify'))['integrity']!='verified':raise ValueError('Verified bracket study required')
raw=fetch('/artifacts/'+run_id+'/bracket.stl');digest=hashlib.sha256(raw).hexdigest()
if digest!=record['manifest']['artifacts']['bracket.stl']:raise ValueError('Source STL hash mismatch')
source=output/'source.stl'
with source.open('xb') as stream:stream.write(raw)
area=stl_strip_area(source)
report={'run_id':run_id,'manifest_sha256':record['manifest_sha256'],'source_stl_sha256':digest,'classification_angle_degrees':25,'global_target_mm':1.5,'root_box_mm':{'x':[-1,3],'y':[-1,31],'z':[2.5,5]},'node_budget':50000,'candidates':[],'status':'exploratory_not_engineering_acceptance'}
for target in (.9,.75):
    directory=output/('root-'+str(target));directory.mkdir()
    candidate={'root_local_target_mm':target};report['candidates'].append(candidate)
    try:
        probe=directory/'mesh-probe';probe.mkdir()
        nodes,elements,fixed,loads,summary=mesh(source,probe,1.5,25,target)
        candidate.update({'mesh_probe':summary,'relative_source_patch_error':abs(summary['load_patch_area_mm2']/area-1)})
        if len(nodes)>50000:candidate['status']='exceeds_demo_budget'
        else:
            summary=solve_mesh(source,directory/'mesh-1.5',1.5,25,target)
            archive=directory/'solver-artifacts.zip'
            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zipped:
                for path in sorted((directory/'mesh-1.5').iterdir()):
                    if path.is_file():zipped.write(path,'mesh-1.5/'+path.name)
            candidate.update({'status':'solved_exploratory','summary':summary,'diagnostic':diagnose(archive),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()})
    except Exception as error:candidate.update({'status':'failed','error':str(error)})
    (output/'probe.json').write_text(json.dumps(report,indent=2))
report['adapter_source_sha256']=hashlib.sha256(Path('/app/kcee/bracket_fea.py').read_bytes()).hexdigest();report['solver_binary_sha256']=hashlib.sha256(Path('/usr/bin/ccx').read_bytes()).hexdigest()
(output/'probe.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
