# Structural API

GET /capabilities includes structural.calculix when the internal worker is ready. POST /runs/structural-benchmark solves the fixed cantilever benchmark, verifies acceptance checks, registers its artifacts and returns a run UUID. Failure returns 503. Benchmark runs use kind structural_benchmark and status benchmark_verified_only. Native brackets retain analytical screening.

The internal worker has no host port and accepts only the fixed benchmark. Inputs, raw results and solver hashes are archived. Solver failures are never represented as successful or accepted runs. Full persistent failure history remains pending.

POST /runs/{uuid}/structural verifies the native source run and analyzes the default supported bracket. A cantilever benchmark or unsupported material/geometry returns 422. The analysis is registered as a child design with numerical check status. Worker failures return 503 with a retained diagnostics run ID.

## Recorded refinement investigations

`GET /runs/{run_id}/refinement-explorations` returns bundled investigation records only when their run identity, saved manifest hash and source STL hash match the verified selected bracket study. Other valid bracket studies return an empty list. Unknown runs return 404, unsupported study kinds 422 and saved artifact/source integrity mismatches 409. Report hashes identify the recorded JSON documents. The API hashes each available archive through a read-only host mount and returns `archive_integrity: verified` only when the hash matches the recorded investigation. Missing archives return `not_available`; changed archives cause 409, and unreadable archives cause 503. Only fixed archive identities are accepted; symlinks escaping the experiment directory are rejected. These results are separate from registered studies and engineering acceptance.

`GET /runs/{run_id}/refinement-explorations/{key}/archive` downloads exact hash-checked ZIP bytes for `global-1.3`, `root-0.9` or `root-0.75`. It requires source-linked investigation evidence. The response includes `X-Archive-SHA256`; missing archives return 404 and changed bytes return 409. These are exploratory solver files, not registered or accepted engineering results.

## Local voice summary

`GET /voice/status` reports the native worker heartbeat. `POST /runs/{run_id}/voice` verifies the saved run and reads its voice-summary artifact; local website Origin and `X-KCEE-Voice: 1` are required. It returns a job UUID. `GET /voice/jobs/{job_id}` reports pending/completed/failed and source/audio/model-manifest hashes. `GET /voice/jobs/{job_id}/audio` returns checked WAV bytes only after completion and revalidation of the saved source. Missing/expired jobs return 404; source/audio integrity failures return 409 and unavailable workers/queues 503. No automatic playback is requested.
