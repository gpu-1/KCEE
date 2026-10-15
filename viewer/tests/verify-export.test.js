import test from 'node:test';
import assert from 'node:assert/strict';
import {verifyImportedExport} from '../verify-export.js';
import {searchSnapshot,textHash} from '../search-export.js';
import {comparisonSnapshot} from '../comparison-export.js';
import {compareEvidence} from '../compare-evidence.js';
import {canonicalNoteJson} from '../note-export.js';
const docs=[{id:'12345678-1234-1234-1234-123456789abc',name:'a.pdf',source_sha256:'a'.repeat(64)},{id:'00000000-0000-4000-8000-000000000001',name:'b.pdf',source_sha256:'b'.repeat(64)}];
async function result(question,id){const document=docs.find(d=>d.id===id),content='Exact heat flow 0.525 W.\n';return {integrity:'verified',retrieval:{query:question,document_id:id},passages:[{document_id:id,name:document.name,citation_id:'D1',source_sha256:document.source_sha256,content,chunk_sha256:await textHash(content),page_number:2}]};}
test('import verifier accepts search and comparison schemas and preserves source-bound records',async()=>{
 const search=await searchSnapshot('Heat?',await result('Heat?',docs[0].id),docs[0]);let checked=await verifyImportedExport(search);assert.equal(checked.passage_count,1);assert.equal(checked.local_payload.documents[0].id,docs[0].id);
 const comparison=await comparisonSnapshot(await compareEvidence('Heat?',docs,result));checked=await verifyImportedExport(comparison);assert.equal(checked.source_count,2);assert.equal(checked.passage_count,2);
});
test('import verifier rejects changed hashes and unsupported records',async()=>{
 const record=await searchSnapshot('Heat?',await result('Heat?',docs[0].id),docs[0]);record.passages[0].content='Changed';await assert.rejects(verifyImportedExport(record),/hash mismatch/);
 for(const value of [null,[],{}, {schema:'unknown'}])await assert.rejects(verifyImportedExport(value));
});
test('self-consistent rewritten records need the independent local source check',async()=>{
 const record=await searchSnapshot('Heat?',await result('Heat?',docs[0].id),docs[0]);record.passages[0].content='Altered 9 W';record.passages[0].chunk_sha256=await textHash(record.passages[0].content);delete record.snapshot_sha256;record.snapshot_sha256=await textHash(JSON.stringify(record));assert.equal((await verifyImportedExport(record)).passage_count,1);
});
test('page note imports preserve empty history and physical source identity',async()=>{
 const identity={document_id:docs[0].id,name:'a.pdf',page_number:2,source_sha256:docs[0].source_sha256,page_text_sha256:'c'.repeat(64),extractor:'recorded'};
 const record={schema:'kcee.page-review-notes.v1',exported_at:'2026-10-15T00:00:00Z',integrity:'verified_at_export',identity,notes:[],note_count:0,latest_note_id:null};record.snapshot_sha256=await textHash(canonicalNoteJson(record));const checked=await verifyImportedExport(record);assert.equal(checked.kind,'Page review notes');assert.equal(checked.local_payload.identity.page_number,2);
});
