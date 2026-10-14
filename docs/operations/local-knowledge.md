# Local document knowledge

Open **Local documents**, choose a UTF-8 `.txt` or `.md` file, and press **Add document**. Sources are limited to 256 KB, 5000 lines and 1800 characters per line. Binary, non-UTF-8, empty and unsafe filenames are rejected. Sources stay in PostgreSQL on this host; there is no remote extraction, embedding API or model upload. PDF/OCR and semantic embeddings are not implemented.

Documents are immutable original bytes with SHA-256 identity. Identical bytes deduplicate to the first stored name. New content is a separate source version, even if the filename is the same. Line-preserving passages carry original source and passage hashes. Document/chunk tables permit application SELECT and INSERT only; triggers also reject UPDATE, DELETE and TRUNCATE. This first library has no removal control.

**View verified source** checks original bytes against the stored hash in both the local API and browser before showing plain text. Markdown is shown as text, never executed or rendered as active HTML. Original-source download is plain text with `nosniff` and attachment disposition.

Select a verified structural or thermal study and opt in with **Include local document references**. Search uses ranked PostgreSQL English full-text terms, matching any normalized question term, and returns at most four passages. This is lexical retrieval, not semantic similarity; relevance and claim interpretation require review. Combined context is capped at 20 KB, and full source files are not passed wholesale to the model.

The native model receives study evidence and original excerpts as untrusted data. Document instructions cannot grant tools, change designs, run solvers or approve engineering acceptance. Reference material does not overwrite saved conductivity, allowables or other solver assumptions. Each model-provided document ID must be one of the supplied IDs; unknown IDs and mismatched inline markers are rejected. Inline markers are optional because the structured citation list is displayed below the answer. Exact cited passages, filenames, original line ranges and hashes are shown independently of the generated prose. The original source and all supplied passages are rechecked when retrieving the completed answer.

A valid citation identifies an authentic passage; it does not automatically prove every generated claim follows from that passage or that the document is an authoritative material allowable. Answers remain drafts. JSON exports preserve the question, complete supplied evidence, references, source hashes, model/runtime/prompt fingerprints and settings; TXT exports list the cited filenames and line ranges with source/passage hashes.

For existing databases, apply the repository migration after backing up the database:

```sh
docker exec -i kcee-postgres-1 psql -U kcee -d kcee < infra/postgres/006-local-knowledge.sql
```

Fresh Compose databases apply the numbered initialization scripts automatically. Existing volumes are not reinitialized. Include the PostgreSQL volume in migration/backup planning; document originals are stored in the database, not under `runs/`. Full database backup/restore and destination Mac Studio acceptance remain separate work. The library initially contains the project’s bracket thermal guide uploaded through the website for verification; its stored version remains unchanged if the repository guide later changes.
