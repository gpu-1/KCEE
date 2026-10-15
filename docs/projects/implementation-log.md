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

## 2026-10-14 — Live engineering-service status

The website now shows Running, Partly running, Stopped or Status unavailable from current capabilities. A bounded status poll runs every ten seconds while the page is visible and immediately when returning to the tab. It updates worker availability and control buttons without reloading the saved-run list or current model. Overlapping polls share one request, and unknown status is not displayed as stopped.

## 2026-10-14 — Compact service controls

Moved the On/Off indicator beside Engineering services and shortened the two buttons to Start and Stop in a shared row. On means at least one engineering worker is available; the tooltip and individual statuses distinguish partial availability. Unknown is retained when status cannot be checked.

## 2026-10-14 — Bounded finer-mesh exploration

Added a verified-source mesh probe and shared single-mesh solver procedure. The production study still uses 2.5/1.8/1.5 mm targets. The exploratory 1.3 mm case remains under 50,000 nodes, whereas 1.2 mm exceeds that limit and is not solved. Evidence and comparisons are documented separately; saved run artifacts/statuses remain unchanged and stress convergence remains pending.

## 2026-10-14 — Local root sensitivity

Added bounded optional root-box refinement for exploratory single-mesh solves; production defaults remain unchanged. Both 0.9/0.75 mm local targets fit the solve budget and complete with force balance and energy consistency. Stress rises substantially relative to the saved unrefined-root study despite stable displacement and unchanged load-strip area. Source and archive hashes are verified and separate evidence is documented. Stress acceptance remains pending.

## 2026-10-14 — Website exploration evidence

Added source-linked recorded exploration evidence to a separate panel for the matching verified bracket study. The table presents the 1.3 mm global mesh and 0.9/0.75 mm local-root targets; full evidence is available to copy. The API verifies saved run integrity and matches manifest/STL hashes before returning bundled investigation records. Archive hashes are recorded evidence, not a claim of live archive verification. No exploratory result replaces the original study or its validation status.

## 2026-10-14 — Explorations in readable report export

Study report exports now include a separate exploratory refinement table when source-linked investigations exist. Full-precision measurements, report hashes and recorded archive hashes accompany explicit source matching and archive-verification limits. Source mismatch and malformed measurements cannot be exported as evidence. Empty or unavailable investigations do not add a results table.

## 2026-10-14 — Live exploratory archive verification

The API now streams SHA-256 checks of fixed exploratory archives through a read-only host mount. Available matching files are marked verified; missing files remain recorded evidence only. Changed, oversized or unsafe linked archives are rejected. Website and report wording reflects the current verification state. Startup and isolated integration checkouts precreate the bind directory; a new host can still show recorded evidence without local archives.

## 2026-10-14 — Verified exploratory archive downloads

Added per-case ZIP downloads for available source-linked exploratory archives. The download endpoint verifies saved run identity and report linkage, then hashes the exact bytes returned; a changed archive cannot be served under its recorded hash. Only the three fixed experiment keys are accepted. Missing host archives have no download link.

## 2026-10-14 — Native Kokoro summary playback

Provisioned local quantized Kokoro ONNX weights and an isolated pinned Python runtime. Added signed, bounded native summary jobs, source-linked audio metadata, API integrity checks and independent browser WAV hashing. Bracket study playback is explicitly opt-in through an audio control; selecting another run clears playback. No original artifacts are modified. Voice transport is mounted separately from weights/runtime. Automatic alerts, priority scheduling and whisper input remain pending.

The exploratory archive link text is now ZIP to fit the compact table column; descriptive accessibility labels are retained. Native Kokoro produced the saved bracket summary successfully and the browser verified its bytes. The audio control reports 5.099 seconds, loaded and paused with autoplay disabled.

## 2026-10-14 — Website voice lifecycle controls

Added local voice On/Off status and Start/Stop next to engineering controls. Voice stop asks for confirmation and pauses current audio; the website/database remain running. The signed supervisor accepts only fixed voice_start/voice_stop actions. Its starter now safely reloads stale supervisor code only when no operation is active, checking signed heartbeat and process identity before graceful termination. No provisioning or model download is triggered from the website.

## 2026-10-14 — Verified voice audio export

Prepared voice summaries now expose Download audio (WAV) using the same hash-checked bytes as the player. The link appears only after successful source/audio verification, and selecting another study clears it together with the player and revokes the blob URL.

## 2026-10-14 — Voice provenance export

Prepared audio now has downloadable/copyable JSON linking its checked bytes to the saved study manifest, source summary, job identity and Kokoro model manifest. The export validates those identities and keeps saved validation status unchanged. Selecting another study clears audio and evidence together. This derived export does not register a new engineering result.

## 2026-10-14 — Voice readiness and migration preflight

Read-only host readiness now optionally checks Kokoro worker availability, model-file hash/size integrity and pinned native dependencies. Voice-enabled startup includes these checks and reports its narrower geometry/FEA/voice scope explicitly. No synthesis, playback, installation or model downloads occur during readiness checking. Destination audio quality and unimplemented subsystems remain separate acceptance work.

## 2026-10-14 — Heart voice default

Set the local synthesis default to Heart (`af_heart`), US English female, at 1.2× speed. Worker response and downloadable provenance now record the speed and language alongside the voice. Previously generated jobs are unchanged; missing historical speed/language are not inferred.

## 2026-10-14 — Roadmap checkpoint

Updated the implementation roadmap to reflect measured bore profiles, global/local-root refinement evidence and archive downloads, native manual Kokoro voice feedback, website lifecycle controls, audio/provenance exports and optional voice readiness. Local AI, speech input, thermal physics, complete database backup/restore and engineering acceptance remain explicit outstanding milestones.

## 2026-10-14 — Grounded local Metal study assistant

Provisioned pinned upstream llama.cpp b11417 and official Qwen3 4B GGUF assets with upstream SHA-256 checks. Added authenticated loopback inference, signed native jobs, bounded verified evidence snapshots, schema-constrained citations and a read-only website question panel with confirmed AI lifecycle controls. All 37 model layers are offloaded to Metal. Initial unsupported citation output was rejected rather than served; schema/category prompting was corrected. Actual tests refused a validation-override/manufacture claim and an unsupported thermal query. Answers remain drafts; no model tools or engineering acceptance are granted. Voice defaults remain Heart, US English, 1.2×.

Verification: 70 standard-library tests, 13 viewer tests and 14 isolated integration tests passed. Optional AI/voice/reference readiness passed. Browser checks confirmed a real study answer, cancellation of stop confirmation, independent AI stop/start with engineering and voice remaining On, and preservation of the completed draft during status polling. Unauthenticated private model access returned HTTP 401. AI is left On. These checks do not certify general answer accuracy or engineering acceptance.

## 2026-10-14 — Downloadable local AI answer record

Completed AI drafts now offer a JSON download and a selectable copy view containing the exact question, answer, supplied source snapshot, evidence hash, model/runtime/prompt fingerprints and generation settings returned by the verified local gateway. New questions and study selection clear the export so old answers cannot be attached to another study. This derived record does not change saved results or acceptance status.

Retry verification caught an ambiguous displacement answer drawn from a separate exploratory run. The evidence snapshot now explicitly names the selected original study’s finest saved mesh displacement and unconverged peak, and the prompt specifies this default. A fresh real-model answer returned 0.7906815628368744 mm for the selected study. Browser checks verified the complete export fields, readable copy view and clearing on study selection. 70 Python tests and 13 viewer tests passed; viewer production build passed. This targeted correction does not guarantee all model answers are accurate.

## 2026-10-14 — Suggested study questions

Added compact displacement, stress convergence and refinement question buttons. Each fills the editable question box; inference only starts when the user presses Ask local AI. Suggestions explicitly distinguish the selected original study from exploratory follow-ups and are disabled while an answer is pending.

## 2026-10-14 — Readable AI answer download

Added a plain-text companion to the full JSON answer record. It preserves the exact question and draft answer, evidence categories, study/source hashes, job identity, model/runtime/prompt fingerprints and generation settings. Both exports clear together on a new question or study selection.

## 2026-10-14 — Steady thermal verification worker

Added isolated 1D conduction, four-grid manufactured-solution verification, API-side reproduction, registered thermal runs with source fingerprints, temperature CSV, original profiles and report. Website thermal results distinguish numerical verification from bracket validation. Engineering service controls now include the thermal worker. Fine-grid error is 0.0025704 °C; observed final order is 2.00033 and relative heat balance error is 3.00e-14. No bracket thermal solve or coupling is claimed.

Verification: 72 Python tests, 13 viewer tests and 15 isolated registry/integration tests passed. Website checks created and verified thermal run f8a1f44a-9b6e-45c8-958d-e2ca77d3a3ce. Its fine-grid profile, heat flows and convergence table rendered correctly. Engineering Stop turned thermal off while preserving saved results and leaving AI and voice On; Start restored the workers. The disposable integration test independently checked CSV bytes against the registered hash and rejected a tampered profile.

## 2026-10-14 — Thermal profile and error charts

Added numerical/analytical temperature comparison and a separate absolute-error plot at saved nodes. A mesh selector shows each of the four verified profiles without re-solving. Axes label position in mm and temperature/error in °C; the fine mesh is the default. Selecting another run clears chart state.

## 2026-10-14 — Visible thermal checks and recorded tolerances

Thermal benchmark results now record their numerical tolerances. The website displays all five check verdicts, measured errors or refinement orders, and saved thresholds. Older immutable runs keep their recorded checks but show absent thresholds as not recorded; no historical values are invented.

## 2026-10-14 — Native bracket steady thermal study

Added actual native-STL Gmsh/C3D10 steady conduction through the existing isolated CalculiX worker. Fixed illustrative conductivity and 20/80 °C reservoirs are explicit; all other surfaces are insulated. A separate exact C3D20 bar verifies the thermal solver procedure. Three meshes, heat balance, boundary/range, source-volume and global refinement checks are saved with immutable parent/source fingerprints and raw solver evidence. Website temperature colors come from archived nodal values and do not deform geometry. No realistic thermal conditions, local flux convergence, structural coupling or engineering acceptance is claimed.

Actual study 2c5c8413-8154-4cc6-b76f-fd849b8a7560 derives from c072e470-2fd9-452a-aee2-19d9cb2a2329. Fine total heat is 1.499583 W; last heat-flow change 0.1401%, last mean-temperature change 0.0420 °C. All seven numerical gates passed. Exact bar temperature error is zero at saved precision and computed heat is 0.525 W. Saved CSV and solver archive downloads matched their registered hashes. Temperature preview contains 19,846 surface nodes and is archive-linked.

Verification: 74 Python tests, 13 viewer tests and 16 isolated integration tests passed. The website created the real three-grid study and displayed source-linked temperature colors with deformation controls hidden. Unit checks reject invalid/non-finite field values and mismatched ranges/connectivity. API integration rejects unsupported source kinds. Actual CSV/archive bytes matched registered hashes and the whole saved run verified against the database manifest. Existing native generation, structural analysis, 1D thermal, AI and voice services remain available.

## 2026-10-14 — Thermal boundary markers

The bracket thermal viewer now enables a Thermal boundaries toggle. Blue and red outlines identify the nominal 20 °C rear upright and 80 °C free end; the legend states that remaining surfaces are insulated and boundaries are ideal reservoirs. Markers follow the original geometry without deformation. Structural load/support labeling and markers are restored when switching back to a structural study.

## 2026-10-14 — Local AI for verified thermal studies

Extended bounded read-only assistant snapshots to bracket thermal and 1D thermal verification runs. Evidence includes the selected fine mesh, imposed conditions, numerical checks/tolerances, global refinement and exact-reference diagnostics; full nodal profiles are excluded from model context. Thermal questions and prompts distinguish imposed reservoirs from computed results and do not invent structural stresses or local heat-flux convergence. Existing source hashes, signed jobs, draft labels and exports apply unchanged.

Verification: 76 Python tests, 13 viewer tests and 16 isolated integration tests passed. Real local-model tests explained the bracket’s ±1.4996 W balance and 38.2938 °C volume mean, refused to invent mechanical stress for the thermal-only source, and returned the 1D benchmark’s recorded 80.1811 °C peak. The separate rectangular solver reference is explicitly scoped in supplied diagnostics. These targeted checks do not certify every generated answer.

## 2026-10-14 — Local document knowledge and exact source citations

Added immutable original UTF-8 text/Markdown sources and line-preserving chunks to PostgreSQL with English full-text indexing, application SELECT/INSERT grants and append-only triggers. Uploaded sources deduplicate by original SHA-256. The website verifies and shows original plain text; opted-in study questions receive at most four rechecked excerpts with exact line ranges and source/passage fingerprints. Native schema-constrained responses identify supplied document IDs; unsupported references and mismatched inline markers are rejected. Structured citations are displayed below the answer, with original excerpt/download and exported source lineage. References cannot change saved solver inputs or approve engineering acceptance. Semantic embeddings, PDF extraction and document removal remain pending.

The website uploaded the actual project bracket thermal guide and verified its source hash. A real local-model answer correctly cited its 15 W/(m·K) conductivity at lines 1–8 and kept the saved study unchanged. Initial output supplied a valid ID without an inline marker; the source reference list now supports this form while retaining strict ID/source checks. No generated prose is treated as verified engineering evidence.

Verification: line-preserving original-byte/hash checks, invalid-input/citation rejection, source-name/line-range tamper checks and signed no-match response checks passed. The isolated integration suite verified local upload authorization, byte-identical original download, SHA-256 metadata, deduplication, natural-question lexical retrieval and append-only grants/triggers. Real native inference cited the project guide correctly. An empty-source schema initially produced a truncated response and was withheld; empty retrieval now uses the ordinary bounded response schema and correctly reports missing information without document references. Sources and complete cited evidence are retained in answer exports; no keys or raw source files are sent to remote services.

Final checks: 81 Python tests, 13 viewer tests and 17 isolated integration tests passed. The final website displayed a real local-model answer with its original passage and line-range citation. No-match inference returned missing information with no document citations. The uploaded thermal guide remains locally stored; model, geometry, structural, thermal and voice services remain available.

### Evidence verification reports

The document workspace Verify panel now exports TXT and JSON reports after snapshot checks and after optional local source checks. Reports record the exact imported file byte count and SHA-256, check timestamps, snapshot identity and counts, and the local result or failure/unavailability. Changing the input clears downloads; checking again replaces the report. JSON reports carry a SHA-256 over UTF-8 compact JSON in recorded property order, excluding `report_sha256`. No evidence payload or original PDF is copied into the report. Reports are unsigned self-consistency records: matching hashes do not prove authorship, OCR accuracy, relevance or engineering validity. Files rejected before reading (type/size limits) do not produce reports.

### Backup and restore status in the document workspace

A Backup tab reads the newest local bundle receipt and restore verification record independently through a read-only API. It shows record modification times, inventory counts, stored bundle SHA-256, file presence and whether review-note verification was recorded. It does not rehash bundles, certify current database coverage or imply the restore tested the displayed bundle. Invalid newest records are reported rather than silently replaced with older successes. The API exposes sanitized names, not host paths or source payloads. The backup folder is mounted read-only; no start/restore controls or archive downloads are exposed. Future successful restore commands retain a status record in `.local/backups`; old records without event timestamps are labelled by file modification time.

### Literal search-result highlighting

Search passages highlight whole query words and decimal numbers, case-insensitively, with common English/Spanish words ignored. A checkbox turns presentation highlighting off or on without fetching again. Semantic-only matches may have no highlighted tokens. Rendering creates text-only span/mark nodes; literal OCR, citation payloads, hashes and exports remain unchanged. Tests cover token boundaries, decimals, Unicode, exact text preservation and HTML-like source text.

### Saved document searches

Search can save up to 50 questions with all-document or selected-document scope in this browser's local storage. Identical question/scope saves update the existing entry. Load restores the question and scope without automatically querying or reusing historical evidence; rerunning verifies current sources and rejects unavailable/archived documents. A selected document outside the current library page is retained in the selector until the next library refresh. Removal requires an inline confirmation. Corrupt or unavailable browser storage is reported without overwriting it. Saved questions are device/browser-local and excluded from project backups; evidence exports remain separate.

### Current library backup coverage

The Backup panel compares a consistent read-only database snapshot with the latest receipt. New backup audits and receipts carry a deterministic, length-framed SHA-256 fingerprint of ordered document, passage, extraction, embedding, visibility and note metadata (including stored content hashes and record identities). Restore verification compares this fingerprint when present. Old receipts can establish count differences but matching counts are explicitly inconclusive. Matching metadata requires local bundle presence and does not rehash archive/source bytes, certify OCR, include browser saved searches or establish whole-project coverage.

### Saved-search transfer

Saved searches can export versioned JSON with a SHA-256 snapshot digest and import UTF-8 JSON up to 256 KB. Preview validates the complete file and reports additions/duplicates before applying. Import merges atomically, preserves existing entries and assigns new local identities; duplicate question/document pairs are skipped. Overflow beyond 50 or invalid storage rejects the whole import. Files contain only questions, document selections and saved timestamps, not source documents/evidence; matching hashes do not establish authorship or document availability.

### Retrieved passage page filter

Search results can be filtered by physical PDF page number across matching documents, or to text documents. The filter shows visible/total passage counts and resets on new results or scope changes. It filters the retrieved set only; it does not rerun retrieval or discover other pages. Search exports and source hashes retain the complete original result.

### PDF page bounds before retrieval

Search optionally limits a selected active PDF to an inclusive physical page range. Bounds are validated against the stored page count; keyword and pgvector SQL apply them before ranking limits, including semantic fallback. Responses and evidence exports retain the requested bounds; the browser rejects out-of-range results. Saved-question and assistant handoffs are disabled for ranged searches because those flows do not yet retain page bounds. Display-only page filtering remains separate.
