import {appendPdfPageLink} from './pdf-source.js';
// These are transparent text checks, never OCR confidence or engineering approval.
export function pageIndicators(page){
 const text=page.text||'',characters=[...text.trim()].length;
 const replacementCharacters=[...text].filter(c=>c==='\uFFFD').length;
 const numericTokens=(text.match(/\d+(?:[.,]\d+)*/g)||[]).length;
 const warnings=[];
 if(!characters)warnings.push('No readable text. Check whether the original page is blank or extraction missed its content.');
 else if(characters<80)warnings.push('Very little text (fewer than 80 characters). This may be a short page or missed content.');
 if(replacementCharacters)warnings.push('Replacement characters found. Some characters may not have been decoded correctly.');
 return {characters,replacementCharacters,numericTokens,warnings,ocr:page.method==='ocr'};
}
export function showPdfReview(extracted,item){
 const get=id=>document.getElementById(id),pages=extracted.pages;
 if(!Array.isArray(pages)||!pages.length)throw new Error('PDF pages unavailable');
 const indicators=pages.map(pageIndicators),ocr=indicators.filter(p=>p.ocr).length,flagged=indicators.filter(p=>p.warnings.length).length;
 get('pdf-review').hidden=false;
 get('pdf-review-summary').textContent=pages.length+' pages · '+ocr+' OCR pages · '+flagged+' pages with text warnings. Text checks are not recognition confidence scores. Compare numbers, units, symbols and reading order with the original. No review approval is recorded.';
 const select=get('pdf-review-page');select.replaceChildren();
 for(let index=0;index<pages.length;index++){
  const option=document.createElement('option'),page=pages[index],info=indicators[index];option.value=String(index);
  option.textContent='Page '+page.page_number+(info.ocr?' · OCR':'')+(info.warnings.length?' · Check text':'');select.appendChild(option);
 }
 select.value='0';
 const render=()=>{
  const index=Number(select.value),page=pages[index],info=indicators[index];
  get('knowledge-source-text').value=page.text;
  const method=info.ocr?'OCR — manual comparison needed':page.method==='embedded_text'?'Embedded text': 'Extraction method not recorded';
  const language={'eng':'English','spa':'Spanish','eng+spa':'English + Spanish'}[extracted.ocr_languages]||'not recorded';
  get('pdf-review-indicators').textContent=method+(info.ocr?' · '+language:'')+' · '+info.characters+' characters · '+info.numericTokens+' numeric tokens · '+info.replacementCharacters+' replacement characters. '+(info.warnings.join(' ')||'No empty, short-text or replacement-character warnings. This does not confirm text accuracy.');
  get('pdf-review-original').replaceChildren();appendPdfPageLink(get('pdf-review-original'),{...item,document_id:item.id,page_number:page.page_number});
  get('pdf-review-previous').disabled=index===0;get('pdf-review-next').disabled=index===pages.length-1;
 };
 select.onchange=render;
 get('pdf-review-previous').onclick=()=>{select.value=String(Number(select.value)-1);render();};
 get('pdf-review-next').onclick=()=>{select.value=String(Number(select.value)+1);render();};
 render();
}
