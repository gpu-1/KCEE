import test from 'node:test';
import assert from 'node:assert/strict';
import {libraryQuery,libraryPageLabel} from '../document-library.js';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync(new URL('../knowledge-ui.js',import.meta.url),'utf8').replace("import {request} from './client.js';",'').replace("import {appendPdfPageLink} from './pdf-source.js';",'').replace("import {showPdfReview} from './pdf-review.js';",'').replace("import {libraryQuery,libraryPageLabel} from './document-library.js';",'');
function setup(states){
 const elements=new Map(),posts=[];
 const get=id=>{if(!elements.has(id))elements.set(id,{hidden:true,disabled:false,value:'',files:[],addEventListener(){},removeAttribute(){},replaceChildren(){},appendChild(){}});return elements.get(id);};
 const storage=new Map();
 const request=async(path,options)=>{
  if(path==='/knowledge/imports'){posts.push(JSON.parse(options.body));return {id:'job-'+posts.length};}
  if(path.startsWith('/knowledge/imports/'))return {state:states.shift(),stage:'extracting',completed_pages:0,error:'OCR failed',result:{name:'scan.pdf',chunks:1}};
  if(path.startsWith('/knowledge/library'))return {items:[],total:0,page:1,page_size:25,pages:1};
  if(path==='/knowledge/semantic-status')return {available:false};
  throw Error('Unexpected request '+path);
 };
 vm.runInNewContext(source,{document:{getElementById:get,createElement:()=>({})},libraryQuery,libraryPageLabel,URLSearchParams,clearTimeout,request,sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},Uint8Array,btoa:s=>Buffer.from(s,'binary').toString('base64'),setTimeout});
 const raw=Buffer.from('%PDF-test');get('knowledge-file').files=[{name:'scan.pdf',size:raw.length,arrayBuffer:async()=>raw}];get('ocr-language').value='spa';
 return {get,posts};
}
for(const state of ['failed','cancelled'])test(state+' import retries exact file and OCR language with a new job',async()=>{
 const {get,posts}=setup([state,'completed']);
 await get('upload-knowledge').onclick();assert.equal(get('retry-import').hidden,false);assert.equal(get('cancel-import').hidden,true);
 // Retried bytes and language come from the failed attempt, not mutable controls.
 get('ocr-language').value='eng';get('knowledge-file').files=[];
 await get('retry-import').onclick();assert.equal(posts.length,2);assert.deepEqual(posts[1],posts[0]);assert.equal(posts[1].ocr_languages,'spa');assert.equal(get('retry-import').hidden,true);assert.equal(get('upload-knowledge').disabled,false);
});
test('changing the selected file or language clears the previous retry',async()=>{
 const {get}=setup(['failed']);await get('upload-knowledge').onclick();get('knowledge-file').onchange();assert.equal(get('retry-import').hidden,true);
});
