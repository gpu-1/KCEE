"""One cancellable local import at a time; atomic registration after extraction."""
import copy,threading,time,uuid
from kcee.knowledge import Knowledge,document_parts
from kcee.pdf_text import MAX_PDF_BYTES,extract_pdf,ImportCancelled

class Imports:
    def __init__(self):self.lock=threading.RLock();self.jobs={}
    def start(self,name,raw):
        pdf=isinstance(name,str) and name.lower().endswith('.pdf')
        document_parts(name[:-4]+'.txt' if pdf else name,b'validate filename' if pdf else raw)
        if pdf and (not isinstance(raw,bytes) or not 0<len(raw)<=MAX_PDF_BYTES or not raw.startswith(b'%PDF-')):raise ValueError('Use a PDF up to 50 MB')
        with self.lock:
            self.jobs={key:value for key,value in self.jobs.items() if value['state'] not in ('completed','failed','cancelled') or time.time()-value['updated_at']<3600}
            if any(j['state'] in ('queued','extracting','saving') for j in self.jobs.values()):raise RuntimeError('Another document import is active')
            if len(self.jobs)>=20:raise RuntimeError('Import history is full; retry after older entries expire')
            identifier=str(uuid.uuid4());self.jobs[identifier]={'id':identifier,'name':name,'state':'queued','completed_pages':0,'total_pages':None,'stage':'queued','updated_at':time.time(),'cancel_event':threading.Event()}
            threading.Thread(target=self._run,args=(identifier,name,raw,pdf),daemon=True).start()
            return self.get(identifier)
    def get(self,identifier):
        with self.lock:
            job=self.jobs[identifier]
            return copy.deepcopy({key:value for key,value in job.items() if key!='cancel_event'})
    def cancel(self,identifier):
        with self.lock:
            job=self.jobs[identifier]
            accepted=job['state'] in ('queued','extracting')
            if accepted:job['cancel_event'].set();job['stage']='cancelling'
            return {**self.get(identifier),'cancel_accepted':accepted}
    def _run(self,identifier,name,raw,pdf):
        with self.lock:job=self.jobs[identifier];event=job['cancel_event'];job['state']='extracting'
        def progress(value):
            with self.lock:
                if not event.is_set():job.update(value);job['updated_at']=time.time()
        def save_gate():
            with self.lock:
                if event.is_set():raise ImportCancelled('Import cancelled')
                job['state']='saving';job['stage']='saving';job['updated_at']=time.time()
        try:
            extraction=extract_pdf(raw,cancel_event=event,progress=progress) if pdf else None
            result=Knowledge().ingest(name,raw,extraction=extraction,before_save=save_gate)
            with self.lock:job.update(state='completed',stage='completed',result=result,updated_at=time.time())
        except ImportCancelled:
            with self.lock:job.update(state='cancelled',stage='cancelled',updated_at=time.time())
        except Exception as error:
            with self.lock:job.update(state='failed',stage='failed',error=str(error)[:250] if isinstance(error,ValueError) else 'Import failed; no partial document saved',updated_at=time.time())

imports=Imports()
