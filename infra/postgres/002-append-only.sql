BEGIN;
CREATE OR REPLACE FUNCTION reject_design_run_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'design_runs is append-only; create a new design record';
END;
$$;
DROP TRIGGER IF EXISTS design_runs_append_only ON design_runs;
CREATE TRIGGER design_runs_append_only BEFORE UPDATE OR DELETE OR TRUNCATE
ON design_runs FOR EACH STATEMENT EXECUTE FUNCTION reject_design_run_mutation();
COMMIT;
