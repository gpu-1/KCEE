import {verifyImportedExport} from './verify-export.js';
import {verificationReport,verificationReportText} from './verification-report.js';
import {request} from './client.js';
const get=id=>document.getElementById(id);let revision=0,verified=null,controller=null,reportState=null,urls=[];
function hideReport(){urls.forEach(URL.revokeObjectURL);urls=[];get('verification-report-downloads').hidden=true;}
async function publishReport(ticket){hideReport();if(!reportState)return;const record=await verificationReport(...reportState);if(ticket!==revision)return;for(const [id,body,type,ext] of [['download-verification-text',verificationReportText(record),'text/plain','txt'],['download-verification-json',JSON.stringify(record,null,2),'application/json','json']]){const url=URL.createObjectURL(new Blob([body],{type}));urls.push(url);get(id).href=url;get(id).download='kcee-verification-'+record.exported_at.replace(/[:.]/g,'-')+'.'+ext;}get('verification-report-downloads').hidden=false;}
function clear(){revision++;verified=null;reportState=null;hideReport();controller?.abort();get('check-export-sources').hidden=true;get('export-verification-summary').textContent='';get('export-verification-status').textContent='';}
get('verify-export-file').onchange=clear;
get('verify-export').onclick=async()=>{
 clear();const ticket=revision,file=get('verify-export-file').files[0];if(!file){get('export-verification-status').textContent='Choose an evidence JSON file.';return;}
 get('verify-export').disabled=true;get('export-verification-status').textContent='Checking snapshot and record hashes locally…';
 try{
  if(!file.name.toLowerCase().endsWith('.json')||file.size>16*1024*1024)throw new Error('Choose a JSON export up to 16 MB');
  const bytes=await file.arrayBuffer();const sha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(ticket!==revision)return;reportState=[{name:file.name,size_bytes:file.size,sha256},{status:'failed',checked_at:new Date().toISOString()},{status:'not_checked'}];const data=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));const result=await verifyImportedExport(data);if(ticket!==revision)return;verified=result;reportState[1]={status:'matches',checked_at:new Date().toISOString(),kind:result.kind,snapshot_sha256:result.snapshot_sha256,sources:result.source_count,passages:result.passage_count,notes:result.note_count};await publishReport(ticket);if(ticket!==revision)return;
  get('export-verification-summary').textContent=result.kind+' · '+result.source_count+' sources · '+result.passage_count+' passages · '+result.note_count+' notes. Snapshot SHA-256: '+result.snapshot_sha256;
  get('export-verification-status').textContent='Snapshot and included record hashes match. This detects changes; it does not prove authorship or check current KCEE sources.';get('check-export-sources').hidden=false;
 }catch(error){if(ticket===revision){get('export-verification-status').textContent='Verification failed: '+error.message;if(reportState){reportState[1]={status:'failed',checked_at:new Date().toISOString(),error:error.message};await publishReport(ticket);}}}
 finally{get('verify-export').disabled=false;}
};
get('check-export-sources').onclick=async()=>{
 if(!verified)return;const ticket=revision;controller?.abort();controller=new AbortController();reportState[2]={status:'checking'};hideReport();get('check-export-sources').disabled=true;get('export-verification-status').textContent='Comparing included records with stored local originals…';
 try{const result=await request('/knowledge/verify-export-records',{method:'POST',headers:{'Content-Type':'application/json','X-KCEE-Knowledge':'1'},body:JSON.stringify(verified.local_payload),signal:controller.signal});if(ticket!==revision)return;
  if(result.integrity!=='matches_local_records')throw new Error('Local source check did not complete');reportState[2]={status:'matches',checked_at:new Date().toISOString(),...result};await publishReport(ticket);if(ticket!==revision)return;get('export-verification-status').textContent='Local records match: '+result.sources+' sources, '+result.passages+' passages and '+result.notes+' notes. Historical archived sources are included. This does not verify authorship, retrieval rankings or engineering validity.';
 }catch(error){if(ticket===revision&&error.name!=='AbortError'){reportState[2]={status:'failed_or_unavailable',checked_at:new Date().toISOString(),error:error.message};await publishReport(ticket);if(ticket===revision)get('export-verification-status').textContent='Local source check failed or unavailable: '+error.message;}}
 finally{get('check-export-sources').disabled=false;}
};
