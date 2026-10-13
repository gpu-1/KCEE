# Implementation log

## 2026-10-13 — Run registry milestone
- Bracket API persists verified run manifests in PostgreSQL before returning success.
- Added paginated history, record retrieval, integrity verification and readiness endpoints.
- Added restricted application role and append-only mutation triggers.
- Added explicit import/recovery for existing and interrupted runs.
- Fixed bracket pipeline when Git is absent in container.
- Locked Python transitive dependencies and API/database base image digests.
- Verified ARM64 API/database build; eight unit tests and four PostgreSQL/API integration tests pass.
- Native AI/PicoGK/voice and numerical solver adapters remain pending; all bracket results remain unvalidated analytical screening.

## 2026-10-13 — Saved-run viewer milestone
- Added paginated run history, bracket creation, verified STL loading, analytical results and provenance.
- Added same-origin API proxy and browser SHA-256 checks on downloaded geometry/results.
- Added cancellation of stale selections and explicit unverified local imports.
- Locked viewer dependencies/image digest; updated Vite to patched 6.4.4.
- Eight Python unit tests, six viewer client tests and five live API/database/proxy integration tests pass.
- Browser verified demo creation, geometry rendering and displayed results; imported the original demo into saved history.
- Local viewer/API/database services are running with private ignored settings.
- All results retain analytical screening limitations; PicoGK/solver adapters remain next work.

## 2026-10-13 — Native geometry milestone
- Implemented real PicoGK 2.3 bracket generation using pinned .NET 9.0.318 on Apple Silicon.
- Added four mounting holes, a fillet-like voxel transition, bounded runtime/resources and explicit failure records.
- Captured native/adapter hashes, kernel settings, geometry request and voxel-derived mass in provenance.
- Removed duplicate-vertex zero-area triangles from voxel mesh export.
- Native checks verify closed oriented meshes, four-hole topology, provenance and plain-bracket volume within 3%.
- Container API still creates the baseline mesh; host-generated native runs are imported for viewing. Solver-backed stress/deflection remain pending.
- Ten unit tests, six viewer client tests, five live API/proxy/database checks and native geometry regressions pass.
- Native run 81c4ade0-895c-4c1d-9399-f838c331e652 was imported and visually checked in the Three.js viewer.
