# Structural API

GET /capabilities includes structural.calculix when the internal worker is ready. POST /runs/structural-benchmark solves the fixed cantilever benchmark, verifies acceptance checks, registers its artifacts and returns a run UUID. Failure returns 503. Benchmark runs use kind structural_benchmark and status benchmark_verified_only. Native brackets retain analytical screening.

The internal worker has no host port and accepts only the fixed benchmark. Inputs, raw results and solver hashes are archived. Solver failures are never represented as successful or accepted runs. Full persistent failure history remains pending.
