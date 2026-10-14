"""Signed native gateway to a private loopback-only Metal model server."""
import fcntl,hashlib,json,os,signal,sys,threading,time,urllib.request,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.geometry_queue import atomic_write,envelope,key_bytes,read_signed
from kcee.study_assistant import validate_assistant_request,validate_answer,SYSTEM,SOURCE_KEYS,DOCUMENT_SYSTEM
root=Path(__file__).resolve().parents[1];local=root/'.local/assistant';queue=local/'queue';key=key_bytes(local/'key');runtime=root/'.local/ai';manifest=json.loads((runtime/'runtime-manifest.json').read_text());server_key=(runtime/'server.key').read_text().strip()
lock=(local/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
stop=threading.Event();signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
def server_request(path,body=None,timeout=5):
    request=urllib.request.Request('http://127.0.0.1:8081'+path,data=json.dumps(body).encode() if body else None,headers={'Authorization':'Bearer '+server_key,'Content-Type':'application/json'})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=timeout) as response:return json.load(response)
def heartbeat():
    while not stop.is_set():
        try:ready=any(model.get('id')=='kcee-study-qwen3-4b' for model in server_request('/v1/models').get('data',[]))
        except Exception:ready=False
        atomic_write(queue/'heartbeat.json',envelope({'state':'ready' if ready else 'unavailable','pid':os.getpid(),'created_at':time.time(),'model_sha256':manifest['model_sha256']},key));stop.wait(2)
thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
schema={'type':'object','properties':{'answer':{'type':'string'},'source_keys':{'type':'array','items':{'type':'string','enum':list(SOURCE_KEYS)}}},'required':['answer','source_keys'],'additionalProperties':False}
try:
    while not stop.is_set():
        for path in sorted(queue.glob('*.request.json')):
            try:
                job_id=str(uuid.UUID(path.name.removesuffix('.request.json')));payload=validate_assistant_request(read_signed(path,key,32768),job_id);claimed=queue/(job_id+'.processing.json');path.rename(claimed)
                if (queue/(job_id+'.response.json')).exists():claimed.unlink();continue
            except (OSError,ValueError,KeyError,TypeError,RuntimeError):path.unlink(missing_ok=True);continue
            candidate=None
            try:
                document_keys=[chunk['citation_id'] for chunk in payload['evidence'].get('documents',[])];with_documents=bool(document_keys);system=DOCUMENT_SYSTEM if with_documents else SYSTEM
                if 'document_search' in payload['evidence'] and not document_keys:system+=' No local document passages matched this question. Do not invent document information or citations. Return only answer and source_keys; document_citations is not part of this empty-source response.'
                answer_schema=json.loads(json.dumps(schema));answer_schema['properties']['source_keys']['items']['enum']=[key for key in SOURCE_KEYS if key!='documents' or document_keys]
                if with_documents:
                    answer_schema['properties']['document_citations']={'type':'array','items':{'type':'string','enum':document_keys} if document_keys else {'type':'string'},'maxItems':len(document_keys)};answer_schema['required'].append('document_citations')
                request={'model':'kcee-study-qwen3-4b','messages':[{'role':'system','content':system},{'role':'user','content':json.dumps({'verified_evidence':payload['evidence'],'question':payload['question']},ensure_ascii=False)}],'temperature':.1,'seed':42,'max_tokens':768,'chat_template_kwargs':{'enable_thinking':False},'response_format':{'type':'json_schema','json_schema':{'name':'study_explanation','strict':True,'schema':answer_schema}}}
                result=server_request('/v1/chat/completions',request,timeout=150);candidate=json.loads(result['choices'][0]['message']['content']);answer=validate_answer(candidate,document_keys if with_documents else None)
                response={'job_id':job_id,'status':'completed','question':payload['question'],'evidence':payload['evidence'],'evidence_sha256':payload['evidence_sha256'],'answer':answer,'model':manifest['model'],'model_sha256':manifest['model_sha256'],'runtime_manifest_sha256':hashlib.sha256((runtime/'runtime-manifest.json').read_bytes()).hexdigest(),'system_prompt_sha256':hashlib.sha256(system.encode()).hexdigest(),'generation_settings':{'temperature':.1,'seed':42,'maximum_output_tokens':768,'thinking':False},'validation':'AI explanation draft; engineering acceptance remains pending'}
            except Exception as error:
                with (local/'inference.log').open('a') as log:log.write(str(error)+'\n')
                response={'job_id':job_id,'status':'failed','message':'Local AI explanation failed; inspect .local/assistant/inference.log'}
            atomic_write(queue/(job_id+'.response.json'),envelope(response,key));claimed.unlink(missing_ok=True)
        for path in queue.glob('*.response.json'):
            if time.time()-path.stat().st_mtime>86400:path.unlink(missing_ok=True)
        stop.wait(.2)
finally:
    stop.set();thread.join(timeout=6);atomic_write(queue/'heartbeat.json',envelope({'state':'stopped','pid':os.getpid(),'created_at':time.time()},key))
