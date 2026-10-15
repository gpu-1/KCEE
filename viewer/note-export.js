import {textHash} from './search-export.js';
function sorted(value){if(Array.isArray(value))return value.map(sorted);if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(key=>[key,sorted(value[key])]));return value;}
export function canonicalNoteJson(value){return JSON.stringify(sorted(value)).replace(/[\u007f-\uffff]/g,char=>'\\u'+char.charCodeAt(0).toString(16).padStart(4,'0'));}
export async function verifyNoteExport(record,item,page){
 const {snapshot_sha256,...payload}=record;
 if(record.schema!=='kcee.page-review-notes.v1'||record.integrity!=='verified_at_export'||await textHash(canonicalNoteJson(payload))!==snapshot_sha256)throw new Error('Notes export snapshot hash mismatch');
 const identity=record.identity;
 if(identity.document_id!==item.id||identity.source_sha256!==item.source_sha256||identity.page_number!==page.page_number||identity.page_text_sha256!==page.text_sha256||record.note_count!==record.notes.length)throw new Error('Notes export page identity mismatch');
 const ids=new Set();let previous=Infinity;
 for(const note of record.notes){
  if(!Number.isSafeInteger(note.id)||note.id<1||note.id>=previous||ids.has(note.id))throw new Error('Notes export history order mismatch');ids.add(note.id);previous=note.id;
  const fields={};for(const key of ['document_id','page_number','source_sha256','page_text_sha256','extractor','note'])fields[key]=note[key];
  if(['document_id','page_number','source_sha256','page_text_sha256','extractor'].some(key=>note[key]!==identity[key])||await textHash(canonicalNoteJson(fields))!==note.note_sha256)throw new Error('Notes export note hash mismatch');
 }
 if(record.latest_note_id!==(record.notes[0]?.id??null))throw new Error('Notes export history boundary mismatch');
 return record;
}
export function noteExportText(record){
 const i=record.identity,lines=['KCEE page review notes — export-time snapshot','Document: '+i.name,'Document ID: '+i.document_id,'Physical PDF page: '+i.page_number,'Original SHA-256: '+i.source_sha256,'Page text SHA-256: '+i.page_text_sha256,'Extractor: '+i.extractor,'Exported: '+record.exported_at,'Snapshot SHA-256: '+record.snapshot_sha256,'Saved notes: '+record.note_count,'','Limitations',...record.limitations];
 if(!record.notes.length)lines.push('','No saved notes for this page.');
 for(const note of record.notes)lines.push('','Note '+note.id+' · '+note.created_at,'Note SHA-256: '+note.note_sha256,'',note.note);
 lines.push('','JSON includes each note’s complete source/page identity.','Hashes use sorted-key compact JSON with non-ASCII characters escaped; omit only the top-level snapshot_sha256 when checking the snapshot.','Hashes detect changes; they are not signatures.','');return lines.join('\n');
}
