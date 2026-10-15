import {textHash} from './search-export.js';
export async function verificationReport(file, snapshot, local, checkedAt=new Date().toISOString()) {
 const record={schema:'kcee.evidence-verification-report.v1',exported_at:checkedAt,file:{...file},snapshot_check:structuredClone(snapshot),local_source_check:structuredClone(local),limitations:['Hashes detect changes; they do not prove authorship.','Local checks compare included records with originals available at the recorded check time, including archived sources.','This report does not verify retrieval rankings, relevance, OCR accuracy or engineering validity.','This report is a self-consistent record, not a signed attestation.']};
 record.report_sha256=await textHash(JSON.stringify(record));return record;
}
export function verificationReportText(r) {
 return ['KCEE evidence verification report',`Exported: ${r.exported_at}`,`File: ${r.file.name}`,`File bytes: ${r.file.size_bytes}`,`File SHA-256: ${r.file.sha256}`,'','Snapshot check:',JSON.stringify(r.snapshot_check,null,2),'','Local source check:',JSON.stringify(r.local_source_check,null,2),'','Limitations:',...r.limitations.map(s=>'• '+s),'',`Report SHA-256: ${r.report_sha256}`,'Hash scheme: SHA-256 of UTF-8 JSON.stringify report excluding report_sha256.',''].join('\n');
}
