import test from 'node:test';
import assert from 'node:assert/strict';
import {filterDocuments} from '../document-library.js';
const items=[{id:'1',name:'Bracket 10.PDF',bytes:10,created_at:'2026-10-10',archived:true},{id:'2',name:'Bracket 2.pdf',bytes:30,created_at:'2026-10-12'},{id:'3',name:'Notes.md',bytes:20,created_at:'2026-10-11'}];
test('filename and type filters combine without dropping archive metadata',()=>{
 const result=filterDocuments(items,{name:' BRACKET ',type:'pdf'});assert.deepEqual(result.map(x=>x.id),['2','1']);assert.equal(result[1].archived,true);
 assert.equal(filterDocuments(items,{name:'missing'}).length,0);assert.equal(filterDocuments(items,{type:'txt'}).length,0);
});
test('library sorting uses dates, numeric names and size without mutating input',()=>{
 for(const [sort,expected] of [['newest',['2','3','1']],['oldest',['1','3','2']],['name',['2','1','3']],['size',['2','3','1']]])assert.deepEqual(filterDocuments(items,{sort}).map(x=>x.id),expected);
 assert.deepEqual(items.map(x=>x.id),['1','2','3']);
});
