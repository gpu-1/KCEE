"""Compare library metadata fingerprints, without re-certifying source bytes."""
import hashlib,json
TABLES=('local_documents','local_document_chunks','local_pdf_extractions','local_chunk_embeddings','document_visibility_events','document_page_notes')
def fingerprint_records(groups):
    digest=hashlib.sha256();counts={}
    for table in TABLES:
        rows=groups[table];count=0
        for row in rows:
            raw=json.dumps([table,row],sort_keys=True,separators=(',',':'),ensure_ascii=True).encode();digest.update(len(raw).to_bytes(8,'big'));digest.update(raw);count+=1
        counts[table]=count
    return {'scheme':'kcee.library-metadata.v1','sha256':digest.hexdigest(),'counts':counts}
def library_snapshot(conn):
    conn.execute("SET LOCAL TIME ZONE 'UTC'")
    groups={}
    for table in TABLES:
        order='document_id' if table=='local_pdf_extractions' else 'id'
        groups[table]=(r['record'] for r in conn.execute("SELECT to_jsonb(t) - 'original_bytes' - 'content' - 'embedding' - 'extraction' - 'note' AS record FROM "+table+' t ORDER BY '+order))
    return fingerprint_records(groups)
def compare_library(backup,current):
    if not backup:return {'status':'no_backup','message':'No available backup receipt.'}
    saved=backup.get('library_snapshot');counts=backup['counts']
    differences=[{'table':t,'backup':counts.get(t),'current':current['counts'][t]} for t in TABLES if counts.get(t)!=current['counts'][t]]
    if differences:return {'status':'differs','message':'Library record counts differ from the backup receipt.','differences':differences}
    if not isinstance(saved,dict) or saved.get('scheme')!=current['scheme'] or not isinstance(saved.get('sha256'),str):return {'status':'unknown','message':'Counts match, but this older receipt has no compatible library fingerprint. Coverage cannot be established from counts alone.'}
    if saved['sha256']!=current['sha256']:return {'status':'differs','message':'Counts match, but library metadata fingerprints differ.'}
    if not backup.get('bundle_present'):return {'status':'missing_bundle','message':'Library metadata matches the receipt, but the local backup bundle is missing.'}
    return {'status':'matches_metadata','message':'Current library metadata matches the backup receipt, including archived sources and review-note history. Archive contents have not been rechecked.'}
