import test from 'node:test';
import assert from 'node:assert/strict';
import {highlightSegments,renderHighlightedPassage} from '../search-highlight.js';
test('whole tokens preserve source text, decimals, punctuation and Unicode',()=>{
 const text='Heat: 0.525 W. HEAT heatflow; TÉRMICA térmica.\n<script>heat</script>';
 const segments=highlightSegments(text,'What is heat, 0.525 W and térmica?');
 assert.equal(segments.map(s=>s.text).join(''),text);
 assert.deepEqual(segments.filter(s=>s.match).map(s=>s.text),['Heat','0.525','W','HEAT','TÉRMICA','térmica','heat']);
 assert.equal(highlightSegments('0.525 0.5 heatflow','heat 0.5').filter(s=>s.match).map(s=>s.text).join(''),'0.5');
});
test('empty, common-word and semantic-only questions leave text intact',()=>{
 for(const q of ['','what is the','conduction']){const parts=highlightSegments('Thermal transport.\n',q);assert.equal(parts.map(p=>p.text).join(''),'Thermal transport.\n');assert.ok(parts.every(p=>!p.match));}
});
test('rendering uses literal text nodes and disabling restores exact source',()=>{
 const children=[],element={replaceChildren(){children.length=0;},ownerDocument:{createElement:tag=>({tag})},appendChild(node){children.push(node);}};
 const text='<img src=x onerror=alert(1)> heat';renderHighlightedPassage(element,text,'heat');assert.equal(children.map(n=>n.textContent).join(''),text);assert.equal(children.filter(n=>n.tag==='mark').length,1);assert.ok(children.every(n=>['span','mark'].includes(n.tag)));
 renderHighlightedPassage(element,text,'heat',false);assert.equal(element.textContent,text);assert.equal(children.length,0);
});
