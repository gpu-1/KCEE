# Local document knowledge

Open **Local documents**, choose a UTF-8 `.txt` or `.md` file, and press **Add document**. Sources are limited to 256 KB, 5000 lines and 1800 characters per line. Binary, non-UTF-8, empty and unsafe filenames are rejected. Sources stay in PostgreSQL on this host; there is no remote extraction, embedding API or model upload. Text PDF import is supported locally; OCR is not implemented. Semantic embeddings run locally on Metal.

Documents are immutable original bytes with SHA-256 identity. Identical bytes deduplicate to the first stored name. New content is a separate source version, even if the filename is the same. Line-preserving passages carry original source and passage hashes. Document/chunk tables permit application SELECT and INSERT only; triggers also reject UPDATE, DELETE and TRUNCATE. This first library has no removal control.

**View verified source** checks original bytes against the stored hash in both the local API and browser before showing plain text. Markdown is shown as text, never executed or rendered as active HTML. Original-source download is plain text with `nosniff` and attachment disposition.

Select a verified structural or thermal study and opt in with **Include local document references**. Search uses ranked PostgreSQL English full-text terms, matching any normalized question term, and returns at most four passages. When indexed, results combine semantic similarity and keyword rankings; relevance and claim interpretation require review. Combined context is capped at 20 KB, and full source files are not passed wholesale to the model.

The native model receives study evidence and original excerpts as untrusted data. Document instructions cannot grant tools, change designs, run solvers or approve engineering acceptance. Reference material does not overwrite saved conductivity, allowables or other solver assumptions. Each model-provided document ID must be one of the supplied IDs; unknown IDs and mismatched inline markers are rejected. Inline markers are optional because the structured citation list is displayed below the answer. Exact cited passages, filenames, original line ranges and hashes are shown independently of the generated prose. The original source and all supplied passages are rechecked when retrieving the completed answer.

A valid citation identifies an authentic passage; it does not automatically prove every generated claim follows from that passage or that the document is an authoritative material allowable. Answers remain drafts. JSON exports preserve the question, complete supplied evidence, references, source hashes, model/runtime/prompt fingerprints and settings; TXT exports list the cited filenames and line ranges with source/passage hashes.

For existing databases, apply the repository migration after backing up the database:

```sh
docker exec -i kcee-postgres-1 psql -U kcee -d kcee < infra/postgres/006-local-knowledge.sql
```

Fresh Compose databases apply the numbered initialization scripts automatically. Existing volumes are not reinitialized. Include the PostgreSQL volume in migration/backup planning; document originals are stored in the database, not under `runs/`. Full database backup/restore and destination Mac Studio acceptance remain separate work. The library initially contains the project’s bracket thermal guide uploaded through the website for verification; its stored version remains unchanged if the repository guide later changes.

## Local semantic search

Start Local AI, open Local documents, and press **Index documents** after adding sources. Indexing resumes missing passages in batches of at most 16. Stop Local AI stops both chat and embeddings; keyword retrieval remains available. The website and original documents remain available.

Provision once with `python3 scripts/provision_embeddings.py`. This explicitly downloads the official [Nomic Embed v1.5 GGUF](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF) F16 model at revision `0188c9bf409793f810680a5a431e7b899c46104c`, SHA-256 `f7af6f66802f4df86eda10fe9bbcfc75c39562bed48ef6ace719a251cf1c2fdb`. Inference uses the pinned llama.cpp runtime, Metal, mean pooling, 2048-token context, task-specific query/document prefixes, and 768 normalized dimensions. Model weights and private HTTP credentials are not mounted into the API container. A signed local queue carries bounded requests.

Apply `infra/postgres/007-local-embeddings.sql` to existing databases after the original knowledge migration, using the same migration procedure above. Fresh databases initialize both automatically. Derived vectors are append-only and versioned by the full model/runtime manifest; indexing a new model never overwrites source bytes or previous vectors. Each vector has input, source, passage, model and vector hashes. Retrieval verifies these before supplying literal passages to the assistant. JSON answer exports retain retrieval fingerprints and ranking metadata.

Exact pgvector cosine scans suit this initial small library. Candidates below cosine 0.5 are excluded from the semantic ranking; reciprocal rank fusion uses constant 60 and returns at most four passages. These settings were smoke-tested on the project guide, not certified as a relevance benchmark. Missing, stopped or busy embedding services fall back to keywords, recorded in retrieval metadata. Integrity failures reject retrieval. No remote inference or automatic downloads occur during a question.

## PDF import and page citations

Choose a `.pdf` in Local documents and press Add document. The original PDF bytes remain immutable in PostgreSQL, with their own SHA-256. PDFs are limited to 5 MB, 40 physical pages, 512 KB extracted text in total and 256 KB per page; extracted lines must fit the existing 1800-character passage limit. Encrypted, malformed and entirely image-only PDFs are rejected. Mixed documents preserve physical page numbering and report pages without text. Blank pages are not indexed. OCR, tables as structured data, diagrams and visual interpretation are separate work.

Extraction uses pinned `pypdf==6.19.0`, plain text mode, in a separate process with a 15-second wall limit, 10-second CPU limit and 512 MB Linux address-space limit. PDF actions and embedded scripts are not executed. Source downloads use attachment disposition and `nosniff`. View extracted pages verifies the original bytes and shows plain text, never active PDF content. The [pypdf extraction guide](https://github.com/py-pdf/pypdf/blob/main/docs/user/extract-text.md) explains why reading order and table layout may differ from the visible page. Review the original before treating extracted text as authoritative.

Apply `infra/postgres/008-pdf-knowledge.sql` after migrations 006 and 007 on existing volumes. The additive migration creates append-only extraction records and adds nullable page numbers to passages; existing text sources and vectors remain intact. Extraction records preserve parser identity, each page text hash, physical page count and a canonical extraction hash. Retrieval and completed-answer citation verification re-extract the original using the pinned parser and reject changed extraction text, incorrect page ranges or source hashes.

PDF passages never cross pages. Assistant citation cards and TXT exports show page numbers; JSON records include the literal excerpt, physical page number, parser identity, page text hash, source hash and passage hash. These citations identify authenticated text extraction, not proof that every generated claim follows from it. Index new PDF passages using Index documents to enable semantic retrieval.
