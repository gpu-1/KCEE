import test from 'node:test';
import assert from 'node:assert/strict';
import {libraryQuery,libraryPageLabel} from '../document-library.js';
test('server library query carries pagination, literal filename filter and ordering',()=>{
 const query=libraryQuery({includeArchived:true,page:5,pageSize:25,name:'A & B%?.pdf',type:'pdf',sort:'size'});
 const p=new URL('http://local'+query).searchParams;
 assert.equal(p.get('name'),'A & B%?.pdf');assert.equal(p.get('page'),'5');assert.equal(p.get('page_size'),'25');assert.equal(p.get('include_archived'),'true');assert.equal(p.get('sort'),'size');assert.equal(p.get('file_type'),'pdf');
});
test('page labels describe final and empty pages',()=>{
 assert.equal(libraryPageLabel({total:105,page:5,page_size:25,pages:5,items:Array(5)}),'101–105 of 105 matching documents · Page 5 of 5');
 assert.equal(libraryPageLabel({total:0,items:[]}), 'No documents match these filters.');
});
