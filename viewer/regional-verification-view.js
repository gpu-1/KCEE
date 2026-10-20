let revision=0,urls=[];
export function verificationMessage(report){
 const messages={matches_reproduced_sources:'Export matches the reproduced local source evidence.',snapshot_differs:'Export differs from the reproduced source evidence.',source_mismatch:'This export belongs to a different saved report. Open its source report before checking.',source_unavailable:'Required source evidence is unavailable on this computer.',source_integrity_failed:'Stored source evidence failed its integrity check.',source_replay_failed:'Stored source evidence could not be reproduced.',not_verified:'Verification did not complete.'};
 return (messages[report.integrity]||messages.not_verified)+(report.mismatched_fields?.length?' Changed fields: '+report.mismatched_fields.join(', ')+'.':'')+(report.source_evidence==='reproduced'&&report.all_source_solver_checks===false?' Some original source checks require attention.':'')+' Engineering acceptance remains pending.';
}
export function reportText(r){return ['Regional export verification','',verificationMessage(r),'','File SHA-256: '+r.file_sha256,'Source report: '+r.selected_report_run_id,'Source evidence: '+r.source_evidence,'Checked at: '+r.checked_at,'','Full verification record:',JSON.stringify(r,null,2)].join('\n');}
export function mountRegionalVerification(verify){
 const $=id=>document.getElementById(id);let pending=false;
 const clear=()=>{revision++;for(const u of urls)URL.revokeObjectURL(u);urls=[];$('regional-verify-export').disabled=false;$('regional-verification-downloads').hidden=true;$('regional-verification-status').textContent='';};clear();$('regional-verify-file').value='';$('regional-verify-export').disabled=false;
 $('regional-verify-file').onchange=clear;
 $('regional-verify-export').onclick=async()=>{
  if(pending)return;clear();const token=revision,file=$('regional-verify-file').files[0];if(!file){$('regional-verification-status').textContent='Choose a regional JSON export.';return;}
  pending=true;$('regional-verify-export').disabled=true;let record=null;
  try{
   if(file.size>2*1024*1024)throw Error('Choose a regional JSON export up to 2 MB');
   const raw=await file.arrayBuffer(),hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),v=>v.toString(16).padStart(2,'0')).join('');if(token!==revision)return;
   record={schema:'native-regional-verification-v1',checked_at:new Date().toISOString(),file_sha256:hash,file_size_bytes:file.size,integrity:'not_verified',source_evidence:'not_checked'};
   $('regional-verification-status').textContent='Reproducing local source evidence and checking the imported snapshot…';
   const response=await verify(raw);if(token!==revision)return;
   if(response.schema!=='native-regional-verification-v1'||response.file_sha256!==hash)throw Error('Verification response does not match the selected file');record=response;
  }catch(e){if(token===revision){if(record)record.error=e.message;else $('regional-verification-status').textContent=e.message;}}
  finally{
   if(token===revision){
    if(record){$('regional-verification-status').textContent=verificationMessage(record)+(record.error?' '+record.error:'');for(const [id,text,type] of [['regional-verification-json',JSON.stringify(record,null,2),'application/json'],['regional-verification-text',reportText(record),'text/plain']]){const u=URL.createObjectURL(new Blob([text],{type}));urls.push(u);$(id).href=u;}$('regional-verification-downloads').hidden=false;}
    $('regional-verify-export').disabled=false;
   }pending=false;
  }
 };
}
