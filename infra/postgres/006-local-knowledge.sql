BEGIN;
CREATE TABLE IF NOT EXISTS local_documents (
 id uuid PRIMARY KEY,
 name text NOT NULL,
 source_sha256 char(64) UNIQUE NOT NULL,
 original_bytes bytea NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS local_document_chunks (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 document_id uuid NOT NULL REFERENCES local_documents(id),
 line_start integer NOT NULL,
 line_end integer NOT NULL,
 content text NOT NULL,
 chunk_sha256 char(64) NOT NULL,
 embedding_model text,
 embedding vector,
 UNIQUE(document_id,line_start,line_end)
);
CREATE INDEX IF NOT EXISTS local_document_search ON local_document_chunks USING gin(to_tsvector('english',content));
GRANT SELECT,INSERT ON local_documents,local_document_chunks TO kcee_app;
GRANT USAGE,SELECT ON SEQUENCE local_document_chunks_id_seq TO kcee_app;
DROP TRIGGER IF EXISTS local_documents_append_only ON local_documents;
CREATE TRIGGER local_documents_append_only BEFORE UPDATE OR DELETE OR TRUNCATE ON local_documents FOR EACH STATEMENT EXECUTE FUNCTION reject_design_run_mutation();
DROP TRIGGER IF EXISTS local_document_chunks_append_only ON local_document_chunks;
CREATE TRIGGER local_document_chunks_append_only BEFORE UPDATE OR DELETE OR TRUNCATE ON local_document_chunks FOR EACH STATEMENT EXECUTE FUNCTION reject_design_run_mutation();
COMMIT;
