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
    def ingest(self,name,raw):
        extraction=None
        if isinstance(name,str) and name.lower().endswith('.pdf'):
            document_parts(name[:-4]+'.txt',b'validate filename')
            from kcee.pdf_text import extract_pdf
            extraction=extract_pdf(raw);digest=hashlib.sha256(raw).hexdigest();chunks=[];offset=0
            for page in extraction['pages']:
                text=page['text']
                if text.strip():
                    _,parts=document_parts('page.txt',text.encode())
                    chunks.extend({**part,'line_start':part['line_start']+offset,'line_end':part['line_end']+offset,'page_number':page['page_number']} for part in parts)
                offset+=len(text.splitlines(keepends=True))
        else:digest,chunks=document_parts(name,raw)
        identifier=str(uuid.uuid4())
        with self.connect() as conn:
            inserted=conn.execute('INSERT INTO local_documents(id,name,source_sha256,original_bytes) VALUES(%s,%s,%s,%s) ON CONFLICT(source_sha256) DO NOTHING RETURNING id',(identifier,name,digest,raw)).fetchone()
            if inserted:
                if extraction:
                    canonical=json.dumps(extraction,sort_keys=True,separators=(',',':'),ensure_ascii=True)
                    conn.execute('INSERT INTO local_pdf_extractions(document_id,extractor,extraction_sha256,extraction) VALUES(%s,%s,%s,%s::jsonb)',(identifier,extraction['extractor'],hashlib.sha256(canonical.encode()).hexdigest(),canonical))
                for chunk in chunks:conn.execute('INSERT INTO local_document_chunks(document_id,line_start,line_end,content,chunk_sha256,page_number) VALUES(%s,%s,%s,%s,%s,%s)',(identifier,chunk['line_start'],chunk['line_end'],chunk['content'],chunk['chunk_sha256'],chunk.get('page_number')))
            stored=conn.execute('SELECT id,name,source_sha256 FROM local_documents WHERE source_sha256=%s',(digest,)).fetchone()
        return {**stored,'id':str(stored['id']),'deduplicated':not bool(inserted),'chunks':len(chunks),**({'page_count':extraction['page_count'],'empty_pages':extraction['empty_pages'],'ocr_pages':extraction.get('ocr_pages',[])} if extraction else {})}
    def list(self):
        with self.connect() as conn:return conn.execute('SELECT d.id,d.name,d.source_sha256,d.created_at,octet_length(d.original_bytes) AS bytes,count(c.id) AS chunks FROM local_documents d JOIN local_document_chunks c ON c.document_id=d.id GROUP BY d.id ORDER BY d.created_at DESC LIMIT 100').fetchall()
    def source(self,identifier):
        with self.connect() as conn:row=conn.execute('SELECT id,name,source_sha256,original_bytes FROM local_documents WHERE id=%s',(str(uuid.UUID(str(identifier))),)).fetchone()
        if row is None:raise KeyError('Document not found')
        raw=bytes(row['original_bytes'])
        if hashlib.sha256(raw).hexdigest()!=row['source_sha256']:raise IntegrityError('Document source hash mismatch')
        return row,raw
    def retrieve(self,question,with_metadata=False):
        if not isinstance(question,str) or not 1<=len(question.strip())<=800:raise ValueError('Use a question of 1 to 800 characters')
        with self.connect() as conn:rows=conn.execute("SELECT c.id AS chunk_id,c.document_id,c.page_number,c.line_start,c.line_end,c.content,c.chunk_sha256,d.name,d.source_sha256 FROM local_document_chunks c JOIN local_documents d ON d.id=c.document_id WHERE to_tsvector('english',c.content) @@ replace(plainto_tsquery('english',%s)::text,' & ',' | ')::tsquery ORDER BY ts_rank_cd(to_tsvector('english',c.content),replace(plainto_tsquery('english',%s)::text,' & ',' | ')::tsquery) DESC,c.id LIMIT 12",(question,question)).fetchall()
        from kcee.semantic_knowledge import retrieve
        rows,metadata=retrieve(self,question,rows)
        result=[]
        for index,row in enumerate(rows,1):
            source,raw=self.source(row['document_id']);lines,pdf=self.reference_lines(source,raw,[row.get('page_number')] if row.get('page_number') else None);excerpt=''.join(lines[row['line_start']-1:row['line_end']])
            if pdf and (type(row.get('page_number')) is not int or not 1<=row['page_number']<=pdf['page_count']):raise IntegrityError('Invalid PDF chunk page')
            if excerpt!=row['content'] or hashlib.sha256(excerpt.encode()).hexdigest()!=row['chunk_sha256']:raise IntegrityError('Document chunk differs from original source')
            result.append({'citation_id':'D'+str(index),'document_id':str(row['document_id']),'name':row['name'],'line_start':row['line_start'],'line_end':row['line_end'],'content':excerpt,'source_sha256':row['source_sha256'],'chunk_sha256':row['chunk_sha256'],**({'extractor':pdf['extractor'],'page_text_sha256':pdf['pages'][row['page_number']-1]['text_sha256'],'extraction_method':pdf['pages'][row['page_number']-1].get('method','embedded_text')} if pdf else {}),**{key:row[key] for key in ('page_number','chunk_id','cosine_similarity','embedding_vector_sha256','retrieval_ranks','hybrid_score') if key in row}})
        self.verify_citations(result)
        return (result,dict(metadata,matches=len(result))) if with_metadata else result
    def reference_lines(self,row,raw,page_numbers=None):
        if not row['name'].lower().endswith('.pdf'):return raw.decode('utf-8').splitlines(keepends=True),None
        with self.connect() as conn:saved=conn.execute('SELECT extraction,extraction_sha256,extractor FROM local_pdf_extractions WHERE document_id=%s',(row['id'],)).fetchone()
        if not saved:raise IntegrityError('PDF extraction record missing')
        canonical=json.dumps(saved['extraction'],sort_keys=True,separators=(',',':'),ensure_ascii=True)
        if hashlib.sha256(canonical.encode()).hexdigest()!=saved['extraction_sha256']:raise IntegrityError('PDF extraction hash mismatch')
        from kcee.pdf_text import extract_pdf,EXTRACTOR,LEGACY_EXTRACTOR
        if saved['extractor'] not in (EXTRACTOR,LEGACY_EXTRACTOR):raise IntegrityError('PDF extractor identity mismatch')
        pdf=saved['extraction']
        if saved['extractor']==LEGACY_EXTRACTOR:
            try:actual=extract_pdf(raw,LEGACY_EXTRACTOR)
            except ValueError as error:raise IntegrityError('PDF source cannot be verified') from error
            if actual!=pdf:raise IntegrityError('PDF extraction differs from original file')
        elif page_numbers:
            cache=getattr(self,'_pdf_page_cache',set())
            missing=[n for n in page_numbers if (row['source_sha256'],saved['extraction_sha256'],n) not in cache]
            if missing:
                try:actual=extract_pdf(raw,EXTRACTOR,missing)
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
