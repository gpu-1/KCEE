import test from 'node:test';
import assert from 'node:assert/strict';
import {handoffSources,scopeRequest,scopeMatches,scopeDescription} from '../assistant-scope.js';
const sources=[{id:'12345678-1234-1234-1234-123456789abc',name:'a.pdf'},{id:'00000000-0000-4000-8000-000000000001',name:'b.pdf'}];
test('single and multiple source handoffs preserve identity and request shape',()=>{
 assert.deepEqual(handoffSources({document:sources[0]}),[sources[0]]);assert.deepEqual(handoffSources({documents:sources}),sources);
 assert.deepEqual(scopeRequest(sources),{document_ids:sources.map(s=>s.id)});assert.deepEqual(scopeRequest([sources[0]]),{document_id:sources[0].id});assert.deepEqual(scopeRequest([]),{});
 assert.equal(handoffSources({documents:[sources[0],sources[0]]}),null);assert.equal(handoffSources({documents:[{id:'bad',name:'a.pdf'}]}),null);
});
test('answer scope requires all selected identities and rejects outside citations',()=>{
 const evidence={document_search:{scopes:sources.map(s=>({document_id:s.id,name:s.name,source_sha256:'a'.repeat(64)}))},documents:sources.map(s=>({document_id:s.id}))};
 assert.equal(scopeMatches(sources,evidence),true);assert.ok(scopeDescription(evidence).includes('b.pdf'));assert.ok(scopeDescription(evidence).includes('a'.repeat(64)));
 assert.equal(scopeMatches([sources[0]],evidence),false);evidence.documents.push({document_id:'outside'});assert.equal(scopeMatches(sources,evidence),false);
});

test('page-limited scope survives handoff and rejects broader evidence or out-of-range citations',()=>{
 const source={...sources[0],page_range:{start:2,end:3}},scoped=handoffSources({document:source});assert.deepEqual(scopeRequest(scoped),{document_id:source.id,page_start:2,page_end:3});
 const evidence={document_search:{scope:{document_id:source.id,name:source.name,source_sha256:'a'.repeat(64),page_range:{start:2,end:3}}},documents:[{document_id:source.id,page_number:2}]};assert.equal(scopeMatches(scoped,evidence),true);assert.match(scopeDescription(evidence),/physical pages 2–3/);evidence.documents[0].page_number=1;assert.equal(scopeMatches(scoped,evidence),false);evidence.documents=[];delete evidence.document_search.scope.page_range;assert.equal(scopeMatches(scoped,evidence),false);assert.equal(handoffSources({documents:[source,sources[1]]}),null);
});
