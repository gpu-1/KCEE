# Reference workflow

1. Open Documents → Search. Choose an active document or all active documents.
2. For a single PDF, optionally enable a physical page range. Keyword and semantic retrieval apply bounds before ranking. The separate result filter only hides returned passages.
3. Save the question and scope. Give it an optional label; filter saved searches by label, question, document or pages. Loading a saved search restores its bounds but does not reuse old evidence.
4. Choose a verified study in Design, return to the reference search, then use the question in the study assistant. The assistant retains single-PDF page bounds; multi-document comparisons use all pages. Scope labels distinguish both.
5. Review the answer and original cited pages. Answers remain drafts; numerical verification is not engineering acceptance. TXT exports show scope; JSON includes complete evidence and the original `evidence_canonical_json` string. SHA-256 of that string's UTF-8 bytes equals `evidence_sha256`, avoiding browser number-format changes.
6. Transfer saved searches using the JSON export/import preview. Schema v3 retains labels and ranges; v1/v2 imports remain supported. Duplicate question/document/page-range searches preserve existing entries and labels. Browser-local saved searches remain outside project backups.

Archived or missing references and invalid PDF page bounds are rejected at retrieval time. No scope automatically falls back to a different document.
