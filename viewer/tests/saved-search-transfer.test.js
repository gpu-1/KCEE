import test from 'node:test';
import assert from 'node:assert/strict';
import {exportSavedSearches,parseSavedSearchExport} from '../saved-search-transfer.js';
import {saveSearch,loadSavedSearches,mergeSavedSearches} from '../saved-searches.js';
const store=()=>{const m=new Map();return {getItem:k=>m.get(k),setItem:(k,v)=>m.set(k,v)};};
test('transfer roundtrip preserves scoped questions; preview is read-only and merge skips duplicates',async()=>{
 const a=store(),b=store();saveSearch(a,'Heat?',{id:'12345678-1234-1234-1234-123456789abc',name:'a.pdf'});saveSearch(a,'Temperature?');const exported=await exportSavedSearches(loadSavedSearches(a));const rows=await parseSavedSearchExport(JSON.stringify(exported));saveSearch(b,'Temperature?');const original=loadSavedSearches(b);assert.equal(mergeSavedSearches(b,rows).added,1);assert.deepEqual(loadSavedSearches(b),original);const result=mergeSavedSearches(b,rows,true);assert.equal(result.skipped,1);assert.equal(result.rows[1].document.name,'a.pdf');assert.equal(mergeSavedSearches(b,rows,true).added,0);assert.equal(loadSavedSearches(b)[0].id,original[0].id);
});
test('changed or wrong files fail and overflow leaves storage unchanged',async()=>{
 const record=await exportSavedSearches([]);record.exported_at='2020-01-01';await assert.rejects(parseSavedSearchExport(JSON.stringify(record)),/hash/);await assert.rejects(parseSavedSearchExport('{}'));const s=store();for(let i=0;i<50;i++)saveSearch(s,'Q'+i);const original=loadSavedSearches(s);assert.throws(()=>mergeSavedSearches(s,[{id:'new',question:'Extra',document:null,saved_at:new Date().toISOString()}],true),/exceed/);assert.deepEqual(loadSavedSearches(s),original);
});
