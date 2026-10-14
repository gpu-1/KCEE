BEGIN;
CREATE TABLE IF NOT EXISTS local_chunk_embeddings (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 chunk_id bigint NOT NULL REFERENCES local_document_chunks(id),
 source_sha256 char(64) NOT NULL,
 chunk_sha256 char(64) NOT NULL,
 model_sha256 char(64) NOT NULL,
 model_manifest_sha256 char(64) NOT NULL,
 input_sha256 char(64) NOT NULL,
 vector_sha256 char(64) NOT NULL,
 embedding vector(768) NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(chunk_id,model_manifest_sha256)
);
CREATE INDEX IF NOT EXISTS local_embedding_model ON local_chunk_embeddings(model_manifest_sha256,chunk_id);
GRANT SELECT,INSERT ON local_chunk_embeddings TO kcee_app;
GRANT USAGE,SELECT ON SEQUENCE local_chunk_embeddings_id_seq TO kcee_app;
DROP TRIGGER IF EXISTS local_embeddings_append_only ON local_chunk_embeddings;
CREATE TRIGGER local_embeddings_append_only BEFORE UPDATE OR DELETE OR TRUNCATE ON local_chunk_embeddings FOR EACH STATEMENT EXECUTE FUNCTION reject_design_run_mutation();
COMMIT;
