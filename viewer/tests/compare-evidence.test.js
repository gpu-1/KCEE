import test from 'node:test';
import assert from 'node:assert/strict';
import {compareEvidence} from '../compare-evidence.js';
import {textHash} from '../search-export.js';
const docs=[{id:'12345678-1234-1234-1234-123456789abc',name:'a.pdf',source_sha256:'a'.repeat(64)},{id:'00000000-0000-4000-8000-000000000001',name:'b.pdf',source_sha256:'b'.repeat(64)}];
test('comparison searches every selected source independently and retains empty results',async()=>{
 const calls=[];const result=await compareEvidence('Heat?',docs,async(q,id)=>{calls.push([q,id]);const content='0.525 W';return {integrity:'verified',retrieval:{query:q,document_id:id},passages:id===docs[0].id?[{citation_id:'D1',document_id:id,name:'a.pdf',page_number:2,content,chunk_sha256:await textHash(content),source_sha256:docs[0].source_sha256}]:[]};});
 assert.deepEqual(calls,docs.map(d=>['Heat?',d.id]));assert.equal(result.sources[0].snapshot.passages[0].page_number,2);assert.equal(result.sources[1].snapshot.passages.length,0);
});
test('comparison rejects invalid selections and source substitution',async()=>{
 for(const selected of [[docs[0]],[...docs,docs[0]],[...docs,...docs],[docs[0],{...docs[1],archived:true}]])await assert.rejects(compareEvidence('Heat?',selected,async()=>({})));
 await assert.rejects(compareEvidence('Heat?',docs,async(q,id)=>{const content='Changed source';return {integrity:'verified',retrieval:{query:q,document_id:id},passages:[{document_id:id,name:'a.pdf',content,chunk_sha256:await textHash(content),source_sha256:'c'.repeat(64)}]};}),/hash mismatch/);
});
