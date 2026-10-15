"""Append-only observations tied to verified original PDF pages, never source edits."""
import hashlib,json,uuid
from kcee.knowledge import Knowledge
from kcee.provenance import IntegrityError
FIELDS=('document_id','page_number','source_sha256','page_text_sha256','extractor','note')
def note_digest(row):
    payload={key:str(row[key]) if key=='document_id' else row[key] for key in FIELDS}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
def verified_page(knowledge,document_id,page_number):
    if type(page_number) is not int or not 1<=page_number<=300:raise ValueError('Invalid physical PDF page')
    row,raw=knowledge.source(document_id);lines,pdf=knowledge.reference_lines(row,raw)
    if not pdf or page_number>pdf['page_count']:raise ValueError('Choose an existing PDF page')
    knowledge.reference_lines(row,raw,[page_number])
    return {'document_id':str(uuid.UUID(str(document_id))),'page_number':page_number,'source_sha256':row['source_sha256'],'page_text_sha256':pdf['pages'][page_number-1]['text_sha256'],'extractor':pdf['extractor']}
def save_note(document_id,page_number,data):
    if not isinstance(data,dict) or set(data)!={'source_sha256','page_text_sha256','note'}:raise ValueError('Use source and page hashes with a review note')
    text=data['note']
    if not isinstance(text,str) or not 1<=len(text.strip())<=2000 or any(ord(c)<32 and c not in '\n\r\t' for c in text):raise ValueError('Use a review note of 1 to 2000 characters')
    knowledge=Knowledge();record=verified_page(knowledge,document_id,page_number)
    if data['source_sha256']!=record['source_sha256'] or data['page_text_sha256']!=record['page_text_sha256']:raise IntegrityError('Review note source or page hash mismatch')
    record['note']=text.strip();record['note_sha256']=note_digest(record)
    with knowledge.connect() as conn:
        saved=conn.execute('INSERT INTO document_page_notes(document_id,page_number,source_sha256,page_text_sha256,extractor,note,note_sha256) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id,created_at',tuple(record[key] for key in (*FIELDS,'note_sha256'))).fetchone()
    return {**record,**saved}
def list_notes(document_id,page_number,before=None):
    if before is not None and before<1:raise ValueError('Invalid note cursor')
    knowledge=Knowledge();identity=verified_page(knowledge,document_id,page_number)
    with knowledge.connect() as conn:rows=conn.execute('SELECT * FROM document_page_notes WHERE document_id=%s AND page_number=%s AND (%s::bigint IS NULL OR id<%s) ORDER BY id DESC LIMIT 21',(str(document_id),page_number,before,before)).fetchall()
    for row in rows:
        if any(str(row[key])!=str(identity[key]) for key in identity) or note_digest(row)!=row['note_sha256']:raise IntegrityError('Saved review note integrity mismatch')
    return {'items':rows[:20],'next_before':rows[19]['id'] if len(rows)>20 else None,'identity':identity}
