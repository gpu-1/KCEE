import {verifyImportedExport} from './verify-export.js';
import {request} from './client.js';
const get=id=>document.getElementById(id);let revision=0,verified=null,controller=null;
function clear(){revision++;verified=null;controller?.abort();get('check-export-sources').hidden=true;get('export-verification-summary').textContent='';get('export-verification-status').textContent='';}
get('verify-export-file').onchange=clear;
get('verify-export').onclick=async()=>{
 clear();const ticket=revision,file=get('verify-export-file').files[0];if(!file){get('export-verification-status').textContent='Choose an evidence JSON file.';return;}
 get('verify-export').disabled=true;get('export-verification-status').textContent='Checking snapshot and record hashes locally…';
 try{
  if(!file.name.toLowerCase().endsWith('.json')||file.size>16*1024*1024)throw new Error('Choose a JSON export up to 16 MB');
  const data=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer()));const result=await verifyImportedExport(data);if(ticket!==revision)return;verified=result;
  get('export-verification-summary').textContent=result.kind+' · '+result.source_count+' sources · '+result.passage_count+' passages · '+result.note_count+' notes. Snapshot SHA-256: '+result.snapshot_sha256;
  get('export-verification-status').textContent='Snapshot and included record hashes match. This detects changes; it does not prove authorship or check current KCEE sources.';get('check-export-sources').hidden=false;
 }catch(error){if(ticket===revision)get('export-verification-status').textContent='Verification failed: '+error.message;}
 finally{get('verify-export').disabled=false;}
};
get('check-export-sources').onclick=async()=>{
 if(!verified)return;const ticket=revision;controller?.abort();controller=new AbortController();get('check-export-sources').disabled=true;get('export-verification-status').textContent='Comparing included records with stored local originals…';
 try{const result=await request('/knowledge/verify-export-records',{method:'POST',headers:{'Content-Type':'application/json','X-KCEE-Knowledge':'1'},body:JSON.stringify(verified.local_payload),signal:controller.signal});if(ticket!==revision)return;
  if(result.integrity!=='matches_local_records')throw new Error('Local source check did not complete');get('export-verification-status').textContent='Local records match: '+result.sources+' sources, '+result.passages+' passages and '+result.notes+' notes. Historical archived sources are included. This does not verify authorship, retrieval rankings or engineering validity.';
 }catch(error){if(ticket===revision&&error.name!=='AbortError')get('export-verification-status').textContent='Local source check failed or unavailable: '+error.message;}
 finally{get('check-export-sources').disabled=false;}
};
