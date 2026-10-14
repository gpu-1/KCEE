"""Read-only verification of restored database data and archived run provenance."""
import argparse,hashlib,json,sys
from pathlib import Path
from kcee.registry import Registry
from kcee.provenance import verify_directory,IntegrityError
from kcee.embeddings import float32_vector
TABLES=('design_runs','run_visibility_events','local_documents','local_document_chunks','local_pdf_extractions','local_chunk_embeddings','document_visibility_events')
def verify(root):
    counts={}
    with Registry().connect() as conn:
        for table in TABLES:counts[table]=conn.execute('SELECT count(*) AS n FROM '+table).fetchone()['n']
        for row in conn.execute('SELECT id,manifest,manifest_sha256 FROM design_runs'):
            verify_directory(Path(root)/str(row['id']),row['manifest'],row['manifest_sha256'])
        docs={}
        for row in conn.execute('SELECT id,name,source_sha256,original_bytes FROM local_documents'):
            raw=bytes(row['original_bytes'])
            if hashlib.sha256(raw).hexdigest()!=row['source_sha256']:raise IntegrityError('Restored source hash mismatch')
            docs[str(row['id'])]=dict(row,lines=None if row['name'].lower().endswith('.pdf') else raw.decode().splitlines(keepends=True))
        for row in conn.execute('SELECT document_id,extraction,extraction_sha256 FROM local_pdf_extractions'):
            data=row['extraction'];canonical=json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=True)
            if hashlib.sha256(canonical.encode()).hexdigest()!=row['extraction_sha256']:raise IntegrityError('Restored extraction hash mismatch')
            for page in data['pages']:
                if hashlib.sha256(page['text'].encode()).hexdigest()!=page['text_sha256']:raise IntegrityError('Restored PDF page hash mismatch')
            docs[str(row['document_id'])]['lines']=''.join(page['text'] for page in data['pages']).splitlines(keepends=True)
        for row in conn.execute('SELECT document_id,line_start,line_end,content,chunk_sha256 FROM local_document_chunks'):
            doc=docs[str(row['document_id'])]
            if doc['lines'] is None or ''.join(doc['lines'][row['line_start']-1:row['line_end']])!=row['content'] or hashlib.sha256(row['content'].encode()).hexdigest()!=row['chunk_sha256']:raise IntegrityError('Restored passage hash mismatch')
        for row in conn.execute('SELECT e.embedding::text AS vector,e.vector_sha256,e.source_sha256,e.chunk_sha256,c.chunk_sha256 AS original_chunk_sha256,d.source_sha256 AS original_source_sha256 FROM local_chunk_embeddings e JOIN local_document_chunks c ON c.id=e.chunk_id JOIN local_documents d ON d.id=c.document_id'):
            if float32_vector(json.loads(row['vector']))[1]!=row['vector_sha256'] or row['source_sha256']!=row['original_source_sha256'] or row['chunk_sha256']!=row['original_chunk_sha256']:raise IntegrityError('Restored embedding fingerprint mismatch')
    return {'integrity':'verified','counts':counts,'limitations':['OCR text hashes and saved extraction are checked; OCR accuracy is not re-certified','Destination native services and new solver runs require separate acceptance checks']}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--runs',default='/data/runs');args=parser.parse_args();print(json.dumps(verify(args.runs),indent=2))
