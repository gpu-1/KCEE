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

## 2026-10-13 — Native viewer generation milestone
- Connected viewer/API creation to native PicoGK through a signed local file queue.
- Added signed worker readiness, job/request identity, hashed STL delivery, bounded queue execution and explicit failure handling.
- Added native/baseline selection and disabled native creation while the worker is unavailable.
- Sixteen unit tests, six viewer client tests and six live API/database/proxy regression tests pass.
- Browser verified native creation, saved provenance, worker shutdown/recovery and explicit baseline selection.
- Worker remains running locally; startup after reboot is explicit. Numerical structural analysis remains pending.

## 2026-10-13 — Structural verification milestone
- Added internal ARM64 CalculiX 2.20 worker and a separate quadratic-solid cantilever benchmark.
- Verified three meshes, analytical displacement agreement, displacement refinement and load/reaction balance.
- Fine displacement 0.287810 mm versus 0.292052 mm reference (1.452%); final refinement change 0.346%.
- Added API/viewer benchmark creation, separate run labels, refinement table and archived solver input/field/log downloads.
- Eighteen unit tests, six viewer client checks and seven live full-stack integration tests pass.
- Browser verified benchmark a491fa36-523a-48be-91f2-651e172a298e and displayed solver-derived results.
- Full FEA of the native PicoGK bracket, converged stress allowables and persistent failed-solver history remain pending.

## 2026-10-13 — Actual native bracket structural study
- Meshed the original four-hole PicoGK STL with Gmsh 4.8.4 and solved three C3D10 refinement levels in CalculiX 2.20.
- Fine mesh: 47,113 nodes / 25,747 elements; loaded-patch displacement approximately 0.780281 mm; final displacement change 0.494%.
- Force balance, load-patch refinement, source-volume agreement (0.288%) and element/midside checks pass.
- Added Analyze selected bracket, separate cantilever benchmark labeling, parent/source hash tracing and retained failure diagnostics.
- Actual viewer analysis 6106f5e9-6ef3-4c2b-8ce4-0775bf1ae2e8 retains parent 8637ec75-588c-4d23-8a36-641efa47ea98 and identical source STL.
- Engineering validation, physical mounting/contact, geometry convergence and converged stress allowables remain pending.

## 2026-10-13 — Bracket inspection controls
- Added wireframe and aspect-aware camera fit for inspecting actual bracket geometry.
- Refinement tables distinguish loaded-patch displacement from cantilever tip displacement and show bracket peak stress with its convergence limitation.
- Benchmark creation now shares the busy state with bracket generation/analysis to prevent overlapping submissions.

## 2026-10-13 — Solver displacement preview
- Added verified fine-mesh archive extraction, original nodal displacement colors and explicit 1×/10×/25× deformation scales.
- Quadratic boundary faces are subdivided using solver midside nodes; preview is a piecewise-linear display, not a new solve.
- Existing immutable runs remain unchanged. Stress-field display and engineering validation remain pending.
