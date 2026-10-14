# Structural API

GET /capabilities includes structural.calculix when the internal worker is ready. POST /runs/structural-benchmark solves the fixed cantilever benchmark, verifies acceptance checks, registers its artifacts and returns a run UUID. Failure returns 503. Benchmark runs use kind structural_benchmark and status benchmark_verified_only. Native brackets retain analytical screening.

The internal worker has no host port and accepts only the fixed benchmark. Inputs, raw results and solver hashes are archived. Solver failures are never represented as successful or accepted runs. Full persistent failure history remains pending.

POST /runs/{uuid}/structural verifies the native source run and analyzes the default supported bracket. A cantilever benchmark or unsupported material/geometry returns 422. The analysis is registered as a child design with numerical check status. Worker failures return 503 with a retained diagnostics run ID.

## Recorded refinement investigations

`GET /runs/{run_id}/refinement-explorations` returns bundled investigation records only when their run identity, saved manifest hash and source STL hash match the verified selected bracket study. Other valid bracket studies return an empty list. Unknown runs return 404, unsupported study kinds 422 and saved artifact/source integrity mismatches 409. Report hashes identify the recorded JSON documents. Experiment archive hashes are retained evidence; this endpoint does not load or reverify the host's exploratory archives. These results are separate from registered studies and engineering acceptance.
