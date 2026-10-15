import {textHash,searchSnapshot,searchText} from './search-export.js';
export async function comparisonSnapshot(comparison){
 if(!Array.isArray(comparison.sources)||comparison.sources.length<2||comparison.sources.length>3||new Set(comparison.sources.map(s=>s.document.id)).size!==comparison.sources.length)throw new Error('Invalid comparison sources');
 for(const source of comparison.sources){
  const {snapshot_sha256,...payload}=source.snapshot;
  if(source.snapshot.question!==comparison.question||snapshot_sha256!==await textHash(JSON.stringify(payload)))throw new Error('Comparison search snapshot mismatch');
  const document=source.document;
  if(source.snapshot.scope?.document_id!==document.id||source.snapshot.scope.name!==document.name||!/^[0-9a-f]{64}$/.test(document.source_sha256)||source.snapshot.passages.some(p=>p.source_sha256!==document.source_sha256))throw new Error('Comparison document identity mismatch');
  await searchSnapshot(comparison.question,{integrity:'verified',passages:source.snapshot.passages,retrieval:source.snapshot.retrieval},document);
 }
 const record={schema:'kcee.reference-comparison.v1',exported_at:new Date().toISOString(),...structuredClone(comparison),integrity:'verified_at_comparison',limitations:['Citations are local to each source: Source 1 [D1] differs from Source 2 [D1].','Independent passage retrieval does not establish agreement or engineering validation.','OCR and relevance require comparison with original documents.','Comparison-time snapshot; later library visibility may differ.']};
 return {...record,snapshot_sha256:await textHash(JSON.stringify(record))};
}
export function comparisonText(record){
 const lines=['KCEE reference comparison — comparison-time snapshot','Question: '+record.question,'Compared: '+record.compared_at,'Exported: '+record.exported_at,'Comparison SHA-256: '+record.snapshot_sha256,'','Limitations',...record.limitations];
 for(const [index,source] of record.sources.entries())lines.push('','================================================','Source '+(index+1)+': '+source.document.name,'Document: '+source.document.id,'Original SHA-256: '+source.document.source_sha256,'Citation prefix: Source '+(index+1),'',searchText(source.snapshot));
 lines.push('','The companion JSON preserves all source snapshots and their individual hashes.','Comparison hash covers JSON.stringify(record) with its top-level snapshot_sha256 omitted.','');return lines.join('\n');
}
