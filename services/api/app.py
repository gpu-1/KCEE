import zipfile
import logging
import threading
import os
from pathlib import Path
from uuid import UUID
import psycopg
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from pydantic import BaseModel, StrictInt
from typing import Literal
from kcee.picogk import GeometryError
from kcee.geometry_queue import available
from kcee.fea_run import run_benchmark,solver_available
from kcee.cfd_run import run_cfd,cfd_available
from kcee.thermal_run import run_thermal,thermal_available
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
    return {'geometry':{'mesh':True,'picogk':available(queue,key)},'cfd':{'plane_poiseuille':cfd_available(),'openfoam_vortex':cfd_available(True),'bracket_flow':cfd_available(bracket=True),'native_forces':cfd_available(native=True)},'thermal':{'steady_1d':thermal_available()},'structural':{'calculix':solver_available()},'validation':'demonstrator_only'}

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
    action: Literal['start','stop','voice_start','voice_stop','ai_start','ai_stop']
    confirm_stop: bool=False

@app.get('/services/control')
def service_control_status():
    from kcee.service_control import active_operation
    queue=os.environ.get('KCEE_CONTROL_QUEUE','/data/control/queue');key=os.environ.get('KCEE_CONTROL_KEY','/data/control/key')
    return {'available':available(queue,key),'operation':active_operation(queue,key)}

@app.post('/services/control',status_code=202)
def service_control(body: ServiceControlRequest,request: Request):
    from kcee.service_control import submit
    from kcee.geometry_queue import QueueError
    if request.headers.get('origin') not in ('http://localhost:5173','http://127.0.0.1:5173','http://localhost:8000','http://127.0.0.1:8000') or request.headers.get('x-kcee-control')!='1':raise HTTPException(403,'Service controls require the local KCEE website')
    if body.action in ('stop','voice_stop','ai_stop') and not body.confirm_stop:raise HTTPException(422,'Confirm stopping services')
    try:return {'job_id':submit(body.action,os.environ.get('KCEE_CONTROL_QUEUE','/data/control/queue'),os.environ.get('KCEE_CONTROL_KEY','/data/control/key')),'status':'pending'}
    except QueueError as error:raise HTTPException(503,str(error))

@app.get('/services/control/{job_id}')
def service_control_result(job_id: UUID):
    from kcee.service_control import result
    from kcee.geometry_queue import QueueError
    try:return result(str(job_id),os.environ.get('KCEE_CONTROL_QUEUE','/data/control/queue'),os.environ.get('KCEE_CONTROL_KEY','/data/control/key'))
    except FileNotFoundError:raise HTTPException(404,'Unknown service control operation')
    except (QueueError,ValueError,OSError):raise HTTPException(503,'Service control response unavailable')


@app.get('/runs/{run_id}/refinement-explorations')
def refinement_explorations(run_id: UUID):
    from kcee.explorations import recorded_explorations
    try:
        registry.verify(ARTIFACTS,run_id);record=registry.get(run_id)
        if record['manifest'].get('kind')!='bracket_structural':raise HTTPException(422,'Explorations require a bracket structural study')
        return {'run_id':str(run_id),'manifest_sha256':record['manifest_sha256'],'source_stl_sha256':record['manifest']['artifacts']['bracket.stl'],'items':recorded_explorations('/app/evidence',record,os.environ.get('KCEE_EXPLORATIONS_DIR','/data/explorations')),'scope':'recorded_exploratory_evidence_not_registered_studies','archive_verification':'Archives marked verified were hashed by the local API against recorded evidence; unavailable archives remain recorded evidence only'}
    except KeyError:raise HTTPException(404,'Unknown or incomplete study')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except ValueError as error:raise HTTPException(422,str(error))
    except OSError:raise HTTPException(503,'Exploratory archives cannot be read')
    except psycopg.Error:raise HTTPException(503,'Database unavailable')


@app.get('/runs/{run_id}/refinement-explorations/{key}/archive')
def exploratory_archive(run_id: UUID,key: Literal['global-1.3','root-0.9','root-0.75']):
    from kcee.explorations import verified_archive_bytes
    evidence=refinement_explorations(run_id)
    row=next((row for item in evidence['items'] for row in item['rows'] if row['download_key']==key),None)
    if row is None:raise HTTPException(404,'No source-linked exploratory archive for this study')
    try:
        raw=verified_archive_bytes(os.environ.get('KCEE_EXPLORATIONS_DIR','/data/explorations'),key,row['recorded_archive_sha256'])
        return Response(raw,media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="kcee-{run_id}-{key}.zip"','X-Archive-SHA256':row['recorded_archive_sha256']})
    except FileNotFoundError:raise HTTPException(404,'Exploratory archive unavailable on this Mac')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except OSError:raise HTTPException(503,'Exploratory archive cannot be read')


def voice_paths():return os.environ.get('KCEE_VOICE_QUEUE','/data/voice/queue'),os.environ.get('KCEE_VOICE_KEY','/data/voice/key')

@app.get('/voice/status')
def voice_status():
    return {'available':available(*voice_paths()),'backend':'native_kokoro','playback':'opt_in_browser_audio'}

@app.post('/runs/{run_id}/voice',status_code=202)
def prepare_voice(run_id: UUID,request: Request):
    import json
    from kcee.voice import submit_voice
    from kcee.geometry_queue import QueueError
    if request.headers.get('origin') not in ('http://localhost:5173','http://127.0.0.1:5173') or request.headers.get('x-kcee-voice')!='1':raise HTTPException(403,'Voice preparation requires the local KCEE website')
    try:
        registry.verify(ARTIFACTS,run_id);record=registry.get(run_id)
        summary=json.loads((ARTIFACTS/str(run_id)/'voice-summary.json').read_text())
        if summary.get('level') not in ('INFO','RESULT','WARNING','CRITICAL'):raise HTTPException(422,'This summary is not eligible for voice')
        return {'job_id':submit_voice(str(run_id),record['manifest']['artifacts']['voice-summary.json'],summary['text'],*voice_paths()),'status':'pending'}
    except KeyError:raise HTTPException(404,'Unknown run or missing voice summary')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except QueueError as error:raise HTTPException(503,str(error))
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Database unavailable')

def checked_voice_job(job_id):
    from kcee.voice import voice_result
    from kcee.geometry_queue import QueueError
    try:
        payload,raw=voice_result(str(job_id),*voice_paths())
        if payload['status']=='completed':
            run_id=UUID(payload['run_id']);registry.verify(ARTIFACTS,run_id);record=registry.get(run_id)
            if payload['summary_sha256']!=record['manifest']['artifacts']['voice-summary.json']:raise IntegrityError('Voice source summary mismatch')
        return payload,raw
    except FileNotFoundError:raise HTTPException(404,'Voice job missing or expired')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except (QueueError,ValueError,KeyError):raise HTTPException(409,'Voice response integrity failed')
    except OSError:raise HTTPException(503,'Voice queue unavailable')
    except psycopg.Error:raise HTTPException(503,'Database unavailable')

@app.get('/voice/jobs/{job_id}')
def get_voice_job(job_id: UUID):return checked_voice_job(job_id)[0]

@app.get('/voice/jobs/{job_id}/audio')
def voice_audio(job_id: UUID):
    payload,raw=checked_voice_job(job_id)
    if payload['status']!='completed':raise HTTPException(409,'Voice audio is not ready')
    return Response(raw,media_type='audio/wav',headers={'X-Audio-SHA256':payload['audio_sha256'],'Cache-Control':'no-store'})


def assistant_paths():return os.environ.get('KCEE_ASSISTANT_QUEUE','/data/assistant/queue'),os.environ.get('KCEE_ASSISTANT_KEY','/data/assistant/key')

@app.get('/assistant/status')
def assistant_status():
    from kcee.geometry_queue import read_signed,key_bytes
    ready=available(*assistant_paths());model=None
    if ready:
        try:model=read_signed(Path(assistant_paths()[0])/'heartbeat.json',key_bytes(assistant_paths()[1]),4096).get('model_sha256')
        except Exception:ready=False
    return {'available':ready,'model_sha256':model,'scope':'read_only_verified_structural_and_thermal_studies','backend':'native_llama_cpp_metal'}

class StudyQuestion(BaseModel):
    question: str
    include_documents: bool=False
    document_id: UUID | None=None
    document_ids: list[UUID] | None=None
    page_start: StrictInt | None=None
    page_end: StrictInt | None=None

@app.post('/runs/{run_id}/assistant',status_code=202)
def ask_study(run_id: UUID,body: StudyQuestion,request: Request):
    import json
    from kcee.study_assistant import study_evidence,submit_assistant
    from kcee.geometry_queue import QueueError
    if request.headers.get('origin') not in ('http://localhost:5173','http://127.0.0.1:5173') or request.headers.get('x-kcee-assistant')!='1':raise HTTPException(403,'Study AI requires the local KCEE website')
    if body.document_ids is not None and (body.document_id is not None or not 1<=len(body.document_ids)<=3 or len(set(body.document_ids))!=len(body.document_ids)):raise HTTPException(422,'Choose one to three different documents using one scope field')
    if (body.document_id is not None or body.document_ids is not None) and not body.include_documents:raise HTTPException(422,'Selected document requires document references')
    if (body.page_start is not None or body.page_end is not None) and (not body.include_documents or body.document_id is None or body.document_ids is not None):raise HTTPException(422,'Page bounds require one selected PDF reference')
    if not 1<=len(body.question.strip())<=800:raise HTTPException(422,'Use a question of 1 to 800 characters')
    try:
        registry.verify(ARTIFACTS,run_id);record=registry.get(run_id)
        kind=record['manifest'].get('kind')
        if kind not in ('bracket_structural','bracket_thermal','thermal_benchmark','cfd_benchmark'):raise HTTPException(422,'Study AI supports verified structural, thermal and channel studies')
        result=json.loads((ARTIFACTS/str(run_id)/'result.json').read_text())
        evidence,digest=study_evidence(record,result,stress_diagnostics(run_id) if kind=='bracket_structural' else {},refinement_explorations(run_id) if kind=='bracket_structural' else {'items':[]})
        if body.include_documents:
            from kcee.knowledge import attach_documents
            evidence,digest=attach_documents(evidence,body.question,body.document_id,body.document_ids,body.page_start,body.page_end)
        return {'job_id':submit_assistant(body.question,evidence,digest,*assistant_paths()),'evidence_sha256':digest,'status':'pending'}
    except KeyError:raise HTTPException(404,'Unknown or incomplete study')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except QueueError as error:raise HTTPException(503,str(error))
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Database unavailable')

@app.get('/assistant/jobs/{job_id}')
def get_study_answer(job_id: UUID):
    from kcee.study_assistant import assistant_result
    from kcee.geometry_queue import QueueError
    try:
        payload=assistant_result(str(job_id),*assistant_paths())
        if payload['status']=='completed':
            from kcee.knowledge import Knowledge
            Knowledge().verify_citations(payload['evidence'].get('documents',[]))
            source=payload['evidence']['source'];run_id=UUID(source['run_id']);registry.verify(ARTIFACTS,run_id);record=registry.get(run_id)
            if source['manifest_sha256']!=record['manifest_sha256'] or source['result_sha256']!=record['manifest']['artifacts']['result.json']:raise IntegrityError('Assistant saved source mismatch')
            from kcee.geometry_queue import encoded
            payload=dict(payload,evidence_canonical_json=encoded(payload['evidence']).decode('utf-8'))
        return payload
    except FileNotFoundError:raise HTTPException(404,'Assistant job missing or expired')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except (QueueError,KeyError,ValueError):raise HTTPException(409,'Assistant response integrity failed')
    except OSError:raise HTTPException(503,'Assistant queue unavailable')
    except psycopg.Error:raise HTTPException(503,'Database unavailable')

@app.post('/runs/thermal-benchmark',status_code=201)
def thermal_benchmark():
    ready()
    try:dest=run_thermal(ARTIFACTS)
    except Exception:raise HTTPException(503,'Thermal worker unavailable or benchmark reproduction failed')
    try:registry.register(dest)
    except (psycopg.Error,IntegrityError):raise HTTPException(503,{'message':'Thermal artifacts retained; registration failed','run_id':dest.name})
    return {'run_id':dest.name,'validation_status':'thermal_benchmark_verified_only'}

@app.post('/runs/{run_id}/thermal',status_code=201)
def bracket_thermal(run_id: UUID):
    from kcee.bracket_thermal_run import analyze_thermal
    ready()
    try:
        record=registry.get(run_id)
        if record is None:raise HTTPException(404,'Run not found')
        registry.verify(ARTIFACTS,run_id)
        if not (ARTIFACTS/str(run_id)/'geometry-request.json').is_file():raise HTTPException(422,'Select a native PicoGK bracket')
        dest=analyze_thermal(ARTIFACTS,run_id,record)
    except IntegrityError as error:raise HTTPException(409,str(error))
    except BracketAnalysisError as error:raise HTTPException(503,{'message':str(error),'run_id':error.run_id})
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Database unavailable')
    try:registry.register(dest)
    except (psycopg.Error,IntegrityError):raise HTTPException(503,{'message':'Thermal artifacts retained; registration failed','run_id':dest.name})
    return {'run_id':dest.name,'parent_design_id':str(run_id)}

@app.get('/runs/{run_id}/temperature-surface')
def thermal_surface(run_id: UUID):
    from kcee.bracket_thermal_run import temperature_surface
    import hashlib,json
    try:
        record=registry.get(run_id)
        if record is None:raise HTTPException(404,'Run not found')
        registry.verify(ARTIFACTS,run_id)
        if record['manifest'].get('kind')!='bracket_thermal':raise HTTPException(422,'Select a bracket thermal study')
        archive=ARTIFACTS/str(run_id)/'thermal-artifacts.zip';data=temperature_surface(archive)
        data.update({'run_id':str(run_id),'source_archive_sha256':record['manifest']['artifacts']['thermal-artifacts.zip']});return data
    except IntegrityError as error:raise HTTPException(409,str(error))
    except ValueError as error:raise HTTPException(409,str(error))
    except psycopg.Error:raise HTTPException(503,'Database unavailable')

@app.get('/knowledge/documents')
def knowledge_documents(include_archived: bool=False):
    from kcee.knowledge import Knowledge
    try:return {'items':Knowledge().list(include_archived),'retrieval':'local hybrid semantic and English keyword search when indexed'}
    except psycopg.Error:raise HTTPException(503,'Knowledge database unavailable or migration not installed')

@app.get('/knowledge/library')
def knowledge_library(include_archived: bool=False,page: int=1,page_size: int=25,name: str='',file_type: str='all',sort: str='newest'):
    from kcee.knowledge import Knowledge
    try:return Knowledge().library(include_archived,page,page_size,name,file_type,sort)
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Knowledge database unavailable')

@app.post('/knowledge/documents',status_code=201)
async def upload_knowledge(request: Request):
    import base64,json
    from kcee.knowledge import Knowledge
    if request.headers.get('origin') not in ('http://localhost:5173','http://127.0.0.1:5173') or request.headers.get('x-kcee-knowledge')!='1':raise HTTPException(403,'Document ingestion requires the local website')
    raw=bytearray()
    async for part in request.stream():
        raw.extend(part)
        if len(raw)>71000000:raise HTTPException(413,'Document request exceeds 50 MB source limit')
    try:
        data=json.loads(raw)
        if set(data)!={'name','bytes_base64'}:raise ValueError('Unexpected document fields')
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(Knowledge().ingest,data['name'],base64.b64decode(data['bytes_base64'],validate=True))
    except (ValueError,TypeError,KeyError) as error:raise HTTPException(422,str(error)[:250])
    except psycopg.Error:raise HTTPException(503,'Knowledge database unavailable or migration not installed')

@app.get('/knowledge/documents/{document_id}/source')
def knowledge_source(document_id: UUID, inline: bool = False):
    from kcee.knowledge import Knowledge
    try:
        row,raw=Knowledge().source(document_id)
        pdf=row['name'].lower().endswith('.pdf')
        if inline and not pdf:raise HTTPException(422,'Only PDF documents can be viewed inline')
        return Response(raw,media_type='application/pdf' if pdf else 'text/plain; charset=utf-8',headers={'X-Source-SHA256':row['source_sha256'],'X-Content-Type-Options':'nosniff','Content-Disposition':('inline' if inline else 'attachment')+'; filename="kcee-document.'+('pdf' if pdf else 'txt')+'"'})
    except KeyError:raise HTTPException(404,'Document not found')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except psycopg.Error:raise HTTPException(503,'Knowledge database unavailable')

@app.get('/knowledge/documents/{document_id}/pages/{page_number}/notes')
def page_review_notes(document_id: UUID,page_number: int,before: int | None=None):
    from kcee.page_notes import list_notes
    try:return list_notes(document_id,page_number,before)
    except KeyError:raise HTTPException(404,'Document not found')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Page review notes migration unavailable')

@app.get('/knowledge/documents/{document_id}/pages/{page_number}/notes/export')
def export_page_review_notes(document_id: UUID,page_number: int):
    from kcee.page_notes import export_notes
    try:return export_notes(document_id,page_number)
    except KeyError:raise HTTPException(404,'Document not found')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Page review notes migration unavailable')

@app.post('/knowledge/documents/{document_id}/pages/{page_number}/notes',status_code=201)
async def save_page_review_note(document_id: UUID,page_number: int,request: Request):
    from kcee.page_notes import save_note
    if request.headers.get('origin') not in ('http://localhost:5173','http://127.0.0.1:5173') or request.headers.get('x-kcee-knowledge')!='1':raise HTTPException(403,'Review notes require the local website')
    raw=bytearray()
    async for part in request.stream():
        raw.extend(part)
        if len(raw)>16384:raise HTTPException(413,'Review note is too large')
    try:
        import json
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(save_note,document_id,page_number,json.loads(raw))
    except KeyError:raise HTTPException(404,'Document not found')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except (ValueError,TypeError) as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Page review notes migration unavailable')

@app.get('/knowledge/semantic-status')
def knowledge_semantic_status():
    from kcee.knowledge import Knowledge
    from kcee.semantic_knowledge import coverage
    try:return coverage(Knowledge())
    except psycopg.Error:raise HTTPException(503,'Embedding index migration unavailable')

@app.post('/knowledge/index')
def index_knowledge(request: Request):
    from kcee.knowledge import Knowledge
    from kcee.semantic_knowledge import index
    from kcee.geometry_queue import QueueError
    if request.headers.get('origin') not in ('http://localhost:5173','http://127.0.0.1:5173') or request.headers.get('x-kcee-knowledge')!='1':raise HTTPException(403,'Indexing requires the local website')
    try:return index(Knowledge())
    except QueueError as error:raise HTTPException(503,str(error))
    except IntegrityError as error:raise HTTPException(409,str(error))
    except psycopg.Error:raise HTTPException(503,'Embedding database unavailable')

@app.get('/knowledge/documents/{document_id}/text')
def knowledge_extracted_text(document_id: UUID):
    from kcee.knowledge import Knowledge
    try:
        knowledge=Knowledge();row,raw=knowledge.source(document_id);lines,pdf=knowledge.reference_lines(row,raw)
        return {'name':row['name'],'source_sha256':row['source_sha256'],'pages':pdf['pages'] if pdf else None,'text':None if pdf else ''.join(lines),'extractor':pdf['extractor'] if pdf else None,'ocr_languages':pdf.get('ocr_settings',{}).get('languages') if pdf else None}
    except KeyError:raise HTTPException(404,'Document not found')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except psycopg.Error:raise HTTPException(503,'PDF extraction migration unavailable')

@app.post('/knowledge/imports',status_code=202)
async def start_document_import(request: Request):
    import base64,json
    from kcee.document_imports import imports
    if request.headers.get('origin') not in ('http://localhost:5173','http://127.0.0.1:5173') or request.headers.get('x-kcee-knowledge')!='1':raise HTTPException(403,'Import requires the local website')
    raw=bytearray()
    async for part in request.stream():
        raw.extend(part)
        if len(raw)>71000000:raise HTTPException(413,'Document request exceeds 50 MB source limit')
    try:
        data=json.loads(raw)
        if not {'name','bytes_base64'}<=set(data) or set(data)-{'name','bytes_base64','ocr_languages'}:raise ValueError('Unexpected document fields')
        return imports.start(data['name'],base64.b64decode(data['bytes_base64'],validate=True),data.get('ocr_languages','eng+spa'))
    except (ValueError,TypeError,KeyError) as error:raise HTTPException(422,str(error)[:250])
    except RuntimeError as error:raise HTTPException(409,str(error))

@app.get('/knowledge/imports/{import_id}')
def document_import_status(import_id: UUID):
    from kcee.document_imports import imports
    try:return imports.get(str(import_id))
    except KeyError:raise HTTPException(404,'Import unavailable; API may have restarted. Check local documents before retrying.')

@app.post('/knowledge/imports/{import_id}/cancel')
def cancel_document_import(import_id: UUID,request: Request):
    from kcee.document_imports import imports
    if request.headers.get('origin') not in ('http://localhost:5173','http://127.0.0.1:5173') or request.headers.get('x-kcee-knowledge')!='1':raise HTTPException(403,'Cancellation requires the local website')
    try:return imports.cancel(str(import_id))
    except KeyError:raise HTTPException(404,'Import not found')

@app.post('/knowledge/search')
async def search_local_documents(request: Request):
    from kcee.knowledge import Knowledge
    if request.headers.get('origin') not in ('http://localhost:5173','http://127.0.0.1:5173') or request.headers.get('x-kcee-knowledge')!='1':raise HTTPException(403,'Search requires the local website')
    raw=bytearray()
    async for part in request.stream():
        raw.extend(part)
        if len(raw)>8192:raise HTTPException(413,'Search request is too large')
    try:
        import json
        data=json.loads(raw)
        if 'question' not in data or set(data)-{'question','document_id','page_start','page_end'}:raise ValueError('Use a question and optional document identity')
        if data.get('document_id') is not None and not isinstance(data['document_id'],str):raise ValueError('Invalid document identity')
        document_id=str(UUID(data['document_id'])) if data.get('document_id') is not None else None
        from starlette.concurrency import run_in_threadpool
        passages,metadata=await run_in_threadpool(Knowledge().retrieve,data['question'],True,document_id,data.get('page_start'),data.get('page_end'))
        return {'passages':passages,'retrieval':metadata,'integrity':'verified'}
    except IntegrityError as error:raise HTTPException(409,str(error))
    except (ValueError,TypeError,KeyError) as error:raise HTTPException(422,str(error)[:200])
    except psycopg.Error:raise HTTPException(503,'Knowledge database unavailable')

@app.post('/knowledge/documents/{document_id}/visibility')
async def document_visibility(document_id: UUID,request: Request):
    from kcee.knowledge import Knowledge
    if request.headers.get('origin') not in ('http://localhost:5173','http://127.0.0.1:5173') or request.headers.get('x-kcee-knowledge')!='1':raise HTTPException(403,'Document changes require the local website')
    raw=bytearray()
    async for part in request.stream():
        raw.extend(part)
        if len(raw)>4096:raise HTTPException(413,'Visibility request is too large')
    try:
        import json
        data=json.loads(raw)
        if set(data)!={'archived','source_sha256','confirmed'}:raise ValueError('Unexpected visibility fields')
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(Knowledge().visibility,document_id,data['archived'],data['source_sha256'],data['confirmed'])
    except IntegrityError as error:raise HTTPException(409,str(error))
    except KeyError:raise HTTPException(404,'Document not found')
    except (ValueError,TypeError) as error:raise HTTPException(422,str(error)[:200])
    except psycopg.Error:raise HTTPException(503,'Document visibility migration unavailable')

@app.post('/knowledge/verify-export-records')
async def verify_export_records(request: Request):
    from kcee.export_verification import verify_records
    if request.headers.get('origin') not in ('http://localhost:5173','http://127.0.0.1:5173') or request.headers.get('x-kcee-knowledge')!='1':raise HTTPException(403,'Export source checks require the local website')
    raw=bytearray()
    async for part in request.stream():
        raw.extend(part)
        if len(raw)>16*1024*1024:raise HTTPException(413,'Export records exceed 16 MB')
    try:
        import json
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(verify_records,json.loads(raw))
    except KeyError:raise HTTPException(404,'An included local source or record is unavailable')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except (ValueError,TypeError,AttributeError,OverflowError) as error:raise HTTPException(422,'Invalid export records: '+str(error)[:150])
    except psycopg.Error:raise HTTPException(503,'Knowledge database or migration unavailable')

@app.get('/knowledge/import-state')
def document_import_state():
    from kcee.document_imports import imports
    with imports.lock:return {'active':[{'id':j['id'],'state':j['state']} for j in imports.jobs.values() if j['state'] in ('queued','extracting','saving')]}

@app.get('/backup-status')
def backup_status():
    from kcee.backup_status import recorded_status
    return recorded_status(os.environ.get('KCEE_BACKUP_STATUS_DIR','/data/backup-status'))

@app.get('/backup-coverage')
def backup_coverage():
    from datetime import datetime,timezone
    from kcee.backup_status import recorded_status
    from kcee.library_coverage import library_snapshot,compare_library
    saved=recorded_status(os.environ.get('KCEE_BACKUP_STATUS_DIR','/data/backup-status'))['backup']
    try:
        with registry.connect() as conn:
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            current=library_snapshot(conn)
    except psycopg.Error:raise HTTPException(503,'Current library comparison unavailable')
    return {**compare_library(saved,current),'checked_at':datetime.now(timezone.utc).isoformat(),'receipt':saved['record_name'] if saved else None,'current':current,'limitations':'Metadata comparison only; does not rehash original bytes or backup archives, cover saved searches in browser storage, or establish whole-project coverage.'}

@app.get('/transfer-readiness')
def get_transfer_readiness():
    from datetime import datetime,timezone
    from kcee.backup_status import recorded_status
    from kcee.library_coverage import library_snapshot
    from kcee.transfer_readiness import study_snapshot,transfer_readiness
    try:
        with registry.connect() as conn:
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            library=library_snapshot(conn);studies=study_snapshot(conn)
    except psycopg.Error:raise HTTPException(503,'Transfer inventory unavailable')
    return dict(transfer_readiness(recorded_status(os.environ.get('KCEE_BACKUP_STATUS_DIR','/data/backup-status')),library,studies),checked_at=datetime.now(timezone.utc).isoformat())

@app.post('/runs/cfd-benchmark',status_code=201)
def cfd_benchmark(body: dict | None=None):
    from kcee.cfd import case_inputs
    try:inputs=case_inputs(body)
    except ValueError as error:raise HTTPException(422,str(error))
    ready()
    try:dest=run_cfd(ARTIFACTS,inputs)
    except Exception:raise HTTPException(503,'CFD worker unavailable or numerical reproduction failed')
    try:registry.register(dest)
    except (psycopg.Error,IntegrityError):raise HTTPException(503,{'message':'CFD artifacts retained; registration failed','run_id':dest.name})
    return {'run_id':dest.name,'validation_status':'cfd_numerical_checks_passed_not_engineering_validated'}

@app.post('/runs/cfd-vortex',status_code=201)
def cfd_vortex(body: dict | None=None):
    if body:raise HTTPException(422,'OpenFOAM vortex uses a fixed reference case')
    ready()
    from kcee.vortex_run import run_vortex
    try:dest=run_vortex(ARTIFACTS)
    except Exception:raise HTTPException(503,'OpenFOAM worker unavailable or vortex verification failed')
    try:registry.register(dest)
    except (psycopg.Error,IntegrityError):raise HTTPException(503,{'message':'Vortex artifacts retained; registration failed','run_id':dest.name})
    return {'run_id':dest.name,'validation_status':'cfd_vortex_numerical_checks_passed_not_engineering_validated'}

@app.post('/runs/{run_id}/flow',status_code=201)
def bracket_external_flow(run_id: UUID,body: dict | None=None):
    import json
    from kcee.bracket_flow import MESHES
    if body and (set(body)-{'mesh_name','domain_name','bore_level','sampling_version','local_profile'} or not isinstance(body.get('mesh_name','coarse'),str) or body.get('mesh_name','coarse') not in MESHES or body.get('domain_name','base') not in ('base','expanded','far','outer') or body.get('sampling_version','compact-radius-v1') not in ('first-enclosing-v1','compact-radius-v1') or body.get('local_profile','baseline') not in ('baseline','wake-below-v1','wall-layers-v1') or type(body.get('bore_level',4)) is not int or body.get('bore_level',4) not in (4,5)):raise HTTPException(422,'Choose a supported mesh, domain and bore level 4 or 5')
    mesh_name=(body or {}).get('mesh_name','coarse')
    from kcee.bracket_flow import domain_spec,validate_profile
    try:
        domain_spec(mesh_name,(body or {}).get('domain_name','base'))
        validate_profile((body or {}).get('local_profile','baseline'),mesh_name,(body or {}).get('domain_name','base'),(body or {}).get('bore_level',4))
        if (body or {}).get('local_profile','baseline')!='baseline' and (body or {}).get('sampling_version','compact-radius-v1')!='compact-radius-v1':raise ValueError('Targeted refinement requires Compact v1 sampling')
    except ValueError as error:raise HTTPException(422,str(error))
    ready()
    from kcee.bracket_flow_run import run_bracket_flow,BracketFlowError
    try:
        registry.verify(ARTIFACTS,run_id);record=registry.get(run_id)
        if not (ARTIFACTS/str(run_id)/'geometry-request.json').is_file():raise HTTPException(422,'Select a native PicoGK bracket')
        dest=run_bracket_flow(ARTIFACTS,run_id,record,mesh_name,(body or {}).get('domain_name','base'),(body or {}).get('bore_level',4),(body or {}).get('sampling_version','compact-radius-v1'),(body or {}).get('local_profile','baseline'))
    except KeyError:raise HTTPException(404,'Unknown parent design')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except BracketFlowError as error:raise HTTPException(503,{'message':str(error),'run_id':error.run_id})
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Database unavailable')
    try:registry.register(dest)
    except (psycopg.Error,IntegrityError):raise HTTPException(503,{'message':'Bracket-flow artifacts retained; registration failed','run_id':dest.name})
    return {'run_id':dest.name,'validation_status':json.loads((dest/'result.json').read_text())['validation_status']}

@app.post('/runs/{run_id}/flow-refinement',status_code=201)
def bracket_flow_refinement(run_id: UUID,body: dict | None=None):
    if body:raise HTTPException(422,'Refinement uses a fixed three-mesh sequence')
    ready()
    from kcee.flow_refinement import run_refinement
    from kcee.bracket_flow_run import BracketFlowError
    try:
        registry.verify(ARTIFACTS,run_id);record=registry.get(run_id)
        if not (ARTIFACTS/str(run_id)/'geometry-request.json').is_file():raise HTTPException(422,'Select a native PicoGK bracket')
        dest=run_refinement(ARTIFACTS,run_id,record,registry);registry.register(dest)
    except KeyError:raise HTTPException(404,'Unknown parent design')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except BracketFlowError as error:raise HTTPException(503,{'message':str(error)+' Earlier completed mesh studies remain saved.','run_id':error.run_id})
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Database unavailable; completed studies and artifacts retained')
    return {'run_id':dest.name,'validation_status':'exploratory_bracket_flow_refinement_recorded_not_engineering_validated'}

@app.post('/runs/{run_id}/flow-domains',status_code=201)
def bracket_flow_domains(run_id: UUID,body: dict | None=None):
    if body:raise HTTPException(422,'Domain study uses fixed base, expanded and far domains at medium resolution')
    ready()
    from kcee.flow_domain import run_domains
    from kcee.bracket_flow_run import BracketFlowError
    try:
        registry.verify(ARTIFACTS,run_id);record=registry.get(run_id)
        if not (ARTIFACTS/str(run_id)/'geometry-request.json').is_file():raise HTTPException(422,'Select a native PicoGK bracket')
        dest=run_domains(ARTIFACTS,run_id,record,registry);registry.register(dest)
    except KeyError:raise HTTPException(404,'Unknown parent design')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except BracketFlowError as error:raise HTTPException(503,{'message':str(error)+' Earlier completed domain cases remain saved.','run_id':error.run_id})
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Database unavailable; completed source cases and artifacts retained')
    return {'run_id':dest.name,'validation_status':'exploratory_bracket_flow_domain_recorded_not_engineering_validated'}

@app.post('/runs/{run_id}/flow-combined',status_code=201)
def bracket_flow_combined(run_id: UUID,body: dict | None=None):
    if body:raise HTTPException(422,'Combined verification uses the fixed far-domain mesh sequence')
    ready()
    from kcee.flow_combined import run_combined
    from kcee.bracket_flow_run import BracketFlowError
    try:
        registry.verify(ARTIFACTS,run_id);record=registry.get(run_id)
        dest=run_combined(ARTIFACTS,run_id,record,registry);registry.register(dest)
    except KeyError:raise HTTPException(404,'Unknown source design or study')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except BracketFlowError as error:raise HTTPException(503,{'message':str(error)+' Completed studies remain saved.','run_id':error.run_id})
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Database unavailable; completed studies retained')
    return {'run_id':dest.name,'validation_status':'exploratory_bracket_flow_combined_recorded_not_engineering_validated'}


@app.post('/runs/{run_id}/flow-local-refinement',status_code=201)
def bracket_flow_local_refinement(run_id: UUID,body: dict | None=None):
    if body:raise HTTPException(422,'Local refinement uses the fixed wake/below boxes and Compact v1')
    ready()
    from kcee.flow_local_refinement import run_study
    from kcee.bracket_flow_run import BracketFlowError
    try:
        registry.verify(ARTIFACTS,run_id);record=registry.get(run_id)
        dest=run_study(ARTIFACTS,run_id,record,registry);registry.register(dest)
    except KeyError:raise HTTPException(404,'Unknown source design')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except BracketFlowError as error:raise HTTPException(503,{'message':str(error)+' Completed studies remain saved.','run_id':error.run_id})
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Database unavailable; completed studies retained')
    return {'run_id':dest.name,'validation_status':'exploratory_bracket_flow_local_recorded_not_engineering_validated'}


@app.post('/runs/{run_id}/flow-reference-study',status_code=201)
def bracket_flow_reference_study(run_id: UUID,body: dict | None=None):
    if body:raise HTTPException(422,'Reference study uses fixed probe pairs and a medium outer domain')
    ready()
    from kcee.flow_reference import run_study
    from kcee.bracket_flow_run import BracketFlowError
    try:
        registry.verify(ARTIFACTS,run_id);record=registry.get(run_id)
        dest=run_study(ARTIFACTS,run_id,record,registry);registry.register(dest)
    except KeyError:raise HTTPException(404,'Unknown source design')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except BracketFlowError as error:raise HTTPException(503,{'message':str(error)+' Completed studies remain saved.','run_id':error.run_id})
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Database unavailable; completed studies retained')
    return {'run_id':dest.name,'validation_status':'exploratory_bracket_flow_reference_not_engineering_validated'}


@app.post('/runs/{run_id}/flow-joint-study',status_code=201)
def bracket_flow_joint_study(run_id: UUID,body: dict | None=None):
    if body:raise HTTPException(422,'Joint study uses the fixed six-case recipe')
    ready()
    from kcee.flow_reference import run_study
    from kcee.bracket_flow_run import BracketFlowError
    try:
        registry.verify(ARTIFACTS,run_id);record=registry.get(run_id)
        dest=run_study(ARTIFACTS,run_id,record,registry,include_fine_outer=True);registry.register(dest)
    except KeyError:raise HTTPException(404,'Unknown source design')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except BracketFlowError as error:raise HTTPException(503,{'message':str(error)+' Completed studies remain saved.','run_id':error.run_id})
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Database unavailable; completed studies retained')
    return {'run_id':dest.name,'validation_status':'exploratory_bracket_flow_reference_not_engineering_validated'}


@app.post('/runs/{run_id}/layer-forces',status_code=201)
def bracket_layer_force_study(run_id: UUID,body: dict | None=None):
    ready()
    if body:raise HTTPException(422,'Layer study uses fixed inputs')
    from kcee.layer_forces_run import run_study
    try:
        dest=run_study(ARTIFACTS,run_id,registry);registry.register(dest)
    except KeyError:raise HTTPException(404,'Unknown layer-study source')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Database unavailable; completed studies retained')
    return {'run_id':dest.name,'validation_status':'exploratory_native_full_stress_not_engineering_validated'}

@app.post('/runs/{run_id}/native-forces',status_code=201)
def bracket_native_force_study(run_id: UUID,body: dict | None=None):
    ready()
    if body:raise HTTPException(422,'Native forces use fixed inputs')
    from kcee.native_forces_run import run_study
    try:
        dest=run_study(ARTIFACTS,run_id,registry);registry.register(dest)
    except KeyError:raise HTTPException(404,'Unknown native-force source')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Database unavailable; completed studies retained')
    return {'run_id':dest.name,'validation_status':'exploratory_native_full_stress_not_engineering_validated'}

@app.get('/runs/{run_id}/native-force-verification')
def native_force_verification(run_id: UUID):
    ready()
    from kcee.native_forces_run import verify_study
    try:return verify_study(ARTIFACTS,run_id,registry)
    except KeyError:raise HTTPException(404,'Unknown native force study')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except ValueError as error:raise HTTPException(422,str(error))

@app.post('/runs/{run_id}/flow-forces',status_code=201)
def bracket_force_study(run_id: UUID,body: dict | None=None):
    ready()
    if body:raise HTTPException(422,'Force studies use fixed inputs')
    from kcee.flow_forces_run import run_study
    try:
        dest=run_study(ARTIFACTS,run_id,registry);registry.register(dest)
    except KeyError:raise HTTPException(404,'Unknown source design')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except ValueError as error:raise HTTPException(422,str(error))
    except psycopg.Error:raise HTTPException(503,'Database unavailable; completed studies retained')
    return {'run_id':dest.name,'validation_status':'exploratory_wall_force_estimate_not_engineering_validated'}

@app.get('/runs/{run_id}/force-verification')
def bracket_force_verification(run_id: UUID):
    ready()
    from kcee.flow_forces_run import verify_study
    try:return verify_study(ARTIFACTS,run_id,registry)
    except KeyError:raise HTTPException(404,'Unknown force study')
    except IntegrityError as error:raise HTTPException(409,str(error))
    except ValueError as error:raise HTTPException(422,str(error))

# A single process owns durable CFD orchestration; solver work stays in the CFD worker.
_cfd_jobs=None
_cfd_jobs_lock=threading.Lock()
def cfd_job_manager():
    global _cfd_jobs
    with _cfd_jobs_lock:
        if _cfd_jobs is None:
            from kcee.cfd_jobs import Jobs
            def execute(kind,parent,options):
                functions={'flow':bracket_external_flow,'refinement':bracket_flow_refinement,'domains':bracket_flow_domains,'combined':bracket_flow_combined,'local':bracket_flow_local_refinement,'reference':bracket_flow_reference_study,'joint':bracket_flow_joint_study,'forces':bracket_force_study,'native_forces':bracket_native_force_study,'layer_forces':bracket_layer_force_study}
                return cfd_vortex() if kind=='vortex' else functions[kind](UUID(parent),options)
            _cfd_jobs=Jobs(os.environ.get('KCEE_CFD_JOBS_DIR','/data/cfd-jobs'),execute)
        return _cfd_jobs
@app.on_event('startup')
def recover_cfd_jobs():cfd_job_manager()

class CFDJobRequest(BaseModel):
    kind: Literal['flow','refinement','domains','combined','local','reference','joint','vortex','forces','native_forces','layer_forces']
    parent_id: UUID | None=None
    options: dict={}

@app.get('/cfd-jobs')
def list_cfd_jobs():return {'items':cfd_job_manager().list()}
@app.get('/cfd-jobs/{job_id}')
def get_cfd_job(job_id: UUID):
    try:return cfd_job_manager().get(str(job_id))
    except KeyError:raise HTTPException(404,'Unknown CFD job')
@app.post('/cfd-jobs',status_code=202)
def start_cfd_job(body: CFDJobRequest):
    ready()
    from kcee.cfd_jobs import validate
    try:
        validate(body.kind,body.parent_id,body.options)
        if body.parent_id:
            registry.verify(ARTIFACTS,body.parent_id)
            if not (ARTIFACTS/str(body.parent_id)/'geometry-request.json').is_file():raise ValueError('Select a native PicoGK bracket')
        return cfd_job_manager().start(body.kind,body.parent_id,body.options)
    except RuntimeError as error:raise HTTPException(409,str(error))
    except (ValueError,TypeError) as error:raise HTTPException(422,str(error))
    except KeyError:raise HTTPException(404,'Unknown parent design')
    except IntegrityError as error:raise HTTPException(409,str(error))
@app.post('/cfd-jobs/{job_id}/cancel')
def cancel_cfd_job(job_id: UUID):
    try:return cfd_job_manager().cancel(str(job_id))
    except KeyError:raise HTTPException(404,'Unknown CFD job')
@app.post('/cfd-jobs/{job_id}/retry',status_code=202)
def retry_cfd_job(job_id: UUID):
    ready()
    try:return cfd_job_manager().retry(str(job_id))
    except KeyError:raise HTTPException(404,'Unknown CFD job')
    except RuntimeError as error:raise HTTPException(409,str(error))
    except ValueError as error:raise HTTPException(422,str(error))
