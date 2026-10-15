import test from 'node:test';
import assert from 'node:assert/strict';
import {searchSnapshot,searchText,textHash} from '../search-export.js';
const id='12345678-1234-1234-1234-123456789abc';
async function fixture(){const content='Literal OCR value: 0.525 W.\r\n';return {integrity:'verified',retrieval:{query:'Heat?',document_id:id,semantic_embeddings:false,matches:1},passages:[{citation_id:'D1',document_id:id,name:'scan.pdf',page_number:2,content,source_sha256:'a'.repeat(64),chunk_sha256:await textHash(content),extraction_method:'ocr',ocr_languages:'eng+spa',page_text_sha256:'b'.repeat(64)}]};}
test('search exports preserve literal citations, scoped identity and snapshot digest',async()=>{
 const result=await fixture(),record=await searchSnapshot('Heat?',result,{id,name:'scan.pdf'});
 assert.equal(record.passages[0].content,result.passages[0].content);assert.equal(record.scope.document_id,id);
 const {snapshot_sha256,...payload}=JSON.parse(JSON.stringify(record));assert.equal(snapshot_sha256,await textHash(JSON.stringify(payload)));
 const text=searchText(record);for(const value of ['0.525 W','Physical PDF page: 2','eng+spa','a'.repeat(64),'b'.repeat(64),'engineering validation'])assert.ok(text.includes(value));
 result.passages[0].content='changed';assert.notEqual(record.passages[0].content,'changed');
});
test('unverified, changed, unrelated and incorrectly scoped exports are rejected',async()=>{
 const original=await fixture();
 for(const change of [r=>r.integrity='failed',r=>r.passages[0].content='changed',r=>r.passages[0].source_sha256='missing',r=>r.passages[0].page_number=0,r=>r.retrieval.query='Other question',r=>r.passages[0].document_id='00000000-0000-4000-8000-000000000001']){const r=structuredClone(original);change(r);await assert.rejects(searchSnapshot('Heat?',r,{id,name:'scan.pdf'}));}
});
test('verified empty results export without inventing citations',async()=>{
 const record=await searchSnapshot('Empty?',{integrity:'verified',retrieval:{query:'Empty?',matches:0},passages:[]});assert.equal(record.scope,null);assert.ok(searchText(record).includes('No matching passages.'));
});
