import test from 'node:test';
import assert from 'node:assert/strict';
import {canonicalNoteJson,verifyNoteExport,noteExportText} from '../note-export.js';
import {textHash} from '../search-export.js';
const fixture={"schema": "kcee.page-review-notes.v1", "exported_at": "2026-10-15T01:00:00+00:00", "identity": {"document_id": "12345678-1234-1234-1234-123456789abc", "page_number": 2, "source_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "page_text_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "extractor": "recorded", "name": "gu\u00eda.pdf"}, "notes": [{"document_id": "12345678-1234-1234-1234-123456789abc", "page_number": 2, "source_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "page_text_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "extractor": "recorded", "note": "Revisar precisi\u00f3n: 0.525 W, \u00b0C, s\u00edmbolo \ud83d\udd0e.", "id": 7, "created_at": "2026-10-15T00:00:00+00:00", "note_sha256": "6cfeda37c2e4f40eeeb22b3fb6108b5c2611d31bd1a53b2f7e11a4cba76d2631"}], "note_count": 1, "latest_note_id": 7, "integrity": "verified_at_export", "limitations": ["Saved observations only; not engineering approval."], "snapshot_sha256": "b976a56a428ef320a4accb7e413f20e40e1d2bb3d1adc7d9e30f596887a01605"};
const item={id:fixture.identity.document_id,source_sha256:fixture.identity.source_sha256},page={page_number:2,text_sha256:fixture.identity.page_text_sha256};
test('Python-generated Unicode note and snapshot hashes verify in the browser',async()=>{
 await verifyNoteExport(fixture,item,page);const text=noteExportText(fixture);for(const value of ['guía.pdf','Physical PDF page: 2','Revisar precisión','🔎',fixture.notes[0].note_sha256])assert.ok(text.includes(value));
});
test('snapshot and independent note checks reject changed content and page identity',async()=>{
 const changed=structuredClone(fixture);changed.notes[0].note='Changed';await assert.rejects(verifyNoteExport(changed,item,page),/snapshot hash/);
 delete changed.snapshot_sha256;changed.snapshot_sha256=await textHash(canonicalNoteJson(changed));await assert.rejects(verifyNoteExport(changed,item,page),/note hash/);
 await assert.rejects(verifyNoteExport(fixture,item,{...page,page_number:1}),/identity/);
});
test('verified empty history remains explicit in exported text',async()=>{
 const empty=structuredClone(fixture);empty.notes=[];empty.note_count=0;empty.latest_note_id=null;delete empty.snapshot_sha256;empty.snapshot_sha256=await textHash(canonicalNoteJson(empty));await verifyNoteExport(empty,item,page);assert.ok(noteExportText(empty).includes('No saved notes'));
});
