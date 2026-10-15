BEGIN;
CREATE TABLE IF NOT EXISTS document_page_notes (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 document_id uuid NOT NULL REFERENCES local_documents(id),
 page_number integer NOT NULL CHECK(page_number BETWEEN 1 AND 300),
 source_sha256 text NOT NULL CHECK(length(source_sha256)=64),
 page_text_sha256 text NOT NULL CHECK(length(page_text_sha256)=64),
 extractor text NOT NULL,
 note text NOT NULL CHECK(length(note) BETWEEN 1 AND 2000),
 note_sha256 text NOT NULL CHECK(length(note_sha256)=64),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS document_page_notes_history ON document_page_notes(document_id,page_number,id DESC);
GRANT SELECT,INSERT ON document_page_notes TO kcee_app;
GRANT USAGE,SELECT ON SEQUENCE document_page_notes_id_seq TO kcee_app;
DROP TRIGGER IF EXISTS document_page_notes_append_only ON document_page_notes;
CREATE TRIGGER document_page_notes_append_only BEFORE UPDATE OR DELETE OR TRUNCATE ON document_page_notes FOR EACH STATEMENT EXECUTE FUNCTION reject_design_run_mutation();
COMMIT;
