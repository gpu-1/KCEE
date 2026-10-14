import base64,hashlib,io,json,os,shutil,uuid,zipfile
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from kcee.bracket_analysis import BracketAnalysisError

def analyze_thermal(root,parent_id,record):
    source=Path(root)/str(parent_id);geometry=json.loads((source/'geometry-request.json').read_text());metadata=json.loads((source/'geometry.json').read_text())
    if geometry['geometry_mm']!={'length':60,'width':30,'height':40,'thickness':3.5} or not geometry['mounting_holes']:raise ValueError('Only the default native bracket is supported')
    dest=Path(root)/str(uuid.uuid4());dest.mkdir()
    for name in ('bracket.stl','geometry-request.json','geometry.json'):shutil.copy2(source/name,dest/name)
    stl=(dest/'bracket.stl').read_bytes();payload={'stl_base64':base64.b64encode(stl).decode(),'expected_volume_mm3':metadata['volume_mm3'],'classification_angle':25 if metadata['voxel_size_mm']<.5 else 20}
    try:
        req=Request(os.environ.get('STRUCTURAL_URL','http://structural:8005')+'/thermal-bracket',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
        with urlopen(req,timeout=320) as response:data=json.load(response)
        result=data['result'];archive=base64.b64decode(data['artifacts_base64'],validate=True)
        if result['source_stl_sha256']!=hashlib.sha256(stl).hexdigest() or len(result['mesh_study'])!=3:raise ValueError('Thermal source/mesh identity mismatch')
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            if json.loads(zipped.read('thermal.json'))!=result:raise ValueError('Thermal archive result mismatch')
            csv=zipped.read('mesh-1.5/temperature.csv')
        if result['kind']!='bracket_thermal' or len(result['checks'])!=7 or not all(isinstance(value,bool) for value in result['checks'].values()):raise ValueError('Incomplete thermal checks')
    except Exception as error:
        if isinstance(error,HTTPError):
            try:(dest/'failed-solver-artifacts.zip').write_bytes(base64.b64decode(json.load(error)['artifacts_base64'],validate=True))
            except Exception:pass
        (dest/'failure.json').write_text(json.dumps({'run_id':dest.name,'parent_design_id':str(parent_id),'stage':'bracket_thermal','status':'failed','message':str(error)},indent=2))
        raise BracketAnalysisError('Bracket thermal analysis failed; retained diagnostics are available.',dest.name) from error
    saved={'kind':'bracket_thermal','geometry_backend':'PicoGK '+metadata['package_version'],'validation_status':result['validation_status'],'thermal':result,'assumptions':result['limits']}
    for name,value in [('result.json',saved),('thermal.json',result),('requirements.json',{'thermal_study':{'conductivity_W_m_K':15,'boundary':result['boundary'],'source_parent_manifest_sha256':record['manifest_sha256']}}),('voice-summary.json',{'text':'Bracket steady thermal study complete. Engineering validation remains pending.','delivery':'artifact_only'})]:(dest/name).write_text(json.dumps(value,indent=2))
    (dest/'thermal-artifacts.zip').write_bytes(archive);(dest/'temperature.csv').write_bytes(csv)
    (dest/'report.md').write_text('# Native PicoGK bracket steady thermal study\n\nEngineering validation remains pending. Parent: '+str(parent_id)+'\n\n'+json.dumps(result,indent=2))
    manifest={'schema_version':1,'kind':'bracket_thermal','run_id':dest.name,'parent_design_id':str(parent_id),'created_at':datetime.now(timezone.utc).isoformat(),'software_commit':None,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_parent_manifest_sha256':record['manifest_sha256'],'validation_status':result['validation_status'],'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2));return dest

def temperature_surface(archive):
    with zipfile.ZipFile(archive) as zipped:
        entry=zipped.getinfo('mesh-1.5/thermal-surface.json')
        if entry.file_size>8*1024*1024:raise ValueError('Thermal field exceeds preview budget')
        data=json.loads(zipped.read(entry))
    import math
    points=data['positions'];values=data['temperatures_C'];triangles=data['triangles']
    if not 0<len(points)==len(values)<50000 or any(len(point)!=3 or not all(math.isfinite(v) for v in point) for point in points) or not all(math.isfinite(v) for v in values):raise ValueError('Invalid thermal field')
    if not triangles or any(len(triangle)!=3 or any(not isinstance(index,int) or not 0<=index<len(points) for index in triangle) for triangle in triangles):raise ValueError('Invalid thermal triangles')
    if min(values)!=data['minimum_temperature_C'] or max(values)!=data['maximum_temperature_C']:raise ValueError('Thermal range mismatch')
    return data
