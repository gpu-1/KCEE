import test from 'node:test';
import assert from 'node:assert/strict';
import {pageIndicators,showPdfReview} from '../pdf-review.js';
test('OCR text indicators count literal numeric tokens and never assign confidence',()=>{
 const p=pageIndicators({method:'ocr',text:'Heat 0.525 W at 80 °C. '+ 'Reference '.repeat(10)});
 assert.equal(p.ocr,true);assert.equal(p.numericTokens,2);assert.equal(p.warnings.length,0);assert.equal(p.confidence,undefined);
});
test('blank, short and damaged text remain separate review signals',()=>{
 assert.match(pageIndicators({text:'  '}).warnings[0],/No readable/);
 assert.match(pageIndicators({text:'Short title'}).warnings[0],/Very little/);
 const p=pageIndicators({text:'A damaged \uFFFD symbol'});assert.equal(p.replacementCharacters,1);assert.equal(p.warnings.length,2);
 assert.equal(pageIndicators({text:'Text'}).ocr,false);
});
test('review navigates physical pages and keeps original text unchanged',t=>{
 const elements=new Map();const element=()=>({value:'',children:[],replaceChildren(){this.children=[];},appendChild(child){this.children.push(child);}});
 const get=id=>{if(!elements.has(id))elements.set(id,element());return elements.get(id);};
 const previous=globalThis.document;globalThis.document={getElementById:get,createElement:element};t.after(()=>{if(previous===undefined)delete globalThis.document;else globalThis.document=previous;});
 const pages=[{page_number:1,method:'ocr',text:'First 0.525 W'},{page_number:2,method:'embedded_text',text:''}];
 showPdfReview({pages,ocr_languages:'spa'},{id:'12345678-1234-1234-1234-123456789abc',name:'scan.pdf'});
 assert.equal(get('knowledge-source-text').value,pages[0].text);assert.equal(get('pdf-review-previous').disabled,true);
 assert.match(get('pdf-review-indicators').textContent,/Spanish/);assert.match(get('pdf-review-summary').textContent,/2 pages.*1 OCR/);
 assert.match(get('pdf-review-original').children[0].children[0].href,/#page=1$/);
 get('pdf-review-next').onclick();assert.equal(get('knowledge-source-text').value,'');assert.equal(get('pdf-review-next').disabled,true);
 assert.match(get('pdf-review-original').children[0].children[0].href,/#page=2$/);assert.match(get('pdf-review-indicators').textContent,/No readable/);
 get('pdf-review-previous').onclick();assert.equal(get('knowledge-source-text').value,pages[0].text);
});
