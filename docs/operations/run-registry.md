# Run registry
POST /runs/bracket now verifies artifacts and stores the manifest/hash transactionally in PostgreSQL before returning 201. GET /runs (limit 1–100, offset), GET /runs/{uuid}, and GET /runs/{uuid}/verify provide history, provenance and integrity. /health is liveness; /ready checks database/schema availability. Integrity does not establish engineering validity.

Set separate POSTGRES_PASSWORD and KCEE_APP_DB_PASSWORD in .env. API uses a non-owner role with SELECT/INSERT only. Triggers also reject normal owner UPDATE/DELETE/TRUNCATE. Database administrators can override protections; this is not tamper-proof storage. Keep credentials private and do not share rendered Compose config.

## Existing database volume
Initialization scripts run only on a fresh database. Back up first, add KCEE_APP_DB_PASSWORD to .env and recreate the PostgreSQL container (preserves volume). Apply migrations explicitly:
```sh
docker compose up -d postgres
docker compose exec -T postgres psql -U kcee -d kcee -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/002-append-only.sql
docker compose exec -T postgres psql -U kcee -d kcee -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/003-app-role.sql
docker compose up --build -d api
```
Scripts are idempotent. Startup checks connection/query availability; migration management remains manual.

## Existing local runs and recovery
Files and database cannot share one atomic transaction. Database outage before a run returns 503 without creating artifacts. Registration failure after generation returns 503 with the retained run ID. Recover after database restoration:
```sh
docker compose exec api python -m kcee.registry register /data/runs/RUN_UUID
docker compose exec api python -m kcee.registry verify /data/runs/RUN_UUID
```
Replace RUN_UUID with the actual UUID. This also imports CLI-created runs. Registration validates all required files and is idempotent only for identical records. Altered provenance under the same ID is rejected. UUID directory checks, fixed artifact inventory and symlink rejection prevent unsafe registration. Raw artifact downloads remain available even when integrity fails; use the verify endpoint before consuming results.

## Verification
Unit tests: `python3 -m unittest discover -s tests -v` (standard library only).
Integration: `python3 scripts/check_integration.py` creates a temporary copy, random credentials, an isolated Compose project and separate run files; builds/tests then removes only its own containers/database volume. Requires Docker Desktop and dependency downloads on the first run. Tests cover persistence, tampering, restricted privileges, owner mutation triggers, database outage, retained artifacts and recovery. Never run mutation tests against a valued database. Production native adapters/knowledge ingestion remain pending.

References: [Psycopg transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html), [PostgreSQL triggers](https://www.postgresql.org/docs/18/trigger-definition.html).

## Remove models from the list
Select a model and choose Remove from list, then confirm its displayed identity. Files, manifests and parent/child links remain intact. Show removed models lists hidden entries; select one and confirm Restore to list to bring it back. Visibility changes are stored as separate events, with no edits to run provenance.

Existing databases require `docker compose exec -T postgres psql -U kcee -d kcee -v ON_ERROR_STOP=1 < infra/postgres/004-run-visibility.sql`. New databases apply this schema automatically.
