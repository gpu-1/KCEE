# Service contracts and status
| Component | Placement | Status |
|---|---|---|
| API / bracket pipeline | Docker or Python | Implemented screening demo |
| PostgreSQL/pgvector | Docker | Run registry and integrity API implemented; knowledge ingestion pending |
| Three.js | Docker/browser | Saved-run history, verified geometry/results and local STL viewer |
| llama.cpp Metal | macOS | Launcher/layout; adapter pending |
| PicoGK | macOS .NET | Native CLI and signed queue worker connected to API/viewer |
| CalculiX / FEniCSx | Worker containers | CalculiX benchmark implemented; bracket/FEniCSx/thermal adapters pending |
| SU2 / OpenFOAM | Worker containers | CFD adapter pending |
| Cantera | Worker container | Thermochemistry adapter pending |
| Materials/manufacturing | Engine | Illustrative data/minimum thickness only |
| Kokoro / whisper.cpp | macOS | Contracts/layout; audio integration pending |

Adapters must return status, version, input hashes, units, output hashes and diagnostics. Missing adapters return unavailable, never synthetic success. Worker jobs must be cancellable, resource-limited and have explicit timeouts. Solver containers will be added after ARM64 capability/licensing verification, rather than placeholder images presented as working solvers.

Structural benchmark: optional fea profile, CalculiX 2.20 worker on ARM64 Debian, internal-only. Viewer/API can request and register fixed cantilever verification runs. Bracket volume meshing/actual bracket FEA remains pending.
