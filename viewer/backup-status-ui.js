import {request} from './client.js';
const get=id=>document.getElementById(id);let pending=false;
async function refresh(){
 if(pending)return;pending=true;get('refresh-backup-status').disabled=true;get('backup-status-records').replaceChildren();get('backup-status-message').textContent='Reading saved backup and restore records…';
 try{const result=await request('/backup-status');const container=get('backup-status-records');
  for(const kind of ['backup','restore']){const record=result[kind],section=document.createElement('section'),heading=document.createElement('h4');heading.textContent=kind==='backup'?'Latest backup receipt':'Latest restore verification';section.append(heading);
   const line=text=>{const p=document.createElement('p');p.textContent=text;section.append(p);};
   if(!record)line('No available record.');else{line('Record updated: '+new Date(record.record_updated_at).toLocaleString());line('Record: '+record.record_name);
    if(kind==='backup'){line('Bundle: '+record.bundle_name);line('Bundle SHA-256: '+record.bundle_sha256);line(record.bundle_present?'Bundle is present. Contents have not been rechecked.':'Bundle is missing from the local backup folder.');}
    else{line('An isolated restore passed its recorded data verification.');line(record.native_setup_required?'Native setup still requires separate checks.':'See the recorded native setup requirements.');}
    line(record.review_notes_verified?'Review-note history verification is recorded.':'Review-note history verification is not recorded.');
    line(Object.entries(record.counts).map(([key,value])=>key.replaceAll('_',' ')+': '+value).join(' · '));}
   container.append(section);}
  get('backup-status-message').textContent='Status read: '+new Date(result.checked_at).toLocaleString()+'. '+result.warnings.join(' ');
 }catch(error){get('backup-status-message').textContent='Backup status unavailable: '+error.message;}
 finally{pending=false;get('refresh-backup-status').disabled=false;}
}
get('refresh-backup-status').onclick=refresh;
window.addEventListener('hashchange',()=>{if(location.hash==='#documents/backup')refresh();});
if(location.hash==='#documents/backup')refresh();
