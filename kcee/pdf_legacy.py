"""Retained v1 extraction for immutable historical PDF citations."""
import hashlib,io
MAX_PDF_BYTES=5*1024*1024
MAX_PAGES=40
MAX_TEXT_BYTES=512*1024
EXTRACTOR='pypdf-6.19.0/plain/kcee-v1'

def extract_direct(raw):
    from pypdf import PdfReader,__version__
    if __version__!='6.19.0':raise ValueError('PDF extractor version mismatch')
    if not raw.startswith(b'%PDF-') or not 0<len(raw)<=MAX_PDF_BYTES:raise ValueError('Use a PDF up to 5 MB')
    reader=PdfReader(io.BytesIO(raw),strict=True)
    if reader.is_encrypted:raise ValueError('Encrypted PDFs are not supported')
    if not 1<=len(reader.pages)<=MAX_PAGES:raise ValueError('Use a PDF with at most 40 pages')
    pages=[];total=0
    for number,page in enumerate(reader.pages,1):
        text=page.extract_text() or ''
        if any(ord(c)<32 and c not in '\t\r\n' for c in text):raise ValueError('PDF text contains unsupported control characters')
        if any(len(line)>1800 for line in text.splitlines(keepends=True)):raise ValueError('PDF extracted lines exceed 1800 characters')
        if text and not text.endswith(('\n','\r')):text+='\n'
        total+=len(text.encode('utf-8'))
        if total>MAX_TEXT_BYTES:raise ValueError('PDF extracted text exceeds 512 KB')
        pages.append({'page_number':number,'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest()})
    if not any(p['text'].strip() for p in pages):raise ValueError('PDF has no extractable text; OCR is not available')
    return {'extractor':EXTRACTOR,'pages':pages,'page_count':len(pages),'empty_pages':[p['page_number'] for p in pages if not p['text'].strip()]}
