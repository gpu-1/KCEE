import {validateSavedSearches} from './saved-searches.js';
import {textHash} from './search-export.js';
export async function exportSavedSearches(rows,now=new Date().toISOString()){
 validateSavedSearches(rows);const searches=rows.map(r=>({id:r.id,question:r.question,document:r.document?{id:r.document.id,name:r.document.name}:null,saved_at:r.saved_at}));
 const record={schema:'kcee.saved-searches-export.v1',exported_at:now,searches};record.snapshot_sha256=await textHash(JSON.stringify(record));return record;
}
export async function parseSavedSearchExport(raw){
 if(typeof raw!=='string'||raw.length>256*1024)throw new Error('Choose a saved-search JSON file up to 256 KB');
 const record=JSON.parse(raw);if(!record||record.schema!=='kcee.saved-searches-export.v1'||typeof record.exported_at!=='string'||!Number.isFinite(Date.parse(record.exported_at))||!/^[a-f0-9]{64}$/.test(record.snapshot_sha256||''))throw new Error('Unsupported saved-search export');
 const {snapshot_sha256,...body}=record;if(await textHash(JSON.stringify(body))!==snapshot_sha256)throw new Error('Saved-search file hash mismatch');validateSavedSearches(record.searches);return record.searches;
}
