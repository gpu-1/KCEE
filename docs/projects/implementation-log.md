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

## 2026-10-13 — Separate stress/displacement colors
- Added von Mises colors from archived CalculiX averaged nodal stress tensors, distinct from integration-point peak stresses.
- Explicit quantity selector, MPa/mm legends, unconverged stress label and undeformed option clarify interpretation.

## 2026-10-13 — Load/support interpretation
- Added optional nominal rear clamp outline and free-end load strip/arrows for supported bracket studies.
- Markers use original model coordinates and remain on the undeformed reference during exaggerated deformation. Labels distinguish total 100 N load, nominal patch edges and ideal clamp from bolt contact.

## 2026-10-13 — Visible numerical checks
- Viewer exposes recorded force balance, displacement/load-patch refinement and source-volume checks with measured percentages.
- Peak stress change is informational and does not claim established stress convergence or engineering validation.

## 2026-10-13 — Field extraction verification
- Verified von Mises conversion against uniaxial, hydrostatic and pure-shear stress tensors.
- Reject incomplete stress fields, invalid C3D10 node references and non-manifold volume faces.
- All 26 unit tests pass; archived bracket remains 49,384 preview triangles with unchanged stress/displacement values.

## 2026-10-13 — Shared-face and orientation verification
- Reject non-positive tetrahedron volume, inconsistent shared midside nodes and shared-face orientation.
- Reference tests verify removal of an internal face between two quadratic tetrahedra and outward surface triangle normals.
- All 30 unit tests pass; actual bracket surface and field values remain unchanged.

## 2026-10-13 — Archive-to-preview acceptance check
- Added repeatable read-only verification of saved bracket fields against their SHA-256-verified solver archive.
- Verified run 6106f5e9: 24,686 surface nodes, 49,384 triangles, closed/oriented edges and 9,821.594885 mm³ volume matching the fine solver mesh.
- Geometry/displacement vectors match exactly; derived magnitudes agree within 1e-12 rounding tolerance. Engineering validation remains pending.

## 2026-10-13 — Verified run backup/restore
- Added exclusive single-run bundle export and checked restoration into new UUID directories.
- Tested actual bracket byte-identical round trip plus overwrite rejection; unit tests cover unsafe paths and hash failures.
- Database registration remains explicit; this does not claim complete project migration.

## 2026-10-13 — Backup snapshot verification
- Export verifies the exact in-memory bytes written to the bundle against the trusted manifest.
- Restore parses the same in-memory bundle bytes whose checksum was verified.
- Added run-change-during-export and altered-artifact restore tests; all 35 unit tests pass. Actual bracket round trip remains byte-identical.

## 2026-10-13 — Confirmed model removal
- Added confirmation dialog identifying the selected run before hiding it from the saved list.
- Show removed models and confirmed Restore to list provide reversible recovery.
- Separate append-only visibility events retain immutable run files/provenance and parent relationships. Existing database migration applied locally.
- Browser cancellation verified; isolated API checks cover confirmation mismatch, hide/restore and unchanged manifest.

## 2026-10-13 — Removal flow and history protection
- Disable removal during active job creation and prevent dismissing a pending visibility save.
- Add append-only triggers for visibility events and integration tests for application/owner mutation rejection.

## 2026-10-13 — Native geometry refinement study
- Generated default four-hole bracket at 0.75/0.5/0.35 mm voxels with verified manifests and closed-mesh/topology checks.
- Last voxel volume change 0.5105%, STL surface volume change 0.1468%; no repeated FEA or stress convergence claim.
- Stored reproducible study summary and command; original study artifacts remain under .local/studies.

## 2026-10-13 — Local bore geometry measurements
- Measured four mid-thickness bore sections across the recorded voxel refinement study.
- Radial envelopes approach nominal 5 mm; fine resolution spans approximately 4.969–4.999 mm.
- Verified measurement against known square-prism radial bounds; no manufacturing acceptance or stress convergence claim.

## 2026-10-13 — Through-thickness bore profiles
- Extended verified bore measurements to quarter/mid/three-quarter plate sections.
- Found coarse-resolution radial envelope widening to approximately 5.255 mm; finer studies remain near nominal.
- Reject unsupported geometry and invalid section depths; all 36 unit tests pass.

## 2026-10-13 — Selected-run geometry measurements
- Added verified native-run API and viewer panel for four bore envelopes at three depths.
- Verified live/local measurements within 1e-12 rounding tolerance and non-native run rejection. Browser verified actual bracket; six viewer checks/build passed.

## 2026-10-13 — Portable host readiness report
- Added read-only host, runtime/service and optional trusted saved-run readiness checks with JSON output.
- All eight checks pass on the current Mac; unavailable API correctly reports needs_attention and nonzero exit.
- Destination reproduction and unimplemented subsystem acceptance remain pending.

## 2026-10-13 — Current workflow documentation
- Updated README, bracket/viewer walkthroughs and install guidance to match implemented native FEA, colors, bore measurements, reversible removal and recovery/readiness checks.
- Removed obsolete pending-adapter statements while retaining actual engineering limitations.

## 2026-10-13 — Finer geometry FEA investigation
- Attempted the 0.35 mm native bracket under existing study conditions; Gmsh rejected surface parameterization.
- Smaller-angle probe passed parametrization but volume meshing rejected overlapping facets; retained failure archives and recorded evidence.
- Restored production adapter settings. Existing results unchanged; geometry-dependent structural convergence remains unresolved. All 36 unit tests pass.

## 2026-10-13 — Completed finer native bracket FEA
- Explicit 30° classification with local 1 mm load-strip refinement resolves the unmodified 0.35 mm STL; original 0.5 mm path remains at 20°.
- Run edac2bbf passes numerical and archive-field checks: displacement 0.783595 mm, peak stress 257.407 MPa.
- Load-patch area and meshing differ; no isolated geometry-sensitivity or stress acceptance claim. All 36 unit tests pass.

## 2026-10-13 — Stress hotspot diagnostics
- Located archived integration-point peaks and their element corner centroids/quality for both bracket studies.
- Finer peak is near lower rear clamp edge; baseline contains poor corner elements elsewhere. No causal or convergence claim.
- Verified mean-ratio metric against an equilateral tetrahedron, scaling and inverted-element rejection; all 38 tests pass.

## 2026-10-13 — Viewer stress diagnostics
- Added archive-verified hotspot centroid and corner mesh-quality panel.
- Verified finer run against archived report and unsupported benchmark rejection; browser verified actual values. Six viewer checks/build pass.

## 2026-10-13 — Saved study comparison
- Added verified reference pinning and side-by-side geometry/mesh/load/result comparison.
- Browser verified original vs finer bracket values and +0.425% loaded displacement change; no stress acceptance claim.

## 2026-10-13 — Comparison export
- Added JSON comparison export with independent manifest/STL/archive hashes and full-precision values.
- Seven viewer checks pass, including identity/provenance rejection and serialized value preservation.
- Link and filename verified in browser; in-app download event did not complete, so download completion remains unverified.

## 2026-10-13 — Comparison copy fallback
- Added read-only inline JSON receipt and Select all JSON for browsers without working downloads.
- Browser verified all 2,226 receipt characters selected and correct reference identity; seven viewer checks/build pass.

## 2026-10-13 — Complete stress diagnostic data checks
- Require four unique, finite integration-point stress records per C3D10 element. Reject invalid IDs and non-finite geometry.
- Both archived and live bracket diagnostics pass with unchanged peak values; all 41 unit tests pass.

## 2026-10-13 — Retained failure workspace view
- Added read-only discovery and viewer dialog for retained failure records and solver diagnostic archives.
- Browser verified five failures from the finer-geometry investigation; clear distinction from verified successes.
- Tests reject mismatched identities, malformed/non-object records and symlinked diagnostic archives.

## 2026-10-13 — Failure reason previews
- Added bounded job-log classification into readable failure reasons with generic fallback.
- Oversized, missing and corrupt logs cannot produce unrestricted previews. Browser verified reasons from existing failures. All 43 unit tests pass.

## 2026-10-13 — Failed-analysis parent navigation
- Added Open parent design actions; parent models pass normal provenance checks before display.
- Cancel pending failure-list requests when closing/reopening the dialog.
- Browser verified finer bracket parent 15802ef9 and Artifacts verified status; seven viewer checks/build pass.

## 2026-10-13 — Clipped quadratic-face traction
- Replace centroid-selected whole-face loading with clipped strip integration preserving force and first moment.
- Verify analytical full/partial-face area and moment tests; all 46 unit tests pass.
- Two new real bracket studies pass numerical and field checks; last patch-area changes 0.0003406%/0.582955%. Different resolved top surfaces and unconverged stress remain limitations.

## 2026-10-13 — Source load-strip discrepancy identified
- Original STL patch comparison reveals baseline 0.00256% vs finer 15.3773% mesh-area error.
- Added future 5% source-area gate and retrospective viewer warning without modifying saved manifests.
- Previous numerical passes were limited to their recorded checks; finer geometry requires further meshing investigation.

## 2026-10-13 — Load-surface tolerance investigation
- Added repeatable read-only source/preview area sweep at four top-face tolerances.
- Finer mesh selection is sensitive at 0.05–0.1 mm; larger masks include more curved source geometry.
- Preserved production mask/gate; documented preview subdivision limitations and unresolved surface representation.

## 2026-10-13 — Planar top-patch partition probe
- Verified original finer STL and inspected classified entities at 20°/30° without modifying geometry.
- Neither isolates a wholly planar top entity; 30° top candidates span up to 3.5033 mm in z. Whole-patch planar projection would be unjustified.
- Added reproducible probe and evidence; production settings/source-area warnings remain unchanged.

## 2026-10-13 — Improved finer-STL meshing classification
- Compared 25°/35°/45° fine meshes without source changes; 25° has lowest source-patch area discrepancy (3.038%).
- Full 25° study c072e470 passes all five numerical gates and field verification; displacement 0.790682 mm, unconverged stress 217.242 MPa.
- New finer jobs use traced 25° setting; baseline remains unchanged. Old warnings and immutable artifacts preserved; 47 unit tests pass.

## 2026-10-13 — Regional stress diagnostics
- Added centroid-distance exclusion sweeps around nominal clamp/load rectangles, retaining unfiltered global peaks.
- New finer study regional peak 88.049 MPa vs global 217.242 MPa; no allowable/convergence claim.
- Browser verified measured values and limits; all 48 unit tests and seven viewer checks pass.

## 2026-10-13 — Archived regional stress refinement
- Measured regional peaks across all three meshes: final changes 0.5512% baseline and 14.4957% finer.
- Viewer verified informational labels; all 49 unit tests and seven viewer checks pass.

## 2026-10-13 — Comparison loading provenance
- Include integration method, source load-area error and recorded gate status in comparison table and JSON receipt.
- Older missing checks are explicitly Not recorded rather than assumed to pass.

## 2026-10-13 — Readable comparison report
- Added Markdown report/download and inline full-text selection from the same verified comparison evidence.
- Test provenance retention, interpretation limits and Markdown table escaping; eight viewer checks pass. Browser verified complete 2,020-character selection.

## 2026-10-13 — Readable single-study reports
- Added derived per-study Markdown report/download with inline text selection and original provenance.
- Distinguish historical recorded checks from retrospective load-area warnings; test prevents masking failures.
- Browser verified full 1,959-character report selection and warning retention; nine viewer checks/build pass.

## 2026-10-13 — Workspace regression coverage
- Added live integration coverage for unsupported diagnostic models, unknown run IDs, tampered artifacts and failure-list/success-list separation.
- All 49 unit tests and 11 isolated full-stack integration tests pass with viewer/structural profiles. Disposable test services/volume were cleaned up.
- Updated roadmap to reflect completed reports, comparisons, recovery and current-host checks; engineering stress validation remains pending.

## 2026-10-13 — Automated repository regression workflow
- Added pinned GitHub Actions jobs for Python 3.9/3.11, Node 22 viewer checks/build and isolated Linux ARM64 full-stack tests.
- Read-only permissions, no persisted checkout credentials, bounded job durations and superseded-run cancellation.
- Workflow YAML structure validated locally; hosted run outcome must be checked separately. Native macOS acceptance remains local.

## 2026-10-13 — Hosted CI cleanup correction
- Hosted ARM64 ran all 11 integration tests successfully but failed deleting root-owned bind-mount files.
- Added bounded failure annotations and unit tests, then corrected disposable API/test UID/GID and pre-created mounts. Exclude .local from test checkout.
- Local wrapper/full-stack cleanup now succeeds; all 51 unit tests pass. Hosted rerun outcome recorded separately.

## 2026-10-13 — Complete numerical-check presentation
- Show all five recorded numerical checks together, including source load-strip agreement.
- Historical absent checks show Not recorded; status text distinguishes recorded checks from retrospective diagnostics.
- Explicit absence of local strip refinement distinguished from missing historical metadata in comparisons. Browser verified current/legacy study labels; ten viewer tests pass.

## 2026-10-13 — Elastic energy consistency
- Added stress-derived isotropic strain energy vs half nodal load-work diagnostic using archived material/input/output data.
- Both reviewed real studies agree within printed-output rounding; viewer verifies finer energy 39.5341 N·mm.
- Test uniaxial/hydrostatic/shear energy and invalid material/tensors; all 53 unit tests pass. Engineering stress convergence remains pending.

## 2026-10-14 — Energy evidence in readable study reports

Derived downloadable and copyable study reports now include strain energy, half applied-load work, full-precision relative error, demo tolerance, and method. Missing historical energy diagnostics remain explicitly unrecorded; malformed values and contradictory verdicts cannot appear as a pass. This diagnostic remains separate from recorded numerical gates and engineering acceptance. Saved run artifacts are unchanged.

## 2026-10-14 — Archived displacement validation

Energy diagnostics now reject truncated or oversized displacement rows, non-finite components, fractional or unknown node identifiers, and duplicate nodal records before computing external work. Signed components remain intact. Missing loaded nodes continue to fail explicitly. This prevents malformed archive data from silently replacing a node or causing an indexing error.

## 2026-10-14 — Energy mesh refinement

Archive diagnostics retain energy/work consistency for each of the three mesh sizes and compute the absolute relative strain-energy change between the last two meshes. The viewer shows this change as informational, and readable study reports preserve each mesh's energy evidence. No convergence threshold or engineering acceptance is inferred.

## 2026-10-14 — Diagnostic interpretation help

Added a compact question-mark help link beside stress and energy diagnostics. Its accessible dialog explains the half-work identity and demo tolerance, energy refinement, integration-point peaks versus averaged nodal colors, regional exclusions and corner quality. It explicitly distinguishes these numerical observations from stress convergence and engineering acceptance. Closing returns focus to the help link.

## 2026-10-14 — One-command local startup

Added `scripts/start_kcee.py` for the already provisioned geometry/FEA workspace. It checks local setup and Docker availability, starts the signed native queue worker before container bind mounts, starts the viewer/FEA profiles with health waiting, and retains a uniquely named readiness report. Rebuilds are optional; existing services/data remain intact on failures. No login agent or audio process is installed.

## 2026-10-14 — Data-preserving shutdown

Added `scripts/stop_kcee.py` to stop the container services without removing containers or volumes, then request graceful native worker termination. The worker's signed fresh heartbeat, stored PID and project-specific command must agree before a signal is sent. Shutdown waits for the signed stopped heartbeat; it does not force-kill the native worker. The default grace period is 150 seconds.

The stop/start check exposed PID 1 signal handling in the structural container. Its HTTP server now explicitly handles SIGTERM/SIGINT, stops accepting requests, and waits for active request threads during close. Docker's configured grace period still bounds container shutdown; longer jobs can exceed it.

## 2026-10-14 — Website engineering-service controls

Added Start/Stop engineering services with a stop confirmation and progress state. The viewer/API/database remain available; native PicoGK and structural analysis are controlled by a separate local supervisor with no network listener. The API sends bounded signed commands and checks response identity; external origins, missing custom headers and unconfirmed stops are rejected. Browser code never receives the signing key or Docker socket. The native stop routine is shared with the CLI command. Startup provisions the supervisor before the API bind mount. Integration checkouts precreate the new bind directory to preserve host ownership during cleanup.

## 2026-10-14 — Reconnect to pending service operations

Control status now exposes authenticated pending operation identity and action. On refresh/reload the viewer reconnects to its existing operation rather than enabling another start/stop. Stale and unverifiable queue records disable controls with an inspection message. Poll failures keep controls disabled until an explicit refresh reconnects. Completed signed responses are not resumed.
