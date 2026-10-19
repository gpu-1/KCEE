# CFD jobs: progress, cancellation and retry

The website starts long bracket-flow and OpenFOAM vortex studies as background
jobs. The **CFD jobs** panel shows recent studies, the current phase/case,
solver progress, Cancel, Retry, Open result and links to saved cases. Refreshing
the website reconnects to server-side state. Existing numerical recipes,
verification gates and immutable run artifacts remain unchanged.

Progress is **per current case**, not an overall study percentage or ETA.
Bracket solves report SIMPLE iterations out of 1,500; vortex cases report
simulated time in seconds out of 0.5. Source verification, meshing,
postprocessing and raw-evidence verification have stage labels. A full current
case bar can be followed by another case or verification work.

## Cancellation and saved evidence

Cancellation sets an API event and relays the same job UUID to the CFD worker.
Fixed solver commands run in isolated process groups. The worker terminates the
whole command group, waits, and escalates to a kill if termination does not
finish. CPU-bound Python verification/postprocessing stops at cooperative stage
boundaries, so Cancel may remain **Stopping at a safe stage** briefly.

Already registered source cases and reports remain available. New registered
and successfully reverified reused cases are listed on the job. Bracket worker
execution failures/cancellation retain bounded partial solver archives and a
failure record when the worker returns them. A partially executed vortex
benchmark is not a registered valid study. Cancellation does not manufacture a
completed result from partial fields. If registration finishes before a late
cancel request, completion wins and the valid result remains available.

Retry is available for failed, cancelled and interrupted jobs. It creates a
new UUID linked by `retry_of`, preserving the original job and recipe. Mesh,
domain, local, reference and joint workflows reuse compatible source cases only
after raw re-verification. Missing cases run normally. A standalone flow or
vortex retry starts that standalone study again; it does not resume arbitrary
solver files or change iteration settings.

## Persistence and recovery

Job records are atomic JSON replacements in `.local/cfd-jobs/`, mounted at
`/data/cfd-jobs`. This operational history is separate from immutable `runs/`
artifacts and the append-only PostgreSQL registry. The panel shows the latest
20 jobs; the manager retains up to 100 loaded records and refuses further starts
when full. Older record files may be moved to an operator archive before API
restart; no study artifacts need to be deleted. Existing Mac Studio engineering
backups remain authoritative for registered studies; this operational job
history is not added to those backups by this change.

An API restart marks formerly active records **interrupted** and attempts to
cancel their worker job, with bounded retries. It does not automatically launch
more computation. Retry is explicit. Worker progress is ephemeral; recorded
terminal state, recipe, lineage, completed-run IDs and result survive restart.
The supported deployment uses one API process and one CFD worker. This is not a
multi-replica scheduler. Legacy synchronous API routes remain compatible and
share the worker's existing exclusivity lock. Fast channel benchmarks retain
their existing immediate workflow.

## API

- `POST /cfd-jobs`: `{kind, parent_id, options}`; returns 202 with a job UUID.
- `GET /cfd-jobs`: recent durable records.
- `GET /cfd-jobs/{id}`: state plus bounded live worker progress while active.
- `POST /cfd-jobs/{id}/cancel`: request cancellation; terminal jobs are unchanged.
- `POST /cfd-jobs/{id}/retry`: create a new linked job; active/completed jobs cannot retry.

Kinds: `flow`, `refinement`, `domains`, `combined`, `local`, `reference`, `joint`,
`vortex` and `forces`. All except vortex require a native parent design; `forces` also accepts a saved bracket-flow case. Only `flow`
accepts the existing bounded flow options; other kinds use fixed recipes.
Invalid inputs are rejected before background work. One managed job runs at a
time. No remote credentials, source documents, arbitrary commands or paths are
accepted by this interface. Job status does not establish engineering accuracy.

## Recorded verification — 19 October 2026

The deployed website started and completed vortex job `18bd0f51`, cancelled
`2e619c90`, then retried cancelled job `faab8599` as `a4604bcd`. The retry
completed after a browser reload and registered result
`3fde0a9c-e985-4eee-8865-67d9f73c4e7a` with verified artifacts.
Cancellation was also observed after a real solver iteration and during bracket
meshing (`3e39e285`); the latter retained failure `94fb9e21` with mesh and job
logs. Restarting the API during bracket job `ef357376` retained its recipe,
marked it interrupted and stopped the worker. The website showed Retry enabled.

The local verification receipt, screenshots and test logs are in
`.local/verification/cfd-jobs/`. Six durable job records matched the API after
restart. All eight manifest digests from the preceding fine outer-domain study
were independently verified unchanged. Automated validation covers 231 backend,
85 viewer and 31 isolated integration tests, including cancellation followed by
a new retry and verified result registration.

Wall-load jobs use verified saved fields without starting OpenFOAM. They report source verification and current-case wall-face progress. Their cancellation is cooperative at source/case and wall-face batch boundaries. See [force estimates](../engineering/bracket-flow-forces.md).
