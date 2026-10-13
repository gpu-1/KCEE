import logging
import os
from pathlib import Path
from uuid import UUID
import psycopg
from fastapi import FastAPI, HTTPException, Query
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
def list_runs(limit: int=Query(50,ge=1,le=100),offset: int=Query(0,ge=0)):
    try: return {'items':registry.list(limit,offset),'limit':limit,'offset':offset}
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
