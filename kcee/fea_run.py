"""Persist a separate verification benchmark, preserving full solver artifacts."""
import base64,hashlib,json,os,uuid
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from kcee.fea import SolverError
from kcee.demo import stl

def solver_available():
    try:
        with urlopen(os.environ.get('STRUCTURAL_URL','http://structural:8005')+'/health',timeout=2) as response:return json.load(response)['status']=='ready'
    except Exception:return False

def run_benchmark(root):
    try:
        req=Request(os.environ.get('STRUCTURAL_URL','http://structural:8005')+'/benchmark',data=b'',method='POST')
        with urlopen(req,timeout=300) as response:data=json.load(response)
        fea=data['result'];archive=base64.b64decode(data['artifacts_base64'],validate=True)
        if fea['validation_status']!='benchmark_verified_only' or not all(fea['checks'].values()):raise ValueError('Benchmark checks did not pass')
    except Exception as exc:raise SolverError('Structural benchmark failed or worker unavailable. Start the fea profile and check worker logs.') from exc
    run_id=str(uuid.uuid4());dest=Path(root)/run_id;dest.mkdir(parents=True,exist_ok=False)
    requirements={'schema_version':1,'kind':'structural_benchmark','geometry_mm':{'length':60,'width':10,'thickness':3.5},'load_N':10,'youngs_modulus_MPa':69000,'poisson_ratio':.33,'density_kg_m3':2700,'boundary':'Fully fixed root; uniform end traction','material_source':'Illustrative benchmark material properties'}
    # Reuse the watertight extrusion exporter with a rectangle (height=thickness), omitting degenerate L vertices.
    vertices=[(x,y,z) for x,y,z in ((0,0,0),(60,0,0),(60,10,0),(0,10,0),(0,0,3.5),(60,0,3.5),(60,10,3.5),(0,10,3.5))]
    faces=[(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    lines=['solid cantilever']
    for face in faces:
        lines+=['facet normal 0 0 0','outer loop']+['vertex '+' '.join(map(str,vertices[i])) for i in face]+['endloop','endfacet']
    (dest/'bracket.stl').write_text('\n'.join(lines+['endsolid cantilever']))
    result={'kind':'structural_benchmark','validation_status':'benchmark_verified_only','geometry_backend':'structured_rectangular_cantilever','structural_backend':'CalculiX '+fea['version'],'selected':{'thickness_mm':3.5,'stress_MPa':6*10*60/(10*3.5**2),'tip_deflection_mm':fea['analytical_tip_deflection_mm'],'factor_of_safety':240/(6*10*60/(10*3.5**2))},'mass_kg':60*10*3.5*1e-9*2700,'fea':fea,'assumptions':['Separate rectangular cantilever benchmark, not the PicoGK bracket','Linear elasticity, small displacement, illustrative isotropic material','Fully fixed root and uniform free-end traction','Displacement and reaction checks passed; peak stress is not a converged bracket allowable']}
    for filename,value in [('requirements.json',requirements),('result.json',result),('fea.json',fea),('voice-summary.json',{'level':'RESULT','text':'Cantilever verification benchmark complete. Bracket validation remains pending.','delivery':'artifact_only'})]:(dest/filename).write_text(json.dumps(value,indent=2))
    (dest/'fea-artifacts.zip').write_bytes(archive)
    (dest/'report.md').write_text('# CalculiX cantilever verification benchmark\n\nThis verifies the benchmark implementation; it does not validate a bracket.\n\n'+json.dumps(fea,indent=2))
    source=Path(__file__)
    manifest={'schema_version':1,'kind':'structural_benchmark','run_id':run_id,'parent_design_id':None,'created_at':datetime.now(timezone.utc).isoformat(),'software_commit':None,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'validation_status':'benchmark_verified_only','artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2));return dest
