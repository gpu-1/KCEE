# Backup/restore
Back up code/docs, runs with manifests, model/runtime checksums and material sources. Use `docker compose exec -T postgres pg_dump -U kcee -d kcee > backup.sql` for database backup; encrypt backups containing private engineering data. Test restoration into a separate project/database before migration. Restore SQL using psql and verify run artifact hashes. Never use `docker compose down -v` on valued data without a verified backup.

## Verified single-run bundles

Get the trusted manifest SHA-256 from the database-backed run API before exporting:

```sh
python3 scripts/backup_run.py export runs/<run-id> /path/to/run.zip --manifest-sha256 <trusted-manifest-hash>
python3 scripts/backup_run.py restore /path/to/run.zip /new/location/<run-id> --bundle-sha256 <export-receipt-bundle-hash> --manifest-sha256 <trusted-manifest-hash>
```

Keep both hashes separately from the bundle. Restore requires an existing parent directory and a new destination named with the original run UUID. It rejects existing destinations, unsafe ZIP paths, hash mismatches and unexpected artifacts. It does not modify the database. After restoring into the configured runs root, explicitly register with `python3 -m kcee.registry register /path/to/runs/<run-id>` in the API environment, then verify against the registry.

This preserves one completed run and its original validation status. Failed diagnostics, PostgreSQL, code, materials and model/runtime files need separate backups. Bundles are not encrypted.

## Complete local project bundles

Finish imports and engineering jobs first. From the project root:

```sh
python3 scripts/backup_project.py create /path/to/new/kcee-project.zip
```

The command refuses pending worker requests and active document imports, briefly stops the API, captures a PostgreSQL custom-format dump, verifies saved run manifests and document/passage/vector hashes, packages files, and restarts the API. PostgreSQL must already be running. Avoid manual database or filesystem changes during capture. Files are checked again before the bundle is published. A failed capture leaves the live database intact and restarts the API if it was previously running.

Included: the database schema and data, registered runs and retained diagnostics under `runs/`, refinement files under `.local/studies`, the source snapshot, and available runtime/model checksum manifests. This includes document originals, PDF/OCR extraction records, semantic vectors, model provenance and archive/restore histories. Source snapshots include current source changes; the Git commit identifies the baseline, while per-file hashes identify the actual captured files.

Excluded: `.env`, signing keys and server credentials, Git configuration/credentials, model weights, native executables, transient worker queues and generated speech. These are recreated or provisioned on the destination. Derived container images are not bundled; building/pulling them may require network access to their pinned dependencies. The ZIP and checksum receipt are private files, not encrypted. Keep sensitive engineering backups on encrypted storage. Keep the trusted checksum receipt separately from the bundle.

## Restore on a Mac Studio

Install Docker Desktop and Python on the destination. Copy the bundle and separately retained trusted SHA-256 receipt. Use a **new, nonexistent destination directory** whose parent already exists:

```sh
python3 scripts/backup_project.py restore /path/to/kcee-project.zip /path/to/KCEE-restored --bundle-sha256 <trusted-bundle-sha256>
```

The tool rejects existing destinations, duplicate/unsafe ZIP paths, mismatched file hashes and excessive archive sizes. It creates a unique `kcee-restored-…` Docker project and new database volume; it never restores over an existing project. Fresh database credentials are generated into the restored `.env` with private permissions. The recorded namespace is explicitly selected for restore commands, even if the caller's shell has another Compose project name. Database restore runs in one transaction and retains application grants and append-only triggers.

The restored project root is `<destination>/source`. `restore-report.json` records the isolated project name, verified counts and limitations. Verification checks every registered run against the database manifest, original document bytes, saved extraction/page hashes, passages and stored vector fingerprints. It does not certify OCR recognition quality or execute all old solver jobs. Only PostgreSQL is started; native services and the viewer are left stopped. Restores preserve data and status without granting engineering acceptance.

Provision native PicoGK, local AI/embeddings and Kokoro using the restored host setup guides. Use the source snapshot's pinned model/runtime manifests as references. New credentials and signing keys are local to the destination. Then run:

```sh
cd /path/to/KCEE-restored/source
python3 scripts/start_kcee.py --build --ai --voice
```

Default viewer/API ports remain 5173/8000. Do not start this alongside an existing stack using those ports without deliberate port changes. Destination acceptance must include a new native bracket, solver verification, a PDF/OCR citation check, semantic retrieval and audible voice output on the actual Mac Studio. The local restore rehearsal verifies data portability, not destination hardware performance. The snapshot omits `.git`; reconnect a fresh Git checkout separately if repository updates are needed. Backup creation also supports a restored source snapshot without Git metadata.

A failed restore retains its new destination and isolated database for diagnosis; it does not change the original stack. The initial restore report records the project name before database restoration. Keep the original backup and receipt until destination acceptance passes.

PostgreSQL's [restore documentation](https://www.postgresql.org/docs/18/app-pgrestore.html) describes custom dumps and single-transaction restore. Docker's [project-name documentation](https://docs.docker.com/compose/how-tos/project-name/) explains Compose namespace precedence.
