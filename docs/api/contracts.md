# API
Implemented: GET /health (liveness), GET /ready (database readiness), GET /runs (paginated history), GET /runs/{uuid}, GET /runs/{uuid}/verify (integrity), POST /runs/bracket (fixed sample requirements, no user parameters yet), GET /artifacts/{run-id}/{filename}. FastAPI serves interactive OpenAPI at /docs. Runs execute synchronously in a thread; job queue/authentication pending. Bind API to localhost.

Planned native gateway: POST /geometry/bracket; POST /ai/propose; POST /voice/speak, /voice/alert, /voice/summary; GET /voice/status; POST /speech/transcribe. Requests carry schema_version, run_id and SI-unit inputs. Voice policy: DEBUG never, INFO opt-in, RESULT concise, WARNING spoken, CRITICAL priority/interruption. User mute and bounded queue required. Microphone recording requires explicit user activation.

GET /capabilities reports native-worker availability from a signed local heartbeat. POST /runs/bracket accepts optional geometry_backend (mesh or picogk); default mesh preserves compatibility. Native errors return 503 without fallback or successful registration.

## CFD channel verification

`GET /capabilities` includes `cfd.plane_poiseuille`. `POST /runs/cfd-benchmark` uses the fixed SI preset and accepts no parameters (empty body or `{}`). A successful response returns the immutable `run_id` and `cfd_numerical_checks_passed_not_engineering_validated` status. Unavailable worker/reproduction failure returns 503; input parameters return 422. Registered artifacts include `result.json`, `cfd.json`, `velocity.csv`, `report.md`, requirements, the display STL and a voice-summary provenance artifact. `/runs/{id}/verify` verifies the exact CFD inventory and hashes. This kind is excluded from bracket analysis, coupled comparisons and the current study-assistant scope.
