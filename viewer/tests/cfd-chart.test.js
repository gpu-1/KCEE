import test from 'node:test';
import assert from 'node:assert/strict';
import {profileSeries} from '../cfd-chart.js';
test('CFD chart preserves numerical and analytical velocities with physical gap units',()=>{const r=profileSeries({cells:2,profile:[{y_m:.001,velocity_m_s:.1,analytical_velocity_m_s:.11},{y_m:.002,velocity_m_s:.2,analytical_velocity_m_s:.21}]});assert.deepEqual(r.gap,[1,2]);assert.deepEqual(r.velocity,[.1,.2]);assert.deepEqual(r.exact,[.11,.21]);assert.throws(()=>profileSeries({cells:2,profile:[]}));});
