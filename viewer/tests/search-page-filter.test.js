import test from 'node:test';
import assert from 'node:assert/strict';
import {pageChoices,pageMatches} from '../search-page-filter.js';
test('physical pages are unique, sorted and bounded; plaintext is separate',()=>{
 assert.deepEqual(pageChoices([{page:2},{page:null},{page:1},{page:2},{page:301},{page:0}]),[1,2]);assert.equal(pageMatches(null,'text'),true);assert.equal(pageMatches(2,'text'),false);assert.equal(pageMatches(2,'2'),true);assert.equal(pageMatches(1,'2'),false);assert.equal(pageMatches(null,''),true);
});
