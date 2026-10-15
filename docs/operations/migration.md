# Mac Studio migration
Stop new runs; copy repository, runs, local models and runtime manifests. Dump/restore PostgreSQL logically (do not copy a live database volume). Install Apple Silicon Docker/native runtimes on the destination, verify hashes and available unified memory, adjust model context/offload and worker concurrency. Keep paths repository-relative; launchers resolve their working root. Run unit tests and the reference bracket and compare artifact hashes excluding timestamps/UUIDs before accepting migration. Preserve historical validation status.

## Read-only destination readiness report

After restoring the repository/runs and database, provisioning the native runtime, starting the native worker and Compose services, run:

```sh
python3 scripts/check_host_readiness.py --reference-run <saved-run-id> --manifest-sha256 <trusted-manifest-hash> --output /path/to/new-readiness-report.json
```

Use the trusted source-host hash, not a newly computed destination hash. The output file must be new. The command checks Apple Silicon macOS, Docker/Compose, native .NET, adapter presence, API/database readiness, native/structural capabilities and the saved reference against both local files and database. It returns exit code 1 on failed checks and records needs_attention. This does not install anything or change services.

A passing report covers the current geometry/FEA stack only. Run fresh native generation, a reference solver reproduction, the saved field check, and a backup/restore round trip on the destination before accepting migration. AI, automatic voice alerts, speech input, thermal, CFD, chemistry and performance require separate acceptance work.

## Optional Kokoro readiness

Add `--voice` to the readiness command after reprovisioning and starting local Kokoro. This checks the worker heartbeat, all model hashes and sizes against its local runtime manifest, and the installed package versions against the pinned lock. `start_kcee.py --voice` includes these checks automatically. The report does not synthesize/play audio and does not certify audible quality; prepare and listen to a reference summary separately on the destination. Model hashes are local recorded trust anchors, not upstream signed checksums.

## Optional local AI readiness

Add `--ai` after provisioning and starting the native study assistant. The preflight checks the model and every recorded runtime file hash, then matches the signed gateway's active model hash with the runtime manifest. `start_kcee.py --ai` includes these checks automatically. This does not certify explanation quality; ask and review reference questions separately on the destination.

## Source transfer checklist and exact restore identity

Documents → Backup → Check transfer readiness compares current document-library and saved-study metadata against the newest backup receipt in `.local/backups`. Study fingerprints bind run identities, manifest hashes, recorded status and visibility history; equal counts alone are insufficient. The latest successful restore is linked by its tested archive SHA-256. A different archive or missing old fingerprint is shown explicitly. The export records the check time and source receipt; refreshing status clears older readiness results.

A source-data pass still leaves two manual steps: export browser-local saved searches separately, and perform native acceptance on Mac Studio. It does not compare current source-code files or rehash the ZIP on each check. The receipt's source commit identifies the included code snapshot.

Migration sequence:

1. Finish current writes, create a fresh bundle using `scripts/backup_project.py create`, and keep its trusted SHA-256 separately.
2. Restore the exact archive into a new isolated destination using `restore --bundle-sha256`. Verify library, review notes, saved studies and run artifacts; retain the restore report. Stop the isolated test database after acceptance.
3. Export saved searches, including labels and page ranges, from Documents → Search. Copy this file separately.
4. Transfer the bundle and trusted hash to Mac Studio. Use a new restore directory; retain the source installation and earlier backups. Restore creates fresh database credentials and an isolated Compose project.
5. Install supported Apple Silicon runtimes and provision local models/native binaries from recorded manifests. Credentials, model weights and native binaries are excluded from the bundle. Reconfigure native launchers for the destination; do not copy source signing keys as a shortcut.
6. Start destination services; run the existing destination readiness command with the trusted source run/manifest, plus `--ai` and `--voice` after provisioning those services. Run fresh native geometry, structural and thermal references, semantic retrieval and page-limited AI citation checks. Prepare and listen to a voice summary. Speech input and other planned solvers require separate checks where implemented.
7. Review numerical/provenance comparisons and performance before accepting the destination. Import saved searches and rerun against restored source identities. Native and hardware acceptance is not inferred from a successful database restore.
