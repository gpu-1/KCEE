BEGIN;
ALTER TABLE local_document_chunks ADD COLUMN IF NOT EXISTS page_number integer CHECK(page_number>0);
CREATE TABLE IF NOT EXISTS local_pdf_extractions (
 document_id uuid PRIMARY KEY REFERENCES local_documents(id),
 extractor text NOT NULL,
 extraction_sha256 char(64) NOT NULL,
 extraction jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT,INSERT ON local_pdf_extractions TO kcee_app;
DROP TRIGGER IF EXISTS local_pdf_extractions_append_only ON local_pdf_extractions;
CREATE TRIGGER local_pdf_extractions_append_only BEFORE UPDATE OR DELETE OR TRUNCATE ON local_pdf_extractions FOR EACH STATEMENT EXECUTE FUNCTION reject_design_run_mutation();
COMMIT;
