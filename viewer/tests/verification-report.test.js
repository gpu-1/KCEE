import test from 'node:test';
import assert from 'node:assert/strict';
import {verificationReport,verificationReportText} from '../verification-report.js';
import {textHash} from '../search-export.js';
test('report binds exact imported file and completed checks without mutating input',async()=>{
 const file={name:'evidence.json',size_bytes:123,sha256:'a'.repeat(64)},snapshot={status:'matches',snapshot_sha256:'b'.repeat(64)},local={status:'not_checked'};
 const report=await verificationReport(file,snapshot,local,'2026-10-15T12:00:00Z');snapshot.status='changed';assert.equal(report.snapshot_check.status,'matches');const {report_sha256,...body}=report;assert.equal(report_sha256,await textHash(JSON.stringify(body)));assert.equal(report.local_source_check.status,'not_checked');assert.match(verificationReportText(report),/not_checked/);assert.match(verificationReportText(report),/not a signed attestation/);
});
test('reports distinguish failed, unavailable and matched checks',async()=>{
 for(const status of ['failed_or_unavailable','matches']){const r=await verificationReport({name:'x.json',sha256:'c'.repeat(64),size_bytes:1},{status:'failed',error:'Hash mismatch'},{status});assert.equal(r.local_source_check.status,status);assert.match(verificationReportText(r),/Hash mismatch/);}
});
