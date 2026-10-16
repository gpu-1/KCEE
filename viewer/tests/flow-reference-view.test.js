import test from 'node:test';
import assert from 'node:assert/strict';
import {referenceSeries,decompositionRows} from '../flow-reference-view.js';
test('reference chart preserves zero, percentages and rejects invalid values',()=>{
 const data={schema:'kcee.bracket-flow-reference.v1',comparisons:[{label:'Domain',maximum_upstream_referenced_change_normalized:0,maximum_local_anchor_change_normalized:.03,maximum_local_pair_change_normalized:.01}]};
 assert.deepEqual(referenceSeries(data),[{label:'Domain',values:[0,3,1]}]);data.comparisons[0].maximum_local_pair_change_normalized=NaN;assert.throws(()=>referenceSeries(data));assert.throws(()=>referenceSeries({}));
});
test('signed decomposition values retain closure and reject mismatch',()=>{
 const c={probes:[{name:'below',upstream_referenced_change_m2_s2:-.000005,local_anchor_change_m2_s2:.000005,anchor_upstream_change_m2_s2:-.00001,closure_residual_m2_s2:0}]};
 const row=decompositionRows(c)[0];assert.equal(row.name,'below');assert.ok(Math.abs(row.values[0]+10)<1e-12);assert.ok(Math.abs(row.values[1]-10)<1e-12);assert.ok(Math.abs(row.values[2]+20)<1e-12);c.probes[0].local_anchor_change_m2_s2=0;assert.throws(()=>decompositionRows(c));
});

test('reference study is wired to an actual result panel and controls',async()=>{
 const {readFile}=await import('node:fs/promises');const html=await readFile(new URL('../index.html',import.meta.url),'utf8');
 for(const id of ['flow-reference-results','reference-domain-note','verify-flow-joint','verify-flow-reference','reference-chart','reference-cases','reference-checks','reference-comparison','reference-decomposition','reference-pairs','reference-velocity','reference-csv','reference-json'])assert.equal(html.split('id="'+id+'"').length-1,1,id+' must exist once');
});

test('joint schema retains all five direct comparisons',()=>{
 const c={label:'Fine far to outer + grid',maximum_upstream_referenced_change_normalized:.01,maximum_local_anchor_change_normalized:.005,maximum_local_pair_change_normalized:0};
 const rows=referenceSeries({schema:'kcee.bracket-flow-reference.v2',comparisons:Array(5).fill(c)});assert.equal(rows.length,5);assert.deepEqual(rows[4].values,[1,.5,0]);
});
