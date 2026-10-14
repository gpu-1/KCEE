"""Local immutable UTF-8 sources, line-preserving chunks and lexical retrieval."""
import hashlib,re,uuid
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
        digest,chunks=document_parts(name,raw);identifier=str(uuid.uuid4())
        with self.connect() as conn:
            inserted=conn.execute('INSERT INTO local_documents(id,name,source_sha256,original_bytes) VALUES(%s,%s,%s,%s) ON CONFLICT(source_sha256) DO NOTHING RETURNING id',(identifier,name,digest,raw)).fetchone()
            if inserted:
                for chunk in chunks:conn.execute('INSERT INTO local_document_chunks(document_id,line_start,line_end,content,chunk_sha256) VALUES(%s,%s,%s,%s,%s)',(identifier,chunk['line_start'],chunk['line_end'],chunk['content'],chunk['chunk_sha256']))
            stored=conn.execute('SELECT id,name,source_sha256 FROM local_documents WHERE source_sha256=%s',(digest,)).fetchone()
        return {**stored,'id':str(stored['id']),'deduplicated':not bool(inserted),'chunks':len(chunks)}
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
        with self.connect() as conn:rows=conn.execute("SELECT c.id AS chunk_id,c.document_id,c.line_start,c.line_end,c.content,c.chunk_sha256,d.name,d.source_sha256 FROM local_document_chunks c JOIN local_documents d ON d.id=c.document_id WHERE to_tsvector('english',c.content) @@ replace(plainto_tsquery('english',%s)::text,' & ',' | ')::tsquery ORDER BY ts_rank_cd(to_tsvector('english',c.content),replace(plainto_tsquery('english',%s)::text,' & ',' | ')::tsquery) DESC,c.id LIMIT 12",(question,question)).fetchall()
        from kcee.semantic_knowledge import retrieve
        rows,metadata=retrieve(self,question,rows)
        result=[]
        for index,row in enumerate(rows,1):
            source,raw=self.source(row['document_id']);lines=raw.decode('utf-8').splitlines(keepends=True);excerpt=''.join(lines[row['line_start']-1:row['line_end']])
            if excerpt!=row['content'] or hashlib.sha256(excerpt.encode()).hexdigest()!=row['chunk_sha256']:raise IntegrityError('Document chunk differs from original source')
            result.append({'citation_id':'D'+str(index),'document_id':str(row['document_id']),'name':row['name'],'line_start':row['line_start'],'line_end':row['line_end'],'content':excerpt,'source_sha256':row['source_sha256'],'chunk_sha256':row['chunk_sha256'],**{key:row[key] for key in ('chunk_id','cosine_similarity','embedding_vector_sha256','retrieval_ranks','hybrid_score') if key in row}})
        return (result,dict(metadata,matches=len(result))) if with_metadata else result
    def verify_citations(self,chunks):
        for chunk in chunks:
            row,raw=self.source(chunk['document_id']);lines=raw.decode('utf-8').splitlines(keepends=True)
            if not 1<=chunk['line_start']<=chunk['line_end']<=len(lines) or row['name']!=chunk['name']:raise IntegrityError('Cited source name or line range mismatch')
            excerpt=''.join(lines[chunk['line_start']-1:chunk['line_end']])
            if row['source_sha256']!=chunk['source_sha256'] or excerpt!=chunk['content'] or hashlib.sha256(excerpt.encode()).hexdigest()!=chunk['chunk_sha256']:raise IntegrityError('Cited source mismatch')

def attach_documents(evidence,question):
    from kcee.geometry_queue import encoded
    evidence=dict(evidence);evidence['documents'],evidence['document_search']=Knowledge().retrieve(question,with_metadata=True)
    raw=encoded(evidence)
    if len(raw)>20000:raise ValueError('Combined study and document context exceeds bounded limit')
    return evidence,hashlib.sha256(raw).hexdigest()
