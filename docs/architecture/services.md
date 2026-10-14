# Service contracts and status
| Component | Placement | Status |
|---|---|---|
| API / bracket pipeline | Docker or Python | Implemented screening demo |
| PostgreSQL/pgvector | Docker | Run registry and integrity API implemented; knowledge ingestion pending |
| Three.js | Docker/browser | Saved-run history, verified geometry/results, solver fields, comparisons, exploratory evidence and local STL viewer |
| llama.cpp Metal | macOS | Launcher/layout; adapter pending |
| PicoGK | macOS .NET | Native CLI and signed queue worker connected to API/viewer |
| CalculiX / FEniCSx | Worker containers | CalculiX cantilever and native-STL bracket studies implemented; stress acceptance, FEniCSx and thermal pending |
| SU2 / OpenFOAM | Worker containers | CFD adapter pending |
| Cantera | Worker container | Thermochemistry adapter pending |
| Materials/manufacturing | Engine | Illustrative data/minimum thickness only |
| Kokoro / whisper.cpp | macOS | Native Kokoro manual playback, verification, exports and website controls implemented; automatic alerts and whisper input pending |

Adapters must return status, version, input hashes, units, output hashes and diagnostics. Missing adapters return unavailable, never synthetic success. Implemented workers have explicit resource/time bounds and graceful shutdown. Per-job inference/solver cancellation remains pending. Solver containers will be added after ARM64 capability/licensing verification, rather than placeholder images presented as working solvers.

Structural benchmark: optional fea profile, CalculiX 2.20 worker on ARM64 Debian, internal-only. Viewer/API can request and register fixed cantilever verification runs. Native-STL volume meshing and actual bracket FEA are implemented. Global/local-root refinement investigations remain exploratory and do not establish stress convergence or engineering acceptance.
