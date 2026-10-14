"""Small standards-compliant PDFs for deterministic extraction regression tests."""
def pdf_bytes(texts=('Boundary condition: the rear face is fixed at 20 degrees C.','Thermal conductivity is illustrative, not a material allowable.')):
    objects=[b'',b''];page_ids=[]
    objects.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    for text in texts:
        page_id=len(objects)+1;content_id=page_id+1;page_ids.append(page_id)
        escaped=text.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
        stream=('BT /F1 12 Tf 40 740 Td ('+escaped+') Tj ET').encode('ascii') if text else b''
        objects.extend([f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>'.encode(),b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream'])
    objects[0]=b'<< /Type /Catalog /Pages 2 0 R >>'
    objects[1]=b'<< /Type /Pages /Count '+str(len(texts)).encode()+b' /Kids ['+b' '.join(f'{i} 0 R'.encode() for i in page_ids)+b'] >>'
    raw=b'%PDF-1.4\n';offsets=[0]
    for i,obj in enumerate(objects,1):offsets.append(len(raw));raw+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
    start=len(raw);raw+=f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()+b''.join(f'{i:010} 00000 n \n'.encode() for i in offsets[1:])
    return raw+f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()
