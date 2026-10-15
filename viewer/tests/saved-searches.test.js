import test from 'node:test';
import assert from 'node:assert/strict';
import {loadSavedSearches,saveSearch,removeSavedSearch} from '../saved-searches.js';
const storage=()=>{const m=new Map();return {getItem:k=>m.get(k),setItem:(k,v)=>m.set(k,v)};};
const doc={id:'12345678-1234-1234-1234-123456789abc',name:'reference.pdf'};
test('saved questions retain scopes across reload, deduplicate and remove independently',()=>{
 const s=storage();saveSearch(s,' Heat? ',doc);saveSearch(s,'Heat?');let rows=saveSearch(s,'Heat?',doc);assert.equal(rows.length,2);assert.equal(rows[0].document.id,doc.id);assert.equal(loadSavedSearches(s)[0].question,'Heat?');removeSavedSearch(s,rows[0].id);assert.equal(loadSavedSearches(s)[0].document,null);
});
test('invalid storage, blank questions and capacity limits never overwrite saved records',()=>{
 const s=storage();assert.throws(()=>saveSearch(s,'  '));for(let i=0;i<50;i++)saveSearch(s,'Question '+i);assert.throws(()=>saveSearch(s,'Overflow'),/50/);assert.equal(loadSavedSearches(s).length,50);assert.equal(saveSearch(s,'Question 0').length,50);s.setItem('kcee.saved-searches.v1','{}');assert.throws(()=>loadSavedSearches(s));assert.throws(()=>saveSearch(s,'Keep corrupted data'));
});
