export function handoffSources(detail){
 const sources=detail.documents??(detail.document?[detail.document]:[]);
 if(!Array.isArray(sources)||sources.length>3||new Set(sources.map(s=>s?.id)).size!==sources.length||sources.some(s=>!s||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s.id)||typeof s.name!=='string'||!s.name||s.name.length>120))return null;
 if(sources.some(s=>s.page_range!=null&&(sources.length!==1||!Number.isInteger(s.page_range.start)||!Number.isInteger(s.page_range.end)||s.page_range.start<1||s.page_range.end<s.page_range.start||s.page_range.end>300)))return null;
 return sources.map(s=>({id:s.id,name:s.name,...(s.page_range?{page_range:{...s.page_range}}:{})}));
}
export function scopeRequest(sources){return sources.length===1?{document_id:sources[0].id,...(sources[0].page_range?{page_start:sources[0].page_range.start,page_end:sources[0].page_range.end}:{})}:sources.length?{document_ids:sources.map(s=>s.id)}:{};}
export function answerScopes(evidence){return evidence.document_search?.scopes||(evidence.document_search?.scope?[evidence.document_search.scope]:[]);}
export function scopeMatches(sources,evidence){
 if(!sources.length)return true;const scopes=answerScopes(evidence),ids=new Set(sources.map(s=>s.id));return scopes.length===ids.size&&new Set(scopes.map(s=>s.document_id)).size===ids.size&&scopes.every(s=>ids.has(s.document_id)&&JSON.stringify(s.page_range||null)===JSON.stringify(sources.find(r=>r.id===s.document_id).page_range||null))&&(evidence.documents||[]).every(c=>{const source=sources.find(s=>s.id===c.document_id);return !!source&&(!source.page_range||(Number.isInteger(c.page_number)&&c.page_number>=source.page_range.start&&c.page_number<=source.page_range.end));});
}
export function scopeDescription(evidence){const scopes=answerScopes(evidence);return scopes.length?scopes.map(s=>s.name+(s.page_range?'; physical pages '+s.page_range.start+'–'+s.page_range.end:'; all pages')+'; document '+s.document_id+'; SHA-256 '+s.source_sha256).join('\n'):evidence.document_search?'All active documents':'Document references disabled';}
