import test from 'node:test';
import assert from 'node:assert/strict';
import {pdfPageUrl} from '../pdf-source.js';
const chunk={name:'scan.pdf',document_id:'12345678-1234-1234-1234-123456789abc',page_number:2};
test('PDF links open the physical cited page without changing the download route',()=>{
 assert.equal(pdfPageUrl(chunk),'/api/knowledge/documents/'+chunk.document_id+'/source?inline=true#page=2');
 assert.equal(pdfPageUrl({...chunk,name:'notes.txt'}),null);
 for(const page_number of [null,0,-1,301,1.5,'2'])assert.equal(pdfPageUrl({...chunk,page_number}),null);
 assert.throws(()=>pdfPageUrl({...chunk,document_id:'../bad'}),/identity/);
});
