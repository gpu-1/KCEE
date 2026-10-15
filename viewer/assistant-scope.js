export function handoffSources(detail){
 const sources=detail.documents??(detail.document?[detail.document]:[]);
 if(!Array.isArray(sources)||sources.length>3||new Set(sources.map(s=>s?.id)).size!==sources.length||sources.some(s=>!s||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s.id)||typeof s.name!=='string'||!s.name||s.name.length>120))return null;
 return sources.map(s=>({id:s.id,name:s.name}));
}
export function scopeRequest(sources){return sources.length===1?{document_id:sources[0].id}:sources.length?{document_ids:sources.map(s=>s.id)}:{};}
export function answerScopes(evidence){return evidence.document_search?.scopes||(evidence.document_search?.scope?[evidence.document_search.scope]:[]);}
export function scopeMatches(sources,evidence){
 if(!sources.length)return true;const scopes=answerScopes(evidence),ids=new Set(sources.map(s=>s.id));return scopes.length===ids.size&&new Set(scopes.map(s=>s.document_id)).size===ids.size&&scopes.every(s=>ids.has(s.document_id))&&(evidence.documents||[]).every(c=>ids.has(c.document_id));
}
export function scopeDescription(evidence){const scopes=answerScopes(evidence);return scopes.length?scopes.map(s=>s.name+'; document '+s.document_id+'; SHA-256 '+s.source_sha256).join('\n'):evidence.document_search?'All active documents':'Document references disabled';}
