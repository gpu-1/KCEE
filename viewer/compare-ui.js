import {closeDocumentWorkspace} from './document-workspace.js';
import {comparisonSnapshot,comparisonText} from './comparison-export.js';
import {request} from './client.js';
import {compareEvidence} from './compare-evidence.js';
import {appendPdfPageLink} from './pdf-source.js';
const selected=new Map(),choices=new Map();let revision=0,busy=false,exportUrls=[],handoff=null;
const get=id=>document.getElementById(id);
export function clearComparison(){revision++;handoff=null;get('use-comparison-in-study').hidden=true;for(const url of exportUrls)URL.revokeObjectURL(url);exportUrls=[];get('comparison-downloads').hidden=true;for(const id of ['download-comparison-text','download-comparison-json'])get(id).removeAttribute('href');get('reference-comparison-results').replaceChildren();get('reference-comparison-status').textContent='Choose two or three documents in the library, then enter a comparison question.';}
function refreshSelection(){
 get('compare-selected').replaceChildren();
 for(const item of selected.values()){const row=document.createElement('p'),name=document.createElement('span'),remove=document.createElement('button');name.textContent=item.name+' · '+item.id.slice(0,8)+' ';remove.textContent='Remove';remove.setAttribute('aria-label','Remove '+item.name+' from comparison');remove.disabled=busy;remove.onclick=()=>{selected.delete(item.id);clearComparison();refreshSelection();};row.append(name,remove);get('compare-selected').appendChild(row);}
 for(const [id,input] of choices){input.checked=selected.has(id);input.disabled=busy||(!selected.has(id)&&selected.size>=3);}
 get('compare-references').disabled=busy||selected.size<2;get('clear-compare-references').disabled=busy||!selected.size;
}
export function addCompareChoice(row,item){
 if(item.archived){if(selected.delete(item.id)){clearComparison();refreshSelection();}return;}
 const label=document.createElement('label'),input=document.createElement('input');label.className='knowledge-opt-in';input.type='checkbox';input.setAttribute('aria-label','Compare '+item.name);label.append(input,document.createTextNode(' Compare reference'));choices.set(item.id,input);
 input.onchange=()=>{if(input.checked){if(selected.size>=3){input.checked=false;return;}selected.set(item.id,item);}else selected.delete(item.id);clearComparison();refreshSelection();};row.appendChild(label);refreshSelection();
}
export function removeCompareDocument(id){selected.delete(id);clearComparison();refreshSelection();}
export function beginComparePage(){choices.clear();}
get('clear-compare-references').onclick=()=>{selected.clear();clearComparison();refreshSelection();};
get('knowledge-search-question').addEventListener('input',clearComparison);
get('compare-references').onclick=async()=>{
 const question=get('comparison-question').value.trim();clearComparison();const ticket=revision;busy=true;refreshSelection();get('reference-comparison-status').textContent='Searching and verifying each selected source…';
 try{
  const result=await compareEvidence(question,[...selected.values()],(question,id)=>request('/knowledge/search',{method:'POST',headers:{'Content-Type':'application/json','X-KCEE-Knowledge':'1'},body:JSON.stringify({question,document_id:id})}));
  if(ticket!==revision)return;
  for(const [index,source] of result.sources.entries()){
   const panel=document.createElement('section'),title=document.createElement('h4'),identity=document.createElement('p'),method=document.createElement('p');title.textContent='Source '+(index+1)+': '+source.document.name;identity.textContent='Original SHA-256: '+source.document.source_sha256;identity.className='hint';method.className='hint';const snapshot=source.snapshot;method.textContent=snapshot.passages.length+' verified passages · '+(snapshot.retrieval.semantic_embeddings?'Semantic + keyword':'Keyword')+(snapshot.retrieval.semantic_fallback?' · '+snapshot.retrieval.semantic_fallback:'');panel.append(title,identity,method);
   if(!snapshot.passages.length){const empty=document.createElement('p');empty.textContent='No matching active passages. No other source was substituted.';panel.appendChild(empty);}
   for(const chunk of snapshot.passages){const card=document.createElement('details'),heading=document.createElement('summary'),text=document.createElement('pre'),hash=document.createElement('p');heading.textContent='Source '+(index+1)+' ['+chunk.citation_id+']'+(chunk.page_number?' · page '+chunk.page_number:' · lines '+chunk.line_start+'–'+chunk.line_end)+(chunk.extraction_method==='ocr'?' · OCR':'');text.textContent=chunk.content;hash.textContent='Passage SHA-256: '+chunk.chunk_sha256;hash.className='hint';card.append(heading,text,hash);appendPdfPageLink(card,chunk);panel.appendChild(card);}
   get('reference-comparison-results').appendChild(panel);
  }
  const snapshot=await comparisonSnapshot(result);if(ticket!==revision)return;
  for(const [id,text,type,extension] of [['download-comparison-text',comparisonText(snapshot),'text/plain;charset=utf-8','txt'],['download-comparison-json',JSON.stringify(snapshot,null,2),'application/json','json']]){const url=URL.createObjectURL(new Blob([text],{type}));exportUrls.push(url);get(id).href=url;get(id).download='kcee-reference-comparison-'+snapshot.exported_at.replace(/[:.]/g,'-')+'.'+extension;}
  get('comparison-downloads').hidden=false;handoff={question:result.question,documents:result.sources.map(s=>({id:s.document.id,name:s.document.name}))};get('use-comparison-in-study').hidden=false;
  get('reference-comparison-status').textContent='Compared '+result.sources.length+' sources for: '+result.question+'. Citations are local to each source. Compare assumptions, units and relevance; these passages do not establish agreement or engineering validity.';
 }catch(error){if(ticket===revision)get('reference-comparison-status').textContent=error.message;}
 finally{busy=false;refreshSelection();}
};

get('use-comparison-in-study').onclick=()=>{if(!handoff)return;const event=new CustomEvent('kcee-study-question',{detail:handoff,cancelable:true});document.dispatchEvent(event);if(event.defaultPrevented){closeDocumentWorkspace();get('assistant-question').focus();get('assistant-question').scrollIntoView({block:'center'});}else get('reference-comparison-status').textContent='Select a verified study and wait for any running explanation before using these references.';};
