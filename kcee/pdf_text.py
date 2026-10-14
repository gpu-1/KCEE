"""Bounded text-only PDF extraction in an isolated, time-limited child process."""
import hashlib,io,json,subprocess,sys
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

def extract_pdf(raw):
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_PDF_BYTES or not raw.startswith(b'%PDF-'):raise ValueError('Use a valid PDF up to 5 MB')
    try:
        result=subprocess.run([sys.executable,'-m','kcee.pdf_text'],input=raw,capture_output=True,timeout=15)
    except subprocess.TimeoutExpired:raise ValueError('PDF extraction exceeded the 15-second limit')
    if result.returncode:raise ValueError('PDF cannot be extracted: '+result.stdout.decode('utf-8',errors='replace')[:200])
    if len(result.stdout)>4*MAX_TEXT_BYTES:raise ValueError('PDF extraction output exceeds limit')
    return json.loads(result.stdout)

if __name__=='__main__':
    import resource
    resource.setrlimit(resource.RLIMIT_CPU,(10,10))
    if sys.platform=='linux':resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    try:print(json.dumps(extract_direct(sys.stdin.buffer.read(MAX_PDF_BYTES+1)),ensure_ascii=True))
    except Exception as error:
        print(str(error)[:200]);sys.exit(1)
