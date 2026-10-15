import {searchSnapshot} from './search-export.js';
export async function compareEvidence(question,documents,search){
 if(typeof question!=='string'||!question.trim()||question.length>800)throw new Error('Enter a comparison question of 1 to 800 characters');
 if(documents.length<2||documents.length>3||new Set(documents.map(d=>d.id)).size!==documents.length)throw new Error('Choose two or three different active documents');
 const results=[];
 // Keep local OCR and embedding work bounded; each source gets its own ranking.
 for(const document of documents){
  if(document.archived)throw new Error('Archived documents cannot be compared');
  const result=await search(question,document.id),snapshot=await searchSnapshot(question,result,document);
  if(snapshot.passages.some(p=>p.source_sha256!==document.source_sha256))throw new Error('Comparison source hash mismatch');
  results.push({document:{id:document.id,name:document.name,source_sha256:document.source_sha256},snapshot});
 }
 return {question,compared_at:new Date().toISOString(),sources:results};
}
