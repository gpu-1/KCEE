# Native geometry worker

Start with `python3 scripts/start_geometry_worker.py` after PicoGK provisioning. Then run `docker compose --profile viewer up --build -d --wait`. The starter generates a 32-byte signing key and starts a background project-local worker. Key, queue, PID and logs live under ignored .local/geometry/. The worker does not start automatically after reboot; rerun the starter.

The API mounts the local geometry directory and submits HMAC-SHA256 signed jobs. The native worker validates signature, job identity, deadline and allowed request fields. It invokes only the configured PicoGK executable in its own temporary directory. Responses carry matching job/request hashes, metadata and hashed STL bytes, signed with the local key. The API verifies these before writing immutable run artifacts and registering provenance. No native TCP listener, LAN endpoint or remote inference is involved. The container API and local account are trusted key holders; signing does not protect against either being compromised.

A signed heartbeat drives GET /capabilities. The viewer defaults to native PicoGK and disables native creation if the worker is unavailable. The baseline mesh remains an explicit selection. POST /runs/bracket accepts {"geometry_backend":"picogk"} or {"geometry_backend":"mesh"}; omitted input preserves legacy mesh API behavior. Native failures return 503 and do not silently produce baseline geometry. Existing analytical validation limits still apply.

Limits: eight pending/processing jobs, one worker, 120 seconds per kernel subprocess, 135 seconds for queue delivery, 8 MB STL response limit. Queue markers/responses expire after five minutes. Failed or interrupted requests retain failure.json without a completed manifest. A worker crash can leave a processing record; after restarting, affected callers must retry and old processing files can be inspected/removed when no job is active. Signing keys must not be committed, displayed or passed to browser code.

Inspect logs in .local/geometry/worker.log. The PID is stored in .local/geometry/worker.pid. To stop, confirm that PID belongs to this project's `kcee.geometry_worker` process, then send SIGTERM; shutdown finishes the current bounded native job. After restart, Refresh updates viewer availability. On Mac Studio, reprovision the native runtime and generate a new local signing key.

## Start the whole provisioned workspace

Run `python3 scripts/start_kcee.py` from any directory using the script's absolute path if needed. It starts this worker before the Docker containers, then checks geometry/structural availability. Use `--build` after code changes. Readiness reports are retained separately under `.local/readiness/`. This is a manual startup command, not a login agent; it does not start audio or microphone services.

## Website start and stop

The Engineering services panel controls this worker and the structural container together, while retaining the viewer, API and database. Stop asks for confirmation and allows worker requests time to finish. Structural shutdown has a 300-second Docker grace period; longer requests may be terminated at that bound. Native shutdown waits up to 150 seconds without force-killing. Cancel leaves services running.

`start_kcee.py` now also starts an independent supervisor in `scripts/service_supervisor.py`. It receives only signed `start` or `stop` commands, with UUID identity and a 30-second delivery deadline, through `.local/control/queue`. Only fixed project commands are executed. API control writes require a loopback website Origin and a custom header; no cross-origin access is enabled. The API and local account are trusted signing-key holders. The supervisor retains operation logs locally and signed responses for one day. A crash during an operation can leave a processing marker; inspect it before retrying.
