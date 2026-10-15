"""Read-only checks of supplied records against immutable local originals."""
import uuid
from kcee.knowledge import Knowledge
from kcee.page_notes import verified_page,note_digest
from kcee.provenance import IntegrityError

def verify_records(data):
    if not isinstance(data,dict):raise ValueError('Use an export record request')
    knowledge=Knowledge()
    if data.get('kind')=='passages' and set(data)=={'kind','documents','passages'}:
        documents,passages=data['documents'],data['passages']
        if not isinstance(documents,list) or not isinstance(passages,list) or not 1<=len(documents)<=12 or len(passages)>12:raise ValueError('No included sources to check, or record limit exceeded')
        sources=set()
        for document in documents:
            identifier=str(uuid.UUID(document['id']));row,raw=knowledge.source(identifier)
            if document['name']!=row['name'] or document['source_sha256']!=row['source_sha256']:raise IntegrityError('Imported document identity differs from stored original')
            sources.add(identifier)
        if any(str(uuid.UUID(p['document_id'])) not in sources for p in passages):raise IntegrityError('Passage is outside supplied sources')
        knowledge.verify_citations(passages)
        return {'integrity':'matches_local_records','sources':len(sources),'passages':len(passages),'notes':0}
    if data.get('kind')=='notes' and set(data)=={'kind','identity','notes'}:
        identity,notes=data['identity'],data['notes']
        if not isinstance(identity,dict) or not isinstance(notes,list) or len(notes)>5000:raise ValueError('Invalid note records')
        actual=verified_page(knowledge,identity['document_id'],identity['page_number']);row,raw=knowledge.source(identity['document_id'])
        if any(identity.get(key)!=value for key,value in actual.items()) or identity.get('name')!=row['name']:raise IntegrityError('Imported note page differs from stored original')
        ids=[note['id'] for note in notes]
        if any(type(id) is not int or not 1<=id<2**63 for id in ids) or len(set(ids))!=len(ids):raise ValueError('Invalid note identities')
        with knowledge.connect() as conn:stored=conn.execute('SELECT * FROM document_page_notes WHERE document_id=%s AND page_number=%s AND id=ANY(%s::bigint[])',(identity['document_id'],identity['page_number'],ids)).fetchall()
        by_id={note['id']:note for note in stored}
        for note in notes:
            saved=by_id.get(note['id'])
            if not saved or note_digest(saved)!=saved['note_sha256'] or note_digest(note)!=saved['note_sha256'] or note['note_sha256']!=saved['note_sha256'] or note['created_at']!=saved['created_at'].isoformat():raise IntegrityError('Imported note differs from saved history')
        return {'integrity':'matches_local_records','sources':1,'passages':0,'notes':len(notes)}
    raise ValueError('Unsupported record check')
