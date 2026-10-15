import {verifyNoteExport,noteExportText} from './note-export.js';
import {request} from './client.js';
const drafts=new Map();let revision=0,exportRevision=0,exportUrls=[];
function clearNoteExports(){exportRevision++;for(const url of exportUrls)URL.revokeObjectURL(url);exportUrls=[];document.getElementById('page-note-downloads').hidden=true;for(const id of ['download-page-notes-text','download-page-notes-json'])document.getElementById(id).removeAttribute('href');}
export function showPageNotes(item,page){
 clearNoteExports();
 const get=id=>document.getElementById(id),key=item.id+'/'+page.page_number,ticket=++revision;
 const path='/knowledge/documents/'+item.id+'/pages/'+page.page_number+'/notes';
 const input=get('page-note-text'),save=get('save-page-note'),history=get('page-note-history'),older=get('older-page-notes');let cursor=null,loadRevision=0;
 const prepare=get('prepare-page-notes-export');prepare.disabled=false;
 prepare.onclick=async()=>{clearNoteExports();const exportTicket=exportRevision;prepare.disabled=true;save.disabled=true;get('page-notes-status').textContent='Preparing the complete saved note history…';try{const record=await request(path+'/export');await verifyNoteExport(record,item,page);if(ticket!==revision||exportTicket!==exportRevision)return;for(const [id,text,type,extension] of [['download-page-notes-text',noteExportText(record),'text/plain;charset=utf-8','txt'],['download-page-notes-json',JSON.stringify(record,null,2),'application/json','json']]){const url=URL.createObjectURL(new Blob([text],{type}));exportUrls.push(url);get(id).href=url;get(id).download='kcee-page-'+page.page_number+'-notes-'+record.exported_at.replace(/[:.]/g,'-')+'.'+extension;}get('page-note-downloads').hidden=false;get('page-notes-status').textContent='Export ready: '+record.note_count+' saved notes for page '+page.page_number+'.';}catch(error){if(ticket===revision&&exportTicket===exportRevision)get('page-notes-status').textContent=error.message;}finally{if(ticket===revision){prepare.disabled=false;save.disabled=false;}}};
 input.value=drafts.get(key)||'';input.oninput=()=>drafts.set(key,input.value);input.disabled=false;save.disabled=false;history.replaceChildren();older.hidden=true;
 get('page-notes-status').textContent='Loading notes for page '+page.page_number+'…';
 async function load(append=false){const loadTicket=++loadRevision;older.disabled=true;
  try{const data=await request(path+(append&&cursor?'?before='+cursor:''));if(ticket!==revision||loadTicket!==loadRevision)return;
   if(data.identity.source_sha256!==item.source_sha256||data.identity.page_text_sha256!==page.text_sha256)throw new Error('Review note identity mismatch');
   if(!append)history.replaceChildren();
   for(const note of data.items){const card=document.createElement('details'),title=document.createElement('summary'),text=document.createElement('pre'),hash=document.createElement('p');title.textContent='Note '+note.id+' · '+new Date(note.created_at).toLocaleString();text.textContent=note.note;hash.className='hint';hash.textContent='Note SHA-256: '+note.note_sha256+' · Page text SHA-256: '+note.page_text_sha256;card.append(title,text,hash);history.appendChild(card);}
   cursor=data.next_before;older.hidden=!cursor;get('page-notes-status').textContent=history.children.length+' saved notes shown for page '+page.page_number+'.';
  }catch(error){if(ticket===revision&&loadTicket===loadRevision)get('page-notes-status').textContent=error.message;}finally{if(ticket===revision&&loadTicket===loadRevision)older.disabled=false;}
 }
 older.onclick=()=>load(true);
 save.onclick=async()=>{const text=input.value;if(!text.trim()){get('page-notes-status').textContent='Enter a review observation first.';return;}clearNoteExports();prepare.disabled=true;save.disabled=true;input.disabled=true;
  try{await request(path,{method:'POST',headers:{'Content-Type':'application/json','X-KCEE-Knowledge':'1'},body:JSON.stringify({source_sha256:item.source_sha256,page_text_sha256:page.text_sha256,note:text})});if(drafts.get(key)===text)drafts.delete(key);if(ticket===revision){input.value='';await load();get('page-notes-status').textContent='Note saved for page '+page.page_number+'. Original text is unchanged.';}}
  catch(error){if(ticket===revision)get('page-notes-status').textContent=error.message;}
  finally{if(ticket===revision){save.disabled=false;input.disabled=false;prepare.disabled=false;}}
 };
 load();
}
