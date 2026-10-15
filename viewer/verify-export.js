import {textHash,searchSnapshot} from './search-export.js';
import {comparisonSnapshot} from './comparison-export.js';
import {verifyNoteExport} from './note-export.js';
export async function verifyImportedExport(record){
 if(!record||typeof record!=='object'||Array.isArray(record))throw new Error('Use a KCEE evidence JSON export');
 if(record.schema!=='kcee.page-review-notes.v1'&&(typeof record.question!=='string'||!record.question.trim()||record.question.length>800))throw new Error('Invalid exported question');
 if(typeof record.exported_at!=='string'||!Number.isFinite(Date.parse(record.exported_at))||!/^[0-9a-f]{64}$/.test(record.snapshot_sha256))throw new Error('Invalid export timestamp or fingerprint');
 const {snapshot_sha256,...payload}=record;let kind,passages=[],documents=[],notes=[];
 if(record.schema==='kcee.page-review-notes.v1'){
  if(!Array.isArray(record.notes)||record.notes.length>5000)throw new Error('Invalid note history');const i=record.identity;if(!i||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(i.document_id)||!Number.isInteger(i.page_number)||i.page_number<1||i.page_number>300||!/^[0-9a-f]{64}$/.test(i.source_sha256)||!/^[0-9a-f]{64}$/.test(i.page_text_sha256)||typeof i.name!=='string'||!i.name.toLowerCase().endsWith('.pdf')||typeof i.extractor!=='string'||record.notes.some(n=>typeof n.note!=='string'||!n.note.trim()||n.note.length>2000||typeof n.created_at!=='string'||!Number.isFinite(Date.parse(n.created_at))))throw new Error('Invalid exported note identity or record');
  await verifyNoteExport(record,{id:i.document_id,source_sha256:i.source_sha256},{page_number:i.page_number,text_sha256:i.page_text_sha256});kind='Page review notes';notes=record.notes;
  return {kind,snapshot_sha256,source_count:1,passage_count:0,note_count:notes.length,local_payload:{kind:'notes',identity:i,notes}};
 }
 if(await textHash(JSON.stringify(payload))!==snapshot_sha256)throw new Error('Export snapshot hash mismatch');
 if(record.schema==='kcee.document-search.v1'){
  if(record.integrity!=='verified_at_search'||!Array.isArray(record.passages)||record.passages.length>4)throw new Error('Invalid search snapshot');
  if(!record.scope&&record.retrieval?.document_id)throw new Error('Search scope mismatch');
  await searchSnapshot(record.question,{integrity:'verified',passages:record.passages,retrieval:record.retrieval},record.scope?{id:record.scope.document_id,name:record.scope.name}:null);kind='Document search';passages=record.passages;
 }else if(record.schema==='kcee.reference-comparison.v1'){
  if(record.integrity!=='verified_at_comparison'||record.sources?.some(s=>s.snapshot.passages.length>4))throw new Error('Invalid comparison snapshot');await comparisonSnapshot(record);kind='Reference comparison';passages=record.sources.flatMap(s=>s.snapshot.passages);documents=record.sources.map(s=>s.document);
 }else throw new Error('Unsupported export schema. Choose a search, reference comparison or page-review-notes JSON export.');
 const sources=new Map(documents.map(d=>[d.id,d]));for(const p of passages){const previous=sources.get(p.document_id);if(previous&&(previous.source_sha256!==p.source_sha256||previous.name!==p.name))throw new Error('Conflicting source identity');sources.set(p.document_id,{id:p.document_id,name:p.name,source_sha256:p.source_sha256});}
 documents=[...sources.values()];return {kind,snapshot_sha256,source_count:documents.length,passage_count:passages.length,note_count:0,local_payload:{kind:'passages',documents,passages}};
}
