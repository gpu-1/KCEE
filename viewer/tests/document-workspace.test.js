import test from 'node:test';
import assert from 'node:assert/strict';
import {workspaceRoute} from '../document-workspace.js';
test('document workspace routes support direct links and keep design/help routes distinct',()=>{
 for(const key of ['library','search','compare','verify','review','backup'])assert.equal(workspaceRoute('#documents/'+key),key);
 assert.equal(workspaceRoute('#documents'),'library');assert.equal(workspaceRoute('#documents/unknown'),'library');assert.equal(workspaceRoute('#geometry-help'),null);assert.equal(workspaceRoute(''),null);
});
