import test from 'node:test';
import assert from 'node:assert/strict';
import {exportSavedSearches,parseSavedSearchExport} from '../saved-search-transfer.js';
import {saveSearch,loadSavedSearches,mergeSavedSearches,labelSavedSearch,filterSavedSearches} from '../saved-searches.js';
const store=()=>{const m=new Map();return {getItem:k=>m.get(k),setItem:(k,v)=>m.set(k,v)};};
test('transfer roundtrip preserves scoped questions; preview is read-only and merge skips duplicates',async()=>{
 const a=store(),b=store();saveSearch(a,'Heat?',{id:'12345678-1234-1234-1234-123456789abc',name:'a.pdf'});saveSearch(a,'Temperature?');const exported=await exportSavedSearches(loadSavedSearches(a));const rows=await parseSavedSearchExport(JSON.stringify(exported));saveSearch(b,'Temperature?');const original=loadSavedSearches(b);assert.equal(mergeSavedSearches(b,rows).added,1);assert.deepEqual(loadSavedSearches(b),original);const result=mergeSavedSearches(b,rows,true);assert.equal(result.skipped,1);assert.equal(result.rows[1].document.name,'a.pdf');assert.equal(mergeSavedSearches(b,rows,true).added,0);assert.equal(loadSavedSearches(b)[0].id,original[0].id);
});
test('changed or wrong files fail and overflow leaves storage unchanged',async()=>{
 const record=await exportSavedSearches([]);record.exported_at='2020-01-01';await assert.rejects(parseSavedSearchExport(JSON.stringify(record)),/hash/);await assert.rejects(parseSavedSearchExport('{}'));const s=store();for(let i=0;i<50;i++)saveSearch(s,'Q'+i);const original=loadSavedSearches(s);assert.throws(()=>mergeSavedSearches(s,[{id:'new',question:'Extra',document:null,saved_at:new Date().toISOString()}],true),/exceed/);assert.deepEqual(loadSavedSearches(s),original);
});

test('page ranges survive export/import, have distinct identity and validate before writing',async()=>{
 const a=store(),doc={id:'12345678-1234-1234-1234-123456789abc',name:'a.pdf'};
 saveSearch(a,'Heat?',doc);saveSearch(a,'Heat?',doc,undefined,{start:2,end:3});assert.equal(loadSavedSearches(a).length,2);
 const data=await exportSavedSearches(loadSavedSearches(a));assert.equal(data.schema,'kcee.saved-searches-export.v3');const rows=await parseSavedSearchExport(JSON.stringify(data));assert.deepEqual(rows[0].page_range,{start:2,end:3});const b=store();assert.equal(mergeSavedSearches(b,rows,true).added,2);assert.equal(mergeSavedSearches(b,rows,true).skipped,2);
 const before=loadSavedSearches(a);assert.throws(()=>saveSearch(a,'Invalid',doc,undefined,{start:3,end:2}));assert.deepEqual(loadSavedSearches(a),before);
});

test('labels persist on save, filter by label and scope, and survive transfer',async()=>{
 const a=store();saveSearch(a,'Heat?',{id:'12345678-1234-1234-1234-123456789abc',name:'a.pdf'},undefined,{start:2,end:2});const id=loadSavedSearches(a)[0].id;labelSavedSearch(a,id,'Cooling review');saveSearch(a,'Heat?',loadSavedSearches(a)[0].document,undefined,{start:2,end:2});assert.equal(loadSavedSearches(a)[0].label,'Cooling review');assert.equal(filterSavedSearches(loadSavedSearches(a),'cooling').length,1);assert.equal(filterSavedSearches(loadSavedSearches(a),'missing').length,0);const rows=await parseSavedSearchExport(JSON.stringify(await exportSavedSearches(loadSavedSearches(a))));const b=store();mergeSavedSearches(b,rows,true);assert.equal(loadSavedSearches(b)[0].label,'Cooling review');assert.throws(()=>labelSavedSearch(a,id,'x'.repeat(101)));
});
test('original transfer versions remain readable',async()=>{
 const {textHash}=await import('../search-export.js');for(const schema of ['kcee.saved-searches-export.v1','kcee.saved-searches-export.v2']){const r={schema,exported_at:'2026-10-15T00:00:00Z',searches:[]};r.snapshot_sha256=await textHash(JSON.stringify(r));assert.deepEqual(await parseSavedSearchExport(JSON.stringify(r)),[]);}
});
