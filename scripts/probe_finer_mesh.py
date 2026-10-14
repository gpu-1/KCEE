"""Bounded, source-verified exploratory mesh probe; run in structural image."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from urllib.request import urlopen
from uuid import UUID
from kcee.bracket_fea import mesh,solve_mesh
from kcee.stress_diagnostics import diagnose
from kcee.surface_load import stl_strip_area
parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);parser.add_argument('--output',required=True);parser.add_argument('--solve',action='store_true');args=parser.parse_args()
run_id=str(UUID(args.run_id));output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
def fetch(path):
    with urlopen('http://api:8000'+path,timeout=20) as response:return response.read()
record=json.loads(fetch('/runs/'+run_id))
if json.loads(fetch('/runs/'+run_id+'/verify'))['integrity']!='verified':raise ValueError('Unverified source run')
if record['manifest'].get('kind')!='bracket_structural':raise ValueError('Probe requires a saved bracket structural study')
raw=fetch('/artifacts/'+run_id+'/bracket.stl');digest=hashlib.sha256(raw).hexdigest()
if digest!=record['manifest']['artifacts']['bracket.stl']:raise ValueError('Source STL hash mismatch')
source=output/'source.stl'
with source.open('xb') as stream:stream.write(raw)
area=stl_strip_area(source)
report={'run_id':run_id,'manifest_sha256':record['manifest_sha256'],'source_stl_sha256':digest,'classification_angle_degrees':25,'node_budget':50000,'candidates':[],'status':'exploratory_meshing_not_solver_or_engineering_acceptance'}
for size in (1.3,1.2):
    directory=output/('mesh-'+str(size));directory.mkdir()
    try:
        nodes,elements,fixed,loads,summary=mesh(source,directory,size,25)
        report['candidates'].append({'status':'within_demo_budget' if len(nodes)<=50000 else 'exceeds_demo_budget','summary':summary,'relative_source_patch_error':abs(summary['load_patch_area_mm2']/area-1)})
    except Exception as error:report['candidates'].append({'target_size_mm':size,'status':'failed','error':str(error)})
    (output/'probe.json').write_text(json.dumps(report,indent=2))
if args.solve:
    directory=output/'solve'/'mesh-1.3'
    summary=solve_mesh(source,directory,1.3,25)
    archive=output/'exploratory-artifacts.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(directory.iterdir()):
            if path.is_file():zipped.write(path,'mesh-1.3/'+path.name)
    report['solve_1_3']={'summary':summary,'diagnostic':diagnose(archive,'mesh-1.3'),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'adapter_source_sha256':hashlib.sha256(Path('/app/kcee/bracket_fea.py').read_bytes()).hexdigest(),'solver_binary_sha256':hashlib.sha256(Path('/usr/bin/ccx').read_bytes()).hexdigest()}
    report['status']='exploratory_solved_not_engineering_acceptance'
    (output/'probe.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
