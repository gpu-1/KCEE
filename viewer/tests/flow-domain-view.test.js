import test from 'node:test';
import assert from 'node:assert/strict';
import {probeRows} from '../flow-domain-view.js';
function fixture(){return {schema:'kcee.bracket-flow-domain.v1',studies:['base','expanded','far'].map((domain_name,i)=>({domain_name,probes:[{name:'wake',speed_m_s:.01,kinematic_pressure_m2_s2:100*i,pressure_minus_upstream_m2_s2:-.00001,maximum_support_distance_m:.002}]}))};}
test('domain probe table uses referenced pressure, not raw outlet gauge',()=>{const rows=probeRows(fixture(),'wake');assert.deepEqual(rows.map(r=>r.pressureDifference),[-.00001,-.00001,-.00001]);assert.equal(rows[0].supportRadiusMm,2);});
test('unavailable or nonfinite referenced values are not displayed as zero',()=>{const data=fixture();delete data.studies[1].probes[0].pressure_minus_upstream_m2_s2;assert.throws(()=>probeRows(data,'wake'));assert.throws(()=>probeRows(fixture(),'unknown'));});
