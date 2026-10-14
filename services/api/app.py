import zipfile
import logging
import os
from pathlib import Path
from uuid import UUID
import psycopg
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Literal
from kcee.picogk import GeometryError
from kcee.geometry_queue import available
from kcee.fea_run import run_benchmark,solver_available
from kcee.fea import SolverError
from kcee.bracket_analysis import analyze,BracketAnalysisError
from kcee.demo import run
from kcee.registry import Registry
from kcee.provenance import IntegrityError

ARTIFACTS=Path(os.environ.get('KCEE_RUNS_DIR','/data/runs'))
ARTIFACTS.mkdir(parents=True,exist_ok=True)
registry=Registry()
app=FastAPI(title='KCEE',version='0.2.0')
app.mount('/artifacts',StaticFiles(directory=ARTIFACTS),name='artifacts')

@app.get('/health')
def health():
    # Liveness does not claim database readiness.
    return {'status':'ok','mode':'analytical_demo','native_adapters':'not_connected'}

@app.get('/ready')
def ready():
    try: registry.ready()
    except psycopg.Error: raise HTTPException(503,'Database unavailable or schema not installed')
    return {'status':'ready','database':'connected'}

class BracketRequest(BaseModel):
    geometry_backend: Literal['mesh','picogk']='mesh'

@app.get('/capabilities')
def capabilities():
    queue=os.environ.get('KCEE_GEOMETRY_QUEUE','/data/geometry/queue')
    key=os.environ.get('KCEE_GEOMETRY_KEY','/data/geometry/key')
    return {'geometry':{'mesh':True,'picogk':available(queue,key)},'structural':{'calculix':solver_available()},'validation':'demonstrator_only'}

@app.post('/runs/bracket',status_code=201)
def bracket(body: BracketRequest=BracketRequest()):
    ready()
    try: dest=run(ARTIFACTS,geometry_backend=body.geometry_backend)
    except GeometryError as exc: raise HTTPException(503,str(exc))
    try: registry.register(dest)
    except (psycopg.Error,IntegrityError):
        # Retain artifacts for explicit recovery; never return a false success.
        logging.error('Run %s was generated but registration failed',dest.name)
        raise HTTPException(503,{'message':'Artifacts retained; database registration failed','run_id':dest.name,'recovery':'Use the documented register command'})
    return {'run_id':dest.name,'manifest_url':f'/artifacts/{dest.name}/manifest.json','stl_url':f'/artifacts/{dest.name}/bracket.stl','validation_status':'unvalidated_analytical_screening','registration':'saved'}

@app.get('/runs')
def list_runs(limit: int=Query(50,ge=1,le=100),offset: int=Query(0,ge=0),hidden: bool=False):
    try: return {'items':registry.list(limit,offset,hidden),'limit':limit,'offset':offset}
    except psycopg.Error: raise HTTPException(503,'Database unavailable')

@app.get('/runs/{run_id}')
def get_run(run_id: UUID):
    try: record=registry.get(run_id)
    except psycopg.Error: raise HTTPException(503,'Database unavailable')
    if record is None: raise HTTPException(404,'Run not found')
    return record

@app.get('/runs/{run_id}/verify')
def verify_run(run_id: UUID):
    try: return registry.verify(ARTIFACTS,run_id)
    except KeyError: raise HTTPException(404,'Run not found')
    except IntegrityError as exc: raise HTTPException(409,str(exc))
    except psycopg.Error: raise HTTPException(503,'Database unavailable')

@app.post('/runs/structural-benchmark',status_code=201)
def structural_benchmark():
    ready()
    try: dest=run_benchmark(ARTIFACTS)
    except SolverError as exc:raise HTTPException(503,str(exc))
    try:registry.register(dest)
    except (psycopg.Error,IntegrityError):raise HTTPException(503,{'message':'Benchmark artifacts retained; registration failed','run_id':dest.name})
    return {'run_id':dest.name,'validation_status':'benchmark_verified_only'}

@app.post('/runs/{run_id}/structural',status_code=201)
def analyze_bracket(run_id: UUID):
    ready()
    try:
        record=registry.get(run_id)
        if record is None:raise HTTPException(404,'Run not found')
        registry.verify(ARTIFACTS,run_id)
        if not (ARTIFACTS/str(run_id)/'geometry.json').is_file():raise HTTPException(422,'Select a native PicoGK bracket; the cantilever benchmark cannot be analyzed as a bracket')
        dest=analyze(ARTIFACTS,run_id,record)
    except IntegrityError as exc:raise HTTPException(409,str(exc))
    except BracketAnalysisError as exc:raise HTTPException(503,{'message':str(exc),'run_id':exc.run_id})
    except ValueError as exc:raise HTTPException(422,str(exc))
    except psycopg.Error:raise HTTPException(503,'Database unavailable')
    try:registry.register(dest)
    except (psycopg.Error,IntegrityError):raise HTTPException(503,{'message':'Analysis artifacts retained; registration failed','run_id':dest.name})
    return {'run_id':dest.name,'parent_design_id':str(run_id),'validation_status':__import__('json').loads((dest/'result.json').read_text())['validation_status']}

@app.get('/runs/{run_id}/displacement-surface')
def surface_field(run_id: UUID):
    from kcee.fields import displacement_surface
    try:
        registry.verify(ARTIFACTS,run_id)
        record=registry.get(run_id)
        if record['manifest'].get('kind')!='bracket_structural':raise HTTPException(422,'Displacement preview requires a bracket structural run')
        field=displacement_surface(ARTIFACTS/str(run_id)/'fea-artifacts.zip')
        field['source_archive_sha256']=record['manifest']['artifacts']['fea-artifacts.zip']
        return field
    except KeyError:raise HTTPException(404,'Unknown run')
    except IntegrityError:raise HTTPException(409,'Run integrity check failed')
    except (ValueError,zipfile.BadZipFile):raise HTTPException(422,'Solver field is incomplete')

class VisibilityRequest(BaseModel):
    confirm_run_id: UUID
    hidden: bool

@app.post('/runs/{run_id}/visibility')
def change_visibility(run_id: UUID,body: VisibilityRequest):
    if body.confirm_run_id!=run_id:raise HTTPException(422,'Confirmation does not match selected run')
    try:return registry.set_visibility(run_id,body.hidden)
    except KeyError:raise HTTPException(404,'Run not found')
    except psycopg.Error:raise HTTPException(503,'Database unavailable')

@app.get('/runs/{run_id}/geometry-measurements')
def geometry_measurements(run_id: UUID):
    import json
    from kcee.geometry_measure import hole_sections
    try:
        registry.verify(ARTIFACTS,run_id);record=registry.get(run_id);directory=ARTIFACTS/str(run_id)
        if 'geometry-request.json' not in record['manifest']['artifacts']:raise HTTPException(422,'Bore measurements require native PicoGK geometry')
        settings=json.loads((directory/'geometry-request.json').read_text())
        if settings['geometry_mm']!={'length':60,'width':30,'height':40,'thickness':3.5} or settings['hole_diameter_mm']!=5 or not settings['mounting_holes']:raise HTTPException(422,'Measurements currently support the default native bracket only')
        holes=[row for depth in (.875,1.75,2.625) for row in hole_sections(directory/'bracket.stl',depth)]
        return {'run_id':str(run_id),'source_stl_sha256':record['manifest']['artifacts']['bracket.stl'],'nominal_diameter_mm':5,'sections_mm':[.875,1.75,2.625],'holes':holes,'status':'measured_not_manufacturing_validated'}
    except KeyError:raise HTTPException(404,'Run not found or incomplete geometry metadata')
    except IntegrityError as exc:raise HTTPException(409,str(exc))
    except ValueError as exc:raise HTTPException(422,str(exc))
    except psycopg.Error:raise HTTPException(503,'Database unavailable')

@app.get('/runs/{run_id}/stress-diagnostics')
def stress_diagnostics(run_id: UUID):
    from kcee.stress_diagnostics import diagnose,regional_refinement
    try:
        registry.verify(ARTIFACTS,run_id);record=registry.get(run_id)
        if record['manifest'].get('kind')!='bracket_structural':raise HTTPException(422,'Diagnostics require a bracket structural run')
        result=diagnose(ARTIFACTS/str(run_id)/'fea-artifacts.zip')
        result['regional_refinement']=regional_refinement(ARTIFACTS/str(run_id)/'fea-artifacts.zip',result)
        import json
        from kcee.surface_load import stl_strip_area
        source_area=stl_strip_area(ARTIFACTS/str(run_id)/'bracket.stl');fea=json.loads((ARTIFACTS/str(run_id)/'fea.json').read_text())
        error=abs(fea['mesh_study'][-1]['load_patch_area_mm2']/source_area-1)
        result.update({'source_load_patch_area_mm2':source_area,'relative_source_load_patch_area_error':error,'source_load_patch_agreement':error<.05})
        result.update({'run_id':str(run_id),'source_archive_sha256':record['manifest']['artifacts']['fea-artifacts.zip']})
        return result
    except KeyError:raise HTTPException(404,'Unknown or incomplete run')
    except IntegrityError as exc:raise HTTPException(409,str(exc))
    except (ValueError,zipfile.BadZipFile) as exc:raise HTTPException(422,str(exc))
    except psycopg.Error:raise HTTPException(503,'Database unavailable')

@app.get('/failures')
def retained_failures(limit: int=Query(50,ge=1,le=100)):
    from kcee.failures import list_failures
    return {'items':list_failures(ARTIFACTS,limit),'limit':limit,'scope':'retained_local_failure_records'}


class ServiceControlRequest(BaseModel):
    action: Literal['start','stop']
    confirm_stop: bool=False

@app.get('/services/control')
def service_control_status():
    return {'available':available(os.environ.get('KCEE_CONTROL_QUEUE','/data/control/queue'),os.environ.get('KCEE_CONTROL_KEY','/data/control/key'))}

@app.post('/services/control',status_code=202)
def service_control(body: ServiceControlRequest,request: Request):
    from kcee.service_control import submit
    from kcee.geometry_queue import QueueError
    if request.headers.get('origin') not in ('http://localhost:5173','http://127.0.0.1:5173','http://localhost:8000','http://127.0.0.1:8000') or request.headers.get('x-kcee-control')!='1':raise HTTPException(403,'Service controls require the local KCEE website')
    if body.action=='stop' and not body.confirm_stop:raise HTTPException(422,'Confirm stopping the engineering services')
    try:return {'job_id':submit(body.action,os.environ.get('KCEE_CONTROL_QUEUE','/data/control/queue'),os.environ.get('KCEE_CONTROL_KEY','/data/control/key')),'status':'pending'}
    except QueueError as error:raise HTTPException(503,str(error))

@app.get('/services/control/{job_id}')
def service_control_result(job_id: UUID):
    from kcee.service_control import result
    from kcee.geometry_queue import QueueError
    try:return result(str(job_id),os.environ.get('KCEE_CONTROL_QUEUE','/data/control/queue'),os.environ.get('KCEE_CONTROL_KEY','/data/control/key'))
    except FileNotFoundError:raise HTTPException(404,'Unknown service control operation')
    except (QueueError,ValueError,OSError):raise HTTPException(503,'Service control response unavailable')
