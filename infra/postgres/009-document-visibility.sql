BEGIN;
CREATE TABLE IF NOT EXISTS document_visibility_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 document_id uuid NOT NULL REFERENCES local_documents(id),
 archived boolean NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS document_visibility_latest ON document_visibility_events(document_id,id DESC);
GRANT SELECT,INSERT ON document_visibility_events TO kcee_app;
GRANT USAGE,SELECT ON SEQUENCE document_visibility_events_id_seq TO kcee_app;
DROP TRIGGER IF EXISTS document_visibility_append_only ON document_visibility_events;
CREATE TRIGGER document_visibility_append_only BEFORE UPDATE OR DELETE OR TRUNCATE ON document_visibility_events FOR EACH STATEMENT EXECUTE FUNCTION reject_design_run_mutation();
CREATE OR REPLACE VIEW active_local_documents AS SELECT d.* FROM local_documents d WHERE NOT COALESCE((SELECT e.archived FROM document_visibility_events e WHERE e.document_id=d.id ORDER BY e.id DESC LIMIT 1),false);
GRANT SELECT ON active_local_documents TO kcee_app;
COMMIT;
