"""Read-only verification of restored database data and archived run provenance."""
import argparse,hashlib,json,sys
from pathlib import Path
from datetime import timezone
from kcee.library_coverage import library_snapshot
from kcee.page_notes import note_digest,FIELDS
from kcee.provenance import verify_directory,IntegrityError
from kcee.embeddings import float32_vector
TABLES=('design_runs','run_visibility_events','local_documents','local_document_chunks','local_pdf_extractions','local_chunk_embeddings','document_visibility_events','document_page_notes')
def review_note_history(rows,docs):
    history=hashlib.sha256();count=0;previous=0
    for row in rows:
        doc=docs.get(str(row['document_id']));pdf=doc.get('pdf') if doc else None;number=row['page_number']
        if not doc or not pdf or type(number) is not int or not 1<=number<=len(pdf['pages']):raise IntegrityError('Restored review note has no matching PDF page')
        page=pdf['pages'][number-1]
        if page['page_number']!=number or row['source_sha256']!=doc['source_sha256'] or row['page_text_sha256']!=page['text_sha256'] or row['extractor']!=pdf['extractor']:raise IntegrityError('Restored review note source/page identity mismatch')
        if not isinstance(row['note'],str) or not 1<=len(row['note'])<=2000 or note_digest(row)!=row['note_sha256']:raise IntegrityError('Restored review note hash mismatch')
        if type(row['id']) is not int or row['id']<=previous or row['created_at'].tzinfo is None:raise IntegrityError('Restored review note history identity mismatch')
        previous=row['id'];record={key:str(row[key]) if key=='document_id' else row[key] for key in (*FIELDS,'id','note_sha256')};record['created_at']=row['created_at'].astimezone(timezone.utc).isoformat()
        raw=json.dumps(record,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode();history.update(len(raw).to_bytes(8,'big'));history.update(raw);count+=1
    return {'integrity':'verified','count':count,'history_sha256':history.hexdigest(),'hash_scheme':'sha256_length_prefixed_canonical_json_v1'}

def verify(root):
    from kcee.registry import Registry
    counts={}
    with Registry().connect() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        for table in TABLES:counts[table]=conn.execute('SELECT count(*) AS n FROM '+table).fetchone()['n']
        for row in conn.execute('SELECT id,manifest,manifest_sha256 FROM design_runs'):
            verify_directory(Path(root)/str(row['id']),row['manifest'],row['manifest_sha256'])
        docs={}
        for row in conn.execute('SELECT id,name,source_sha256,original_bytes FROM local_documents'):
            raw=bytes(row['original_bytes'])
            if hashlib.sha256(raw).hexdigest()!=row['source_sha256']:raise IntegrityError('Restored source hash mismatch')
            docs[str(row['id'])]=dict(row,pdf=None,lines=None if row['name'].lower().endswith('.pdf') else raw.decode().splitlines(keepends=True))
        for row in conn.execute('SELECT document_id,extraction,extraction_sha256,extractor FROM local_pdf_extractions'):
            data=row['extraction'];canonical=json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=True)
            if hashlib.sha256(canonical.encode()).hexdigest()!=row['extraction_sha256']:raise IntegrityError('Restored extraction hash mismatch')
            if data['extractor']!=row['extractor']:raise IntegrityError('Restored PDF extractor identity mismatch')
            docs[str(row['document_id'])]['pdf']=data
            for page in data['pages']:
                if hashlib.sha256(page['text'].encode()).hexdigest()!=page['text_sha256']:raise IntegrityError('Restored PDF page hash mismatch')
            docs[str(row['document_id'])]['lines']=''.join(page['text'] for page in data['pages']).splitlines(keepends=True)
        for row in conn.execute('SELECT document_id,line_start,line_end,content,chunk_sha256 FROM local_document_chunks'):
            doc=docs[str(row['document_id'])]
            if doc['lines'] is None or ''.join(doc['lines'][row['line_start']-1:row['line_end']])!=row['content'] or hashlib.sha256(row['content'].encode()).hexdigest()!=row['chunk_sha256']:raise IntegrityError('Restored passage hash mismatch')
        for row in conn.execute('SELECT e.embedding::text AS vector,e.vector_sha256,e.source_sha256,e.chunk_sha256,c.chunk_sha256 AS original_chunk_sha256,d.source_sha256 AS original_source_sha256 FROM local_chunk_embeddings e JOIN local_document_chunks c ON c.id=e.chunk_id JOIN local_documents d ON d.id=c.document_id'):
            if float32_vector(json.loads(row['vector']))[1]!=row['vector_sha256'] or row['source_sha256']!=row['original_source_sha256'] or row['chunk_sha256']!=row['original_chunk_sha256']:raise IntegrityError('Restored embedding fingerprint mismatch')
        notes=review_note_history(conn.execute('SELECT * FROM document_page_notes ORDER BY id'),docs)
        if notes['count']!=counts['document_page_notes']:raise IntegrityError('Review note history changed during verification')
        snapshot=library_snapshot(conn)
    return {'integrity':'verified','counts':counts,'review_notes':notes,'library_snapshot':snapshot,'limitations':['OCR text hashes and saved extraction are checked; OCR accuracy is not re-certified','Destination native services and new solver runs require separate acceptance checks']}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--runs',default='/data/runs');args=parser.parse_args();print(json.dumps(verify(args.runs),indent=2))
