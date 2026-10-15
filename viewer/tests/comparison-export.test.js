import test from 'node:test';
import assert from 'node:assert/strict';
import {comparisonSnapshot,comparisonText} from '../comparison-export.js';
import {searchSnapshot,textHash} from '../search-export.js';
async function fixture(){
 const docs=[{id:'12345678-1234-1234-1234-123456789abc',name:'scan.pdf',source_sha256:'a'.repeat(64)},{id:'00000000-0000-4000-8000-000000000001',name:'notes.md',source_sha256:'b'.repeat(64)}];
 const sources=[];for(const [i,document] of docs.entries()){const content='Exact 0.525 W.\r\n';const passages=i?[]:[{citation_id:'D1',document_id:document.id,name:document.name,page_number:2,content,source_sha256:document.source_sha256,chunk_sha256:await textHash(content),extraction_method:'ocr',ocr_languages:'eng+spa'}];sources.push({document,snapshot:await searchSnapshot('Heat?',{integrity:'verified',passages,retrieval:{query:'Heat?',document_id:document.id}},document)});}
 return {question:'Heat?',compared_at:'2026-10-15T00:00:00Z',sources};
}
test('comparison exports preserve source-specific citations, empty sources and independent hashes',async()=>{
 const original=await fixture(),record=await comparisonSnapshot(original);const {snapshot_sha256,...payload}=JSON.parse(JSON.stringify(record));assert.equal(snapshot_sha256,await textHash(JSON.stringify(payload)));
 const text=comparisonText(record);for(const value of ['Source 1: scan.pdf','Source 2: notes.md','Physical PDF page: 2','No matching passages.','0.525 W','Citations are local'])assert.ok(text.includes(value));
 assert.equal(record.sources[0].snapshot.snapshot_sha256,original.sources[0].snapshot.snapshot_sha256);original.sources[0].document.name='changed';assert.equal(record.sources[0].document.name,'scan.pdf');
});
test('changed comparison passages, questions and source identity reject export',async()=>{
 for(const change of [r=>r.question='Other',r=>r.sources[0].snapshot.passages[0].content='changed',r=>r.sources[1].document.id=r.sources[0].document.id,r=>r.sources[1].document.source_sha256='missing',r=>r.sources[0].document.source_sha256='c'.repeat(64)]){const r=await fixture();change(r);await assert.rejects(comparisonSnapshot(r));}
});
