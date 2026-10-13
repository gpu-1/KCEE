import logging
import os
from pathlib import Path
from uuid import UUID
import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
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

@app.post('/runs/bracket',status_code=201)
def bracket():
    ready()
    dest=run(ARTIFACTS)
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
