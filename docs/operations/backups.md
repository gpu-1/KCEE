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
