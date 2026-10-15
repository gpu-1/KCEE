// Physical PDF page numbers match the recorded extraction pages.
export function pdfPageUrl(chunk){
 if(!chunk.name?.toLowerCase().endsWith('.pdf')||!Number.isInteger(chunk.page_number)||chunk.page_number<1||chunk.page_number>300)return null;
 if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(chunk.document_id))throw new Error('Invalid document identity');
 return '/api/knowledge/documents/'+chunk.document_id+'/source?inline=true#page='+chunk.page_number;
}
export function appendPdfPageLink(container,chunk){
 const url=pdfPageUrl(chunk);if(!url)return;
 const link=document.createElement('a');link.href=url;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Open PDF at page '+chunk.page_number;
 const row=document.createElement('p');row.appendChild(link);container.appendChild(row);
}
