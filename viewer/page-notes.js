import {request} from './client.js';
const drafts=new Map();let revision=0;
export function showPageNotes(item,page){
 const get=id=>document.getElementById(id),key=item.id+'/'+page.page_number,ticket=++revision;
 const path='/knowledge/documents/'+item.id+'/pages/'+page.page_number+'/notes';
 const input=get('page-note-text'),save=get('save-page-note'),history=get('page-note-history'),older=get('older-page-notes');let cursor=null,loadRevision=0;
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
 save.onclick=async()=>{const text=input.value;if(!text.trim()){get('page-notes-status').textContent='Enter a review observation first.';return;}save.disabled=true;input.disabled=true;
  try{await request(path,{method:'POST',headers:{'Content-Type':'application/json','X-KCEE-Knowledge':'1'},body:JSON.stringify({source_sha256:item.source_sha256,page_text_sha256:page.text_sha256,note:text})});if(drafts.get(key)===text)drafts.delete(key);if(ticket===revision){input.value='';await load();get('page-notes-status').textContent='Note saved for page '+page.page_number+'. Original text is unchanged.';}}
  catch(error){if(ticket===revision)get('page-notes-status').textContent=error.message;}
  finally{if(ticket===revision){save.disabled=false;input.disabled=false;}}
 };
 load();
}
