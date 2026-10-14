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
