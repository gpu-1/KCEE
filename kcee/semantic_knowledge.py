"""Immutable pgvector indexing and hybrid reciprocal-rank retrieval."""
import hashlib,json,time
from kcee.embeddings import status,embed,float32_vector,input_text
from kcee.geometry_queue import QueueError
from kcee.provenance import IntegrityError
THRESHOLD=.5
RRF_K=60

def coverage(knowledge,state=None):
    state=state or status()
    with knowledge.connect() as conn:
        total=conn.execute('SELECT count(*) AS n FROM local_document_chunks c JOIN active_local_documents d ON d.id=c.document_id').fetchone()['n']
        indexed=conn.execute('SELECT count(*) AS n FROM local_chunk_embeddings e JOIN local_document_chunks c ON c.id=e.chunk_id JOIN active_local_documents d ON d.id=c.document_id WHERE model_manifest_sha256=%s',(state.get('model_manifest_sha256',''),)).fetchone()['n']
    return {**state,'total_passages':total,'indexed_passages':indexed,'remaining_passages':max(0,total-indexed)}

def index(knowledge):
    state=status()
    if not state['available']:raise QueueError('Start local semantic search before indexing')
    with knowledge.connect() as conn:rows=conn.execute('SELECT c.id,c.document_id,c.page_number,c.line_start,c.line_end,c.content,c.chunk_sha256,d.name,d.source_sha256 FROM local_document_chunks c JOIN active_local_documents d ON d.id=c.document_id WHERE NOT EXISTS(SELECT 1 FROM local_chunk_embeddings e WHERE e.chunk_id=c.id AND e.model_manifest_sha256=%s) ORDER BY c.id LIMIT 16',(state['model_manifest_sha256'],)).fetchall()
    count=0;started=time.monotonic()
    for row in rows:
        if time.monotonic()-started>30:break
        chunk={'document_id':str(row['document_id']),'page_number':row['page_number'],'name':row['name'],'line_start':row['line_start'],'line_end':row['line_end'],'content':row['content'],'source_sha256':row['source_sha256'],'chunk_sha256':row['chunk_sha256']};knowledge.verify_citations([chunk])
        result=embed('document',row['content'])
        if result['model_manifest_sha256']!=state['model_manifest_sha256']:raise QueueError('Embedding model changed during indexing')
        with knowledge.connect() as conn:
            conn.execute('INSERT INTO local_chunk_embeddings(chunk_id,source_sha256,chunk_sha256,model_sha256,model_manifest_sha256,input_sha256,vector_sha256,embedding) VALUES(%s,%s,%s,%s,%s,%s,%s,%s::vector) ON CONFLICT(chunk_id,model_manifest_sha256) DO NOTHING',(row['id'],row['source_sha256'],row['chunk_sha256'],result['model_sha256'],result['model_manifest_sha256'],result['input_sha256'],result['vector_sha256'],json.dumps(result['vector'])))
        count+=1
    return {**coverage(knowledge,state),'processed_this_batch':count}

def fuse(lexical,semantic,limit=4):
    scores={};rows={};ranks={}
    for method,candidates in (('keyword',lexical),('semantic',semantic)):
        for rank,row in enumerate(candidates,1):
            key=row['chunk_id'];rows.setdefault(key,row);scores[key]=scores.get(key,0)+1/(RRF_K+rank);ranks.setdefault(key,{})[method]=rank
            if method=='semantic':rows[key]={**rows[key],'cosine_similarity':row['cosine_similarity'],'embedding_vector_sha256':row['embedding_vector_sha256']}
    return [{**rows[key],'retrieval_ranks':ranks[key],'hybrid_score':scores[key]} for key in sorted(scores,key=lambda key:(-scores[key],key))[:limit]]

def retrieve(knowledge,question,lexical,document_id=None):
    metadata={'method':'local PostgreSQL English full-text search','query':question,'semantic_embeddings':False}
    try:
        state=coverage(knowledge)
        if not state['available']:metadata['semantic_fallback']='Local embedding service unavailable';return lexical[:4],metadata
        if not state['indexed_passages']:metadata['semantic_fallback']='No passages indexed for this model';return lexical[:4],metadata
        result=embed('query',question);vector=json.dumps(result['vector'])
        if result['model_manifest_sha256']!=state['model_manifest_sha256']:raise QueueError('Embedding model changed during retrieval')
        with knowledge.connect() as conn:rows=conn.execute('SELECT c.id AS chunk_id,c.document_id,c.page_number,c.line_start,c.line_end,c.content,c.chunk_sha256,d.name,d.source_sha256,e.source_sha256 AS indexed_source_sha256,e.chunk_sha256 AS indexed_chunk_sha256,e.input_sha256,e.vector_sha256,e.embedding::text AS embedding_text,1-(e.embedding <=> %s::vector) AS cosine_similarity FROM local_chunk_embeddings e JOIN local_document_chunks c ON c.id=e.chunk_id JOIN active_local_documents d ON d.id=c.document_id WHERE e.model_manifest_sha256=%s AND (%s::uuid IS NULL OR d.id=%s::uuid) ORDER BY e.embedding <=> %s::vector,c.id LIMIT 12',(vector,state['model_manifest_sha256'],document_id,document_id,vector)).fetchall()
        candidates=[]
        for row in rows:
            try:_,digest=float32_vector(json.loads(row['embedding_text']))
            except (ValueError,TypeError) as error:raise IntegrityError('Invalid stored embedding vector') from error
            if row['vector_sha256']!=digest or row['indexed_source_sha256']!=row['source_sha256'] or row['indexed_chunk_sha256']!=row['chunk_sha256'] or row['input_sha256']!=hashlib.sha256(input_text('document',row['content']).encode()).hexdigest():raise IntegrityError('Indexed vector/source fingerprint mismatch')
            if row['cosine_similarity']<THRESHOLD:continue
            candidates.append({**row,'document_id':str(row['document_id']),'embedding_vector_sha256':digest})
        metadata={'method':'local keyword + Nomic semantic retrieval (reciprocal rank fusion)','query':question,'semantic_embeddings':True,'model':state['model'],'model_sha256':state['model_sha256'],'model_manifest_sha256':state['model_manifest_sha256'],'dimensions':state['dimensions'],'query_input_sha256':result['input_sha256'],'query_vector_sha256':result['vector_sha256'],'minimum_cosine_similarity':THRESHOLD,'rank_fusion_constant':RRF_K,'indexed_passages':state['indexed_passages'],'total_passages':state['total_passages']}
        return fuse(lexical,candidates),metadata
    except QueueError as error:
        metadata['semantic_fallback']=str(error);return lexical[:4],metadata
