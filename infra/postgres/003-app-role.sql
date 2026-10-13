\getenv app_password KCEE_APP_DB_PASSWORD
BEGIN;
SELECT 'CREATE ROLE kcee_app LOGIN' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname='kcee_app') \gexec
SELECT format('ALTER ROLE kcee_app PASSWORD %L', :'app_password') \gexec
REVOKE ALL ON design_runs FROM kcee_app;
GRANT CONNECT ON DATABASE kcee TO kcee_app;
GRANT USAGE ON SCHEMA public TO kcee_app;
GRANT SELECT, INSERT ON design_runs TO kcee_app;
COMMIT;
