export function pageChoices(records){return [...new Set(records.filter(r=>Number.isInteger(r.page)&&r.page>=1&&r.page<=300).map(r=>r.page))].sort((a,b)=>a-b);}
export function pageMatches(page,filter){return filter===''||(filter==='text'?page===null:page===Number(filter));}
export function installPageFilter(document){
 const select=document.getElementById('search-page-filter'),summary=document.getElementById('search-page-filter-status'),root=document.getElementById('knowledge-search-results'),controls=document.getElementById('search-page-controls');
 function records(){return Array.from(root.children).map(node=>({node,page:node.dataset.pdfPage?Number(node.dataset.pdfPage):null}));}
 function apply(){const rows=records();let shown=0;for(const row of rows){row.node.hidden=!pageMatches(row.page,select.value);if(!row.node.hidden)shown++;}summary.textContent='Showing '+shown+' of '+rows.length+' retrieved passages.';}
 function reset(){const rows=records();select.replaceChildren();const add=(value,label)=>{const option=document.createElement('option');option.value=value;option.textContent=label;select.append(option);};add('','All retrieved pages');for(const page of pageChoices(rows))add(String(page),'PDF page '+page);if(rows.some(r=>r.page===null))add('text','Text documents');select.value='';controls.hidden=rows.length===0;apply();}
 select.onchange=apply;new MutationObserver(reset).observe(root,{childList:true});reset();
}
