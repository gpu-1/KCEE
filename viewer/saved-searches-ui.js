import {loadSavedSearches,saveSearch,removeSavedSearch} from './saved-searches.js';
const get=id=>document.getElementById(id);
function status(message){get('saved-search-status').textContent=message;}
function render(){
 const list=get('saved-search-list');list.replaceChildren();
 try{const rows=loadSavedSearches(localStorage);if(!rows.length){status('No saved searches yet.');return;}
 for(const row of rows){const card=document.createElement('section'),question=document.createElement('p'),scope=document.createElement('p'),load=document.createElement('button'),remove=document.createElement('button');question.textContent=row.question;scope.className='hint';scope.textContent=(row.document?'Document: '+row.document.name:'All active documents')+' · Saved '+new Date(row.saved_at).toLocaleString();load.textContent='Load search';remove.textContent='Remove';
 load.onclick=()=>{if(get('search-knowledge').disabled){status('Wait for the running search to finish.');return;}const select=get('knowledge-search-document');if(row.document&&!Array.from(select.options).some(o=>o.value===row.document.id)){const option=document.createElement('option');option.value=row.document.id;option.textContent=row.document.name;select.append(option);}select.value=row.document?.id||'';select.dispatchEvent(new Event('change',{bubbles:true}));get('knowledge-search-question').value=row.question;get('knowledge-search-question').dispatchEvent(new Event('input',{bubbles:true}));get('knowledge-search-results').replaceChildren();get('knowledge-search-status').textContent='Saved question loaded. Press Search to retrieve and verify current sources. Unavailable or archived documents cannot be searched.';get('knowledge-search-question').focus();status('Loaded saved question and document selection.');};
 remove.onclick=()=>{const confirm=document.createElement('button'),cancel=document.createElement('button');confirm.textContent='Confirm removal';cancel.textContent='Cancel';remove.hidden=true;card.append(confirm,cancel);confirm.onclick=()=>{try{removeSavedSearch(localStorage,row.id);render();status('Saved search removed.');}catch(error){status(error.message);}};cancel.onclick=()=>{confirm.remove();cancel.remove();remove.hidden=false;};};
 card.append(question,scope,load,remove);list.append(card);}
 }catch(error){status('Saved searches unavailable: '+error.message);}
}
get('save-current-search').onclick=()=>{try{const select=get('knowledge-search-document');saveSearch(localStorage,get('knowledge-search-question').value,select.value?{id:select.value,name:select.selectedOptions[0].textContent}:null);render();status('Search saved in this browser.');}catch(error){status('Could not save: '+error.message);}};
window.addEventListener('storage',render);render();
