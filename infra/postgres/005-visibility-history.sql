BEGIN;
CREATE OR REPLACE FUNCTION reject_visibility_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'Visibility history is append-only; add a new visibility event';
END;
$$;
DROP TRIGGER IF EXISTS visibility_append_only ON run_visibility_events;
CREATE TRIGGER visibility_append_only BEFORE UPDATE OR DELETE OR TRUNCATE
ON run_visibility_events FOR EACH STATEMENT EXECUTE FUNCTION reject_visibility_mutation();
COMMIT;
