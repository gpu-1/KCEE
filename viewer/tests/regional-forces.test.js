import test from 'node:test';
import assert from 'node:assert/strict';
import {regionalRows} from '../regional-forces-view.js';
const data={schema:'native-regional-loads-v1',comparisons:[{regions:[{region:'Base',signed_changes:{pressure_force_N:[-2,3,4],viscous_moment_N_m:[5,-6,7]}}]}]};
test('regional display preserves signed axes and force/moment units',()=>{assert.deepEqual(regionalRows(data,0),[{name:'Base',value:-2}]);assert.deepEqual(regionalRows(data,0,'viscous',true,1),[{name:'Base',value:-6}]);});
test('regional display rejects malformed vectors and unknown comparisons',()=>{assert.throws(()=>regionalRows(data,3));assert.throws(()=>regionalRows(data,0,'anything'));assert.throws(()=>regionalRows({...data,schema:'wrong'},0));const bad=structuredClone(data);bad.comparisons[0].regions[0].signed_changes.pressure_force_N[0]=Infinity;assert.throws(()=>regionalRows(bad,0));});
