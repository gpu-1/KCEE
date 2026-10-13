BEGIN;
CREATE TABLE IF NOT EXISTS run_visibility_events (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id uuid NOT NULL REFERENCES design_runs(id),
  hidden boolean NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT ON run_visibility_events TO kcee_app;
GRANT USAGE, SELECT ON SEQUENCE run_visibility_events_id_seq TO kcee_app;
COMMIT;
