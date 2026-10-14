"""Local, bounded native text extraction and scanned-page OCR."""
import hashlib,io,json,os,subprocess,sys,tempfile
from pathlib import Path
MAX_PDF_BYTES=50*1024*1024
MAX_PAGES=300
MAX_TEXT_BYTES=8*1024*1024
LEGACY_EXTRACTOR='pypdf-6.19.0/plain/kcee-v1'
EXTRACTOR='pypdf-6.19.0/poppler-tesseract/eng+spa/kcee-v2'

def ocr_runtime():
    files=['/usr/bin/pdftoppm','/usr/bin/tesseract','/usr/share/tesseract-ocr/5/tessdata/eng.traineddata','/usr/share/tesseract-ocr/5/tessdata/spa.traineddata']
    try:return {path:hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in files}
    except OSError:raise ValueError('Local OCR runtime is unavailable')

def contains_image(resources,depth=0,seen=None):
    if depth>8 or not resources:return False
    resources=resources.get_object()
    seen=set() if seen is None else seen
    xobjects=resources.get('/XObject')
    if not xobjects:return False
    for obj in xobjects.get_object().values():
        item=obj.get_object();identity=id(item)
        if identity in seen:continue
        seen.add(identity)
        if item.get('/Subtype')=='/Image' and item.get('/Width',0)>=128 and item.get('/Height',0)>=128:return True
        if item.get('/Subtype')=='/Form' and contains_image(item.get('/Resources'),depth+1,seen):return True
    return False

def recognize_page(pdf_path,number,directory):
    prefix=Path(directory)/'page'
    env={**os.environ,'OMP_THREAD_LIMIT':'2','LC_ALL':'C'}
    try:
        rendered=subprocess.run(['/usr/bin/pdftoppm','-f',str(number),'-l',str(number),'-singlefile','-scale-to','2400','-gray',str(pdf_path),str(prefix)],capture_output=True,timeout=25,env=env)
        if rendered.returncode:raise ValueError('PDF page rendering failed')
        image=prefix.with_suffix('.pgm')
        if not image.is_file() or image.stat().st_size>16*1024*1024:raise ValueError('Rendered PDF page exceeds image limit')
        result=subprocess.run(['/usr/bin/tesseract',str(image),'stdout','--tessdata-dir','/usr/share/tesseract-ocr/5/tessdata','-l','eng+spa','--oem','1','--psm','3'],capture_output=True,timeout=25,env=env)
        if result.returncode:raise ValueError('Local OCR failed')
        return result.stdout.decode('utf-8')
    except subprocess.TimeoutExpired:raise ValueError('PDF page OCR exceeded its time limit')

def extract_direct(raw,extractor=EXTRACTOR,page_numbers=None):
    if extractor==LEGACY_EXTRACTOR:
        from kcee.pdf_legacy import extract_direct as legacy
        return legacy(raw)
    from pypdf import PdfReader,__version__
    if extractor!=EXTRACTOR or __version__!='6.19.0':raise ValueError('PDF extractor version mismatch')
    if not raw.startswith(b'%PDF-') or not 0<len(raw)<=MAX_PDF_BYTES:raise ValueError('Use a PDF up to 50 MB')
    reader=PdfReader(io.BytesIO(raw),strict=True)
    if reader.is_encrypted:raise ValueError('Encrypted PDFs are not supported')
    count=len(reader.pages)
    if not 1<=count<=MAX_PAGES:raise ValueError('Use a PDF with at most 300 pages')
    numbers=list(range(1,count+1)) if page_numbers is None else sorted(set(page_numbers))
    if not numbers or any(type(n) is not int or not 1<=n<=count for n in numbers):raise ValueError('Invalid PDF page selection')
    pages=[];total=0;runtime=None
    with tempfile.TemporaryDirectory(prefix='kcee-ocr-') as directory:
        pdf_path=Path(directory)/'source.pdf';pdf_path.write_bytes(raw)
        for number in numbers:
            page=reader.pages[number-1];text=page.extract_text() or '';method='embedded_text'
            if len(text.strip())<80 and contains_image(page.get('/Resources')):
                runtime=runtime or ocr_runtime();text=recognize_page(pdf_path,number,directory);method='ocr'
            if any(ord(c)<32 and c not in '\t\r\n' for c in text):raise ValueError('PDF text contains unsupported control characters')
            if any(len(line)>1800 for line in text.splitlines(keepends=True)):raise ValueError('PDF extracted lines exceed 1800 characters')
            if text and not text.endswith(('\n','\r')):text+='\n'
            size=len(text.encode('utf-8'));total+=size
            if size>256*1024 or total>MAX_TEXT_BYTES:raise ValueError('PDF extracted text exceeds limits')
            pages.append({'page_number':number,'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'method':method})
    if page_numbers is None and not any(p['text'].strip() for p in pages):raise ValueError('PDF has no readable text, including OCR')
    result={'extractor':EXTRACTOR,'pages':pages,'page_count':count,'empty_pages':[p['page_number'] for p in pages if not p['text'].strip()],'ocr_pages':[p['page_number'] for p in pages if p['method']=='ocr'],'ocr_settings':{'languages':'eng+spa','maximum_image_dimension':2400,'psm':3,'oem':1}}
    if runtime:result['ocr_runtime_sha256']=runtime
    return result

def extract_pdf(raw,extractor=EXTRACTOR,page_numbers=None):
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_PDF_BYTES or not raw.startswith(b'%PDF-'):raise ValueError('Use a valid PDF up to 50 MB')
    timeout=15 if extractor==LEGACY_EXTRACTOR else min(600,15+50*len(page_numbers)) if page_numbers else 600
    try:
        result=subprocess.run([sys.executable,'-m','kcee.pdf_text',extractor,json.dumps(page_numbers)],input=raw,capture_output=True,timeout=timeout)
    except subprocess.TimeoutExpired:raise ValueError('PDF extraction exceeded its '+str(timeout)+'-second limit')
    if result.returncode:raise ValueError('PDF cannot be extracted: '+result.stdout.decode('utf-8',errors='replace')[:200])
    if len(result.stdout)>4*MAX_TEXT_BYTES:raise ValueError('PDF extraction output exceeds limit')
    return json.loads(result.stdout)

if __name__=='__main__':
    import resource
    resource.setrlimit(resource.RLIMIT_CPU,(240,240))
    if sys.platform=='linux':resource.setrlimit(resource.RLIMIT_AS,(1024*1024*1024,1024*1024*1024))
    try:print(json.dumps(extract_direct(sys.stdin.buffer.read(MAX_PDF_BYTES+1),sys.argv[1],json.loads(sys.argv[2])),ensure_ascii=True))
    except Exception as error:
        print(str(error)[:200]);sys.exit(1)
