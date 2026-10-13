# Service contracts and status
| Component | Placement | Status |
|---|---|---|
| API / bracket pipeline | Docker or Python | Implemented screening demo |
| PostgreSQL/pgvector | Docker | Run registry and integrity API implemented; knowledge ingestion pending |
| Three.js | Docker/browser | Saved-run history, verified geometry/results and local STL viewer |
| llama.cpp Metal | macOS | Launcher/layout; adapter pending |
| PicoGK | macOS .NET | Contract/layout; kernel integration pending |
| CalculiX / FEniCSx | Worker containers | Structural/thermal adapter pending |
| SU2 / OpenFOAM | Worker containers | CFD adapter pending |
| Cantera | Worker container | Thermochemistry adapter pending |
| Materials/manufacturing | Engine | Illustrative data/minimum thickness only |
| Kokoro / whisper.cpp | macOS | Contracts/layout; audio integration pending |

Adapters must return status, version, input hashes, units, output hashes and diagnostics. Missing adapters return unavailable, never synthetic success. Worker jobs must be cancellable, resource-limited and have explicit timeouts. Solver containers will be added after ARM64 capability/licensing verification, rather than placeholder images presented as working solvers.
