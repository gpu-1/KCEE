"""Immutable local sources, verified PDF pages and hybrid document retrieval."""
import hashlib,json,re,uuid
from kcee.provenance import IntegrityError
MAX_BYTES=256*1024

def document_parts(name,raw):
    if not isinstance(name,str) or not 1<=len(name)<=120 or '/' in name or '\\' in name or any(ord(c)<32 for c in name) or not name.lower().endswith(('.txt','.md')):raise ValueError('Use a text or Markdown filename without path components')
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_BYTES:raise ValueError('Use a nonempty document up to 256 KB')
    try:text=raw.decode('utf-8')
    except UnicodeDecodeError:raise ValueError('Document must be UTF-8 text')
    if any(ord(char)<32 and char not in '\t\r\n' for char in text) or not text.strip():raise ValueError('Document must contain readable text')
    lines=text.splitlines(keepends=True)
    if len(lines)>5000 or any(len(line)>1800 for line in lines):raise ValueError('Use at most 5000 lines, each shorter than 1800 characters')
    chunks=[];start=1;content=''
    for index,line in enumerate(lines,1):
        if content and len(content)+len(line)>1800:
            chunks.append({'line_start':start,'line_end':index-1,'content':content,'chunk_sha256':hashlib.sha256(content.encode()).hexdigest()});start=index;content=''
        content+=line
    if content:chunks.append({'line_start':start,'line_end':len(lines),'content':content,'chunk_sha256':hashlib.sha256(content.encode()).hexdigest()})
    return hashlib.sha256(raw).hexdigest(),chunks

class Knowledge:
    def connect(self):
        from kcee.registry import Registry
        return Registry().connect()
    def ingest(self,name,raw,extraction=None,before_save=None,ocr_languages='eng+spa'):
        if isinstance(name,str) and name.lower().endswith('.pdf'):
            document_parts(name[:-4]+'.txt',b'validate filename')
            from kcee.pdf_text import extract_pdf
            extraction=extraction if extraction is not None else extract_pdf(raw,ocr_languages=ocr_languages);digest=hashlib.sha256(raw).hexdigest();chunks=[];offset=0
            for page in extraction['pages']:
                text=page['text']
                if text.strip():
                    _,parts=document_parts('page.txt',text.encode())
                    chunks.extend({**part,'line_start':part['line_start']+offset,'line_end':part['line_end']+offset,'page_number':page['page_number']} for part in parts)
                offset+=len(text.splitlines(keepends=True))
        else:digest,chunks=document_parts(name,raw)
        identifier=str(uuid.uuid4())
        if before_save:before_save()
        with self.connect() as conn:
            inserted=conn.execute('INSERT INTO local_documents(id,name,source_sha256,original_bytes) VALUES(%s,%s,%s,%s) ON CONFLICT(source_sha256) DO NOTHING RETURNING id',(identifier,name,digest,raw)).fetchone()
            if inserted:
                if extraction:
                    canonical=json.dumps(extraction,sort_keys=True,separators=(',',':'),ensure_ascii=True)
                    conn.execute('INSERT INTO local_pdf_extractions(document_id,extractor,extraction_sha256,extraction) VALUES(%s,%s,%s,%s::jsonb)',(identifier,extraction['extractor'],hashlib.sha256(canonical.encode()).hexdigest(),canonical))
                for chunk in chunks:conn.execute('INSERT INTO local_document_chunks(document_id,line_start,line_end,content,chunk_sha256,page_number) VALUES(%s,%s,%s,%s,%s,%s)',(identifier,chunk['line_start'],chunk['line_end'],chunk['content'],chunk['chunk_sha256'],chunk.get('page_number')))
            stored=conn.execute('SELECT id,name,source_sha256 FROM local_documents WHERE source_sha256=%s',(digest,)).fetchone()
        chunk_count=len(chunks)
        if not inserted:
            with self.connect() as conn:
                existing=conn.execute('SELECT extraction FROM local_pdf_extractions WHERE document_id=%s',(stored['id'],)).fetchone()
                chunk_count=conn.execute('SELECT count(*) AS n FROM local_document_chunks WHERE document_id=%s',(stored['id'],)).fetchone()['n']
            extraction=existing['extraction'] if existing else None
        return {**stored,'id':str(stored['id']),'deduplicated':not bool(inserted),'chunks':chunk_count,**({'page_count':extraction['page_count'],'empty_pages':extraction['empty_pages'],'ocr_pages':extraction.get('ocr_pages',[]),'ocr_languages':extraction.get('ocr_settings',{}).get('languages')} if extraction else {})}
    def list(self,include_archived=False):
        table='local_documents' if include_archived else 'active_local_documents'
        with self.connect() as conn:return conn.execute('SELECT d.id,d.name,d.source_sha256,d.created_at,octet_length(d.original_bytes) AS bytes,(SELECT count(*) FROM local_document_chunks c WHERE c.document_id=d.id) AS chunks,COALESCE((SELECT e.archived FROM document_visibility_events e WHERE e.document_id=d.id ORDER BY e.id DESC LIMIT 1),false) AS archived FROM '+table+' d ORDER BY d.created_at DESC LIMIT 100').fetchall()

    def library(self,include_archived=False,page=1,page_size=25,name='',file_type='all',sort='newest'):
        if type(page) is not int or page<1 or page>1000000 or type(page_size) is not int or page_size not in (10,25,50,100):raise ValueError('Invalid library page or page size')
        if not isinstance(name,str) or len(name)>200 or file_type not in ('all','pdf','md','txt'):raise ValueError('Invalid library filter')
        orders={'newest':'d.created_at DESC,d.id DESC','oldest':'d.created_at ASC,d.id ASC','name':'lower(d.name) ASC,d.id ASC','size':'octet_length(d.original_bytes) DESC,d.id ASC'}
        if sort not in orders:raise ValueError('Invalid library sort')
        table='local_documents' if include_archived else 'active_local_documents'
        where=" WHERE strpos(lower(d.name),lower(%s))>0 AND (%s='all' OR right(lower(d.name),length(%s)+1)='.'||%s)"
        params=(name.strip(),file_type,file_type,file_type)
        with self.connect() as conn:
            total=conn.execute('SELECT count(*) AS n FROM '+table+' d'+where,params).fetchone()['n']
            pages=max(1,(total+page_size-1)//page_size);page=min(page,pages)
            rows=conn.execute('SELECT d.id,d.name,d.source_sha256,d.created_at,octet_length(d.original_bytes) AS bytes,(SELECT count(*) FROM local_document_chunks c WHERE c.document_id=d.id) AS chunks,COALESCE((SELECT e.archived FROM document_visibility_events e WHERE e.document_id=d.id ORDER BY e.id DESC LIMIT 1),false) AS archived FROM '+table+' d'+where+' ORDER BY '+orders[sort]+' LIMIT %s OFFSET %s',(*params,page_size,(page-1)*page_size)).fetchall()
        return {'items':rows,'total':total,'page':page,'page_size':page_size,'pages':pages}

    def visibility(self,identifier,archived,source_sha256,confirmed=False):
        if type(archived) is not bool or (archived and confirmed is not True):raise ValueError('Archiving requires confirmation')
        row,raw=self.source(identifier)
        if row['source_sha256']!=source_sha256:raise IntegrityError('Document identity changed; refresh the library')
        with self.connect() as conn:
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(str(row['id']),))
            previous=conn.execute('SELECT archived FROM document_visibility_events WHERE document_id=%s ORDER BY id DESC LIMIT 1',(row['id'],)).fetchone()
            if bool(previous and previous['archived'])!=archived:conn.execute('INSERT INTO document_visibility_events(document_id,archived) VALUES(%s,%s)',(row['id'],archived))
        return {'id':str(row['id']),'name':row['name'],'source_sha256':row['source_sha256'],'archived':archived}

    def source(self,identifier):
        with self.connect() as conn:row=conn.execute('SELECT id,name,source_sha256,original_bytes FROM local_documents WHERE id=%s',(str(uuid.UUID(str(identifier))),)).fetchone()
        if row is None:raise KeyError('Document not found')
        raw=bytes(row['original_bytes'])
        if hashlib.sha256(raw).hexdigest()!=row['source_sha256']:raise IntegrityError('Document source hash mismatch')
        return row,raw
    def retrieve(self,question,with_metadata=False,document_id=None):
        if not isinstance(question,str) or not 1<=len(question.strip())<=800:raise ValueError('Use a question of 1 to 800 characters')
        if document_id is not None:document_id=str(uuid.UUID(str(document_id)))
        with self.connect() as conn:rows=conn.execute("SELECT c.id AS chunk_id,c.document_id,c.page_number,c.line_start,c.line_end,c.content,c.chunk_sha256,d.name,d.source_sha256 FROM local_document_chunks c JOIN active_local_documents d ON d.id=c.document_id WHERE (%s::uuid IS NULL OR d.id=%s::uuid) AND to_tsvector('english',c.content) @@ replace(plainto_tsquery('english',%s)::text,' & ',' | ')::tsquery ORDER BY ts_rank_cd(to_tsvector('english',c.content),replace(plainto_tsquery('english',%s)::text,' & ',' | ')::tsquery) DESC,c.id LIMIT 12",(document_id,document_id,question,question)).fetchall()
        from kcee.semantic_knowledge import retrieve
        rows,metadata=retrieve(self,question,rows,document_id=document_id)
        if document_id is not None:metadata['document_id']=document_id
        result=[]
        for index,row in enumerate(rows,1):
            source,raw=self.source(row['document_id']);lines,pdf=self.reference_lines(source,raw,[row.get('page_number')] if row.get('page_number') else None);excerpt=''.join(lines[row['line_start']-1:row['line_end']])
            if pdf and (type(row.get('page_number')) is not int or not 1<=row['page_number']<=pdf['page_count']):raise IntegrityError('Invalid PDF chunk page')
            if excerpt!=row['content'] or hashlib.sha256(excerpt.encode()).hexdigest()!=row['chunk_sha256']:raise IntegrityError('Document chunk differs from original source')
            result.append({'citation_id':'D'+str(index),'document_id':str(row['document_id']),'name':row['name'],'line_start':row['line_start'],'line_end':row['line_end'],'content':excerpt,'source_sha256':row['source_sha256'],'chunk_sha256':row['chunk_sha256'],**({'extractor':pdf['extractor'],'page_text_sha256':pdf['pages'][row['page_number']-1]['text_sha256'],'extraction_method':pdf['pages'][row['page_number']-1].get('method','embedded_text'),'ocr_languages':pdf.get('ocr_settings',{}).get('languages')} if pdf else {}),**{key:row[key] for key in ('page_number','chunk_id','cosine_similarity','embedding_vector_sha256','retrieval_ranks','hybrid_score') if key in row}})
        self.verify_citations(result)
        return (result,dict(metadata,matches=len(result))) if with_metadata else result
    def reference_lines(self,row,raw,page_numbers=None):
        if not row['name'].lower().endswith('.pdf'):return raw.decode('utf-8').splitlines(keepends=True),None
        with self.connect() as conn:saved=conn.execute('SELECT extraction,extraction_sha256,extractor FROM local_pdf_extractions WHERE document_id=%s',(row['id'],)).fetchone()
        if not saved:raise IntegrityError('PDF extraction record missing')
        canonical=json.dumps(saved['extraction'],sort_keys=True,separators=(',',':'),ensure_ascii=True)
        if hashlib.sha256(canonical.encode()).hexdigest()!=saved['extraction_sha256']:raise IntegrityError('PDF extraction hash mismatch')
        from kcee.pdf_text import extract_pdf,EXTRACTOR,LEGACY_EXTRACTOR,COMBINED_EXTRACTOR
        if saved['extractor'] not in (EXTRACTOR,LEGACY_EXTRACTOR,COMBINED_EXTRACTOR):raise IntegrityError('PDF extractor identity mismatch')
        pdf=saved['extraction']
        if saved['extractor']==LEGACY_EXTRACTOR:
            try:actual=extract_pdf(raw,LEGACY_EXTRACTOR)
            except ValueError as error:raise IntegrityError('PDF source cannot be verified') from error
            if actual!=pdf:raise IntegrityError('PDF extraction differs from original file')
        elif page_numbers:
            cache=getattr(self,'_pdf_page_cache',set())
            missing=[n for n in page_numbers if (row['source_sha256'],saved['extraction_sha256'],n) not in cache]
            if missing:
                try:actual=extract_pdf(raw,saved['extractor'],missing,ocr_languages=pdf.get('ocr_settings',{}).get('languages','eng+spa'))
                except ValueError as error:raise IntegrityError('PDF cited page cannot be verified') from error
                if actual['page_count']!=pdf['page_count']:raise IntegrityError('PDF page count mismatch')
                for page in actual['pages']:
                    if page!=pdf['pages'][page['page_number']-1]:raise IntegrityError('PDF cited page extraction mismatch')
                if actual.get('ocr_runtime_sha256') and actual['ocr_runtime_sha256']!=pdf.get('ocr_runtime_sha256'):raise IntegrityError('OCR runtime fingerprint mismatch')
                cache.update((row['source_sha256'],saved['extraction_sha256'],n) for n in missing);self._pdf_page_cache=cache
        return ''.join(page['text'] for page in pdf['pages']).splitlines(keepends=True),pdf

    def verify_citations(self,chunks):
        for chunk in chunks:
            row,raw=self.source(chunk['document_id']);lines,pdf=self.reference_lines(row,raw,[chunk.get('page_number')] if chunk.get('page_number') else None)
            if not 1<=chunk['line_start']<=chunk['line_end']<=len(lines) or row['name']!=chunk['name']:raise IntegrityError('Cited source name or line range mismatch')
            if pdf:
                offset=0;matching=False
                for page in pdf['pages']:
                    count=len(page['text'].splitlines(keepends=True))
                    if chunk.get('page_number')==page['page_number'] and offset<chunk['line_start']<=chunk['line_end']<=offset+count:
                        if 'ocr_languages' in chunk and chunk['ocr_languages']!=pdf.get('ocr_settings',{}).get('languages'):raise IntegrityError('PDF citation OCR language mismatch')
                        if ('extraction_method' in chunk and chunk['extraction_method']!=page.get('method','embedded_text')):raise IntegrityError('PDF citation OCR method mismatch')
                        if ('extractor' in chunk and chunk['extractor']!=pdf['extractor']) or ('page_text_sha256' in chunk and chunk['page_text_sha256']!=page['text_sha256']):raise IntegrityError('PDF extraction citation fingerprint mismatch')
                        matching=True
                    offset+=count
                if not matching:raise IntegrityError('Cited PDF page mismatch')
            elif chunk.get('page_number') is not None:raise IntegrityError('Unexpected PDF page citation')
            excerpt=''.join(lines[chunk['line_start']-1:chunk['line_end']])
            if row['source_sha256']!=chunk['source_sha256'] or excerpt!=chunk['content'] or hashlib.sha256(excerpt.encode()).hexdigest()!=chunk['chunk_sha256']:raise IntegrityError('Cited source mismatch')

def attach_documents(evidence,question):
    from kcee.geometry_queue import encoded
    evidence=dict(evidence);evidence['documents'],evidence['document_search']=Knowledge().retrieve(question,with_metadata=True)
    raw=encoded(evidence)
    if len(raw)>20000:raise ValueError('Combined study and document context exceeds bounded limit')
    return evidence,hashlib.sha256(raw).hexdigest()
