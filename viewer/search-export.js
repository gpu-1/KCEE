const hashPattern=/^[0-9a-f]{64}$/;
const uuidPattern=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export async function textHash(text){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))].map(x=>x.toString(16).padStart(2,'0')).join('');}
export async function searchSnapshot(question,result,scope=null){
 if(result.integrity!=='verified'||!Array.isArray(result.passages)||result.retrieval?.query!==question)throw new Error('Search export requires verified results for this question');
 if(scope&&(!uuidPattern.test(scope.id)||result.retrieval.document_id!==scope.id))throw new Error('Search scope mismatch');
 for(const chunk of result.passages){
  if(!uuidPattern.test(chunk.document_id)||!hashPattern.test(chunk.source_sha256)||!hashPattern.test(chunk.chunk_sha256)||typeof chunk.content!=='string'||await textHash(chunk.content)!==chunk.chunk_sha256)throw new Error('Search passage integrity mismatch');
  if(scope&&chunk.document_id!==scope.id)throw new Error('Search scope mismatch');
  if(chunk.page_number!=null&&(!Number.isInteger(chunk.page_number)||chunk.page_number<1||chunk.page_number>300))throw new Error('Invalid citation page');
 }
 const record={schema:'kcee.document-search.v1',exported_at:new Date().toISOString(),question,scope:scope?{document_id:scope.id,name:scope.name}:null,integrity:'verified_at_search',limitations:['Search-time snapshot; later library visibility may differ.','OCR and relevance require comparison with the original.','Source integrity does not establish engineering validation.'],retrieval:structuredClone(result.retrieval),passages:structuredClone(result.passages)};
 return {...record,snapshot_sha256:await textHash(JSON.stringify(record))};
}
export function searchText(record){
 const lines=['KCEE document search — search-time snapshot','Exported: '+record.exported_at,'Snapshot SHA-256: '+record.snapshot_sha256,'','Question',record.question,'','Scope',record.scope?record.scope.name+' (document '+record.scope.document_id+')':'All active documents at search time','','Retrieval',JSON.stringify(record.retrieval),'','Passages'];
 if(!record.passages.length)lines.push('No matching passages.');
 for(const chunk of record.passages){
  lines.push('','['+chunk.citation_id+'] '+chunk.name,chunk.page_number?'Physical PDF page: '+chunk.page_number:'Lines: '+chunk.line_start+'–'+chunk.line_end,'Document: '+chunk.document_id,'Extraction: '+(chunk.extraction_method||'text')+(chunk.ocr_languages?' · OCR language: '+chunk.ocr_languages:''),'Source SHA-256: '+chunk.source_sha256,'Passage SHA-256: '+chunk.chunk_sha256,...(chunk.page_text_sha256?['Page text SHA-256: '+chunk.page_text_sha256]:[]),'',chunk.content);
 }
 lines.push('','Limitations',...record.limitations,'','The companion JSON preserves complete passage and retrieval metadata.','Snapshot hash covers JSON.stringify(record) with snapshot_sha256 omitted.','');return lines.join('\n');
}
