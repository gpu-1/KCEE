"""Analyze a verified native bracket, preserving parent identity and raw diagnostics."""
import base64,hashlib,json,os,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from kcee.fea import SolverError

class BracketAnalysisError(SolverError):
    def __init__(self,message,run_id):super().__init__(message);self.run_id=run_id

def analyze(root,parent_id,record):
    source=Path(root)/str(parent_id)
    geometry=json.loads((source/'geometry-request.json').read_text())
    settings=json.loads((source/'requirements.json').read_text())
    if settings.get('load_N')!=100 or settings.get('youngs_modulus_MPa')!=69000:raise ValueError('This study supports the default 100 N / 69000 MPa sample only')
    if geometry['geometry_mm']!={'length':60,'width':30,'height':40,'thickness':3.5} or not geometry['mounting_holes']:raise ValueError('Only the default native 60×30×40 mm, 3.5 mm bracket is supported by this mounting/load study')
    run_id=str(uuid.uuid4());dest=Path(root)/run_id;dest.mkdir()
    for name in ('requirements.json','bracket.stl','geometry-request.json','geometry.json'):shutil.copy2(source/name,dest/name)
    metadata=json.loads((dest/'geometry.json').read_text());stl=(dest/'bracket.stl').read_bytes()
    payload={'stl_base64':base64.b64encode(stl).decode(),'expected_volume_mm3':metadata['volume_mm3'],'classification_angle':25 if metadata['voxel_size_mm']<.5 else 20}
    try:
        req=Request(os.environ.get('STRUCTURAL_URL','http://structural:8005')+'/bracket',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
        with urlopen(req,timeout=320) as response:data=json.load(response)
        fea=data['result'];archive=base64.b64decode(data['artifacts_base64'],validate=True)
        if fea['source_stl_sha256']!=hashlib.sha256(stl).hexdigest() or len(fea['mesh_study'])!=3:raise ValueError('Solver result is not tied to the selected STL')
    except Exception as exc:
        if isinstance(exc,HTTPError):
            try:
                failure=json.load(exc)
                (dest/'failed-solver-artifacts.zip').write_bytes(base64.b64decode(failure['artifacts_base64'],validate=True))
            except Exception:pass
        (dest/'failure.json').write_text(json.dumps({'run_id':run_id,'parent_design_id':str(parent_id),'stage':'bracket_structural','status':'failed','message':str(exc)},indent=2))
        raise BracketAnalysisError('Bracket analysis failed; retained diagnostics are available for this run.',run_id) from exc
    result=json.loads((source/'result.json').read_text());result.update({'kind':'bracket_structural','validation_status':fea['validation_status'],'structural_backend':'CalculiX 2.20 / Gmsh 4.8.4','fea':fea})
    result['analytical_assumptions']=result['assumptions']
    result['assumptions']=['Actual native PicoGK STL, including mounting holes and root transition','Linear isotropic elasticity, small displacement and illustrative material properties',fea['boundary'],'Displayed analytical estimates are separate ideal-cantilever references']
    result['assumptions']+=['FEA uses an ideal fully clamped rear mounting face, not bolt/contact behavior',fea['load'],fea['stress_note'],'Numerical mesh/force checks do not establish engineering validation']
    requirements=json.loads((dest/'requirements.json').read_text());requirements['structural_study']={'boundary':fea['boundary'],'load':fea['load'],'material':fea['material']};(dest/'requirements.json').write_text(json.dumps(requirements,indent=2))
    for name,value in [('result.json',result),('fea.json',fea),('voice-summary.json',{'level':'RESULT','text':'Native bracket structural study complete. Engineering validation remains pending.','delivery':'artifact_only'})]:(dest/name).write_text(json.dumps(value,indent=2))
    (dest/'fea-artifacts.zip').write_bytes(archive)
    (dest/'report.md').write_text('# Native PicoGK bracket structural study\n\nEngineering validation remains pending. Parent: '+str(parent_id)+'\n\n'+json.dumps(fea,indent=2))
    manifest={'schema_version':1,'kind':'bracket_structural','run_id':run_id,'parent_design_id':str(parent_id),'created_at':datetime.now(timezone.utc).isoformat(),'software_commit':None,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_parent_manifest_sha256':record['manifest_sha256'],'validation_status':fea['validation_status'],'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2));return dest
