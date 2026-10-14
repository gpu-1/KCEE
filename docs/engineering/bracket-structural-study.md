# Native bracket structural study

This analyzes the verified native PicoGK STL, preserving its holes and root transition. It is distinct from the rectangular cantilever verification benchmark. Select a saved native bracket, then Analyze selected bracket. The first supported case is the default 60×30×40 mm bracket, 3.5 mm thickness, 100 N load and E=69000 MPa. Other dimensions/material/loading cases are rejected explicitly until parameterized rules are implemented.

Gmsh 4.8.4 classifies the actual triangulated surface at 20 degrees, parameterizes it and produces straight-sided quadratic tetrahedra. C3D10 connectivity is reordered from Gmsh to CalculiX and independently checked using midside-node coordinates. Non-positive element volumes and >50,000 nodes are rejected. Original STL bytes remain unchanged; meshes and input decks are archived separately. An initial 45-degree classification failed parameterization and is not used.

The rear upright face (|x|<0.05 mm, z>3.5 mm) has all translations fixed. This is an idealized full clamp, not bolt/contact behavior. A total 100 N downward load is distributed over the top free-end strip near x>=55 mm using triangle area weights and consistent six-node face weights. The numerical patch boundary is approximate; its area variation is tracked. No artificial point load is applied.

Target sizes are 2.5, 1.8 and 1.5 mm. Checks require <5% final displacement change, <0.1% force imbalance, <5% final load-patch area change, and <2% fine mesh volume difference from native voxel volume. The reference bracket study produced approximately 0.7803 mm loaded-patch displacement, 100 N reaction, and 0.494% final displacement change. These establish limited numerical checks, not engineering acceptance. Peak stress is archived/displayed as unconverged and is not used for a factor of safety.

Each analysis creates a child design with the selected parent UUID, parent manifest hash, identical source STL hash, native metadata, explicit structural assumptions, solver/mesher versions and source/binary hashes, and zipped solver/mesh/log output. Failed jobs retain failure.json and available raw diagnostics; no completed manifest is issued for execution failure. Numerical-check failures can be retained for review and are never labeled passed.

Worker limits: internal-only service, 1 GB memory, two CPUs, one job at a time, 256 MB temporary scratch, 300-second bracket-job timeout and 120 seconds per CalculiX solve. Start with `docker compose --profile viewer --profile fea up --build -d --wait`. Native geometry worker startup remains separate. Regression: `python3 scripts/check_bracket_fea.py --run-id NATIVE_RUN_UUID` against the running local API.

Next: independently verify the tetrahedral formulation on more benchmarks, refine geometry/mesh resolution, define real mount/contact conditions, validate material allowables, test load cases and compare with physical measurements. Bracket fabrication approval, fatigue, buckling and thermal coupling remain outside this study.

## Verify displayed fields

Run `python3 scripts/check_bracket_fields.py --run-id <saved-bracket-analysis-id>` while the API is running. This read-only check downloads and verifies the solver archive, compares preview geometry/displacement vectors exactly, and compares derived magnitudes at 1e-12 relative/absolute tolerance for platform rounding. It also checks closed, consistently oriented surface edges and agreement with the fine solver mesh volume. It does not establish physical validity or stress convergence.

## Clipped-face load integration

New studies clip each planar top face at x=55 mm and integrate quadratic face shape functions over the clipped polygon using degree-two triangle quadrature. This preserves total traction force and its first moment on each planar face instead of selecting whole triangles by centroid. Consistent corner weights can be negative on a partially loaded quadratic face. Solver midside positions remain linear; the source STL is unchanged. The global total is normalized to 100 N. The existing top-face z tolerance and ideal clamp remain.

Recorded revised studies are d5351ced (baseline) and 90f8cb89 (finer), with full identifiers/evidence in clipped-load-study.json. Final displacements are 0.780636 and 0.783470 mm. Last patch-area changes are 0.0003406% and 0.582955%; baseline/finer final patch areas remain 130.928 and 114.937 mm², so cross-geometry differences are not isolated. Both pass numerical checks and archive-to-preview verification. Stress peaks remain unconverged. Existing saved studies were not modified. New studies record the integration helper source hash.

## Source load-strip agreement

A retrospective check now clips the original STL with the same x≥55 mm/top-face tolerance used for loading, then compares its area with the fine volume mesh load strip. For clipped-load baseline d5351ced, source/mesh areas are 130.930924/130.927573 mm² (0.00256% error). For finer study 90f8cb89, they are 135.823083/114.937223 mm² (15.3773% error). This reveals a local source-to-volume-mesh representation discrepancy not caught by total volume/within-study patch checks.

New solves require source load-area agreement within 5% as an additional numerical gate; this threshold is a demo diagnostic, not a physical acceptance criterion. Existing immutable validation statuses are preserved, with a retrospective Needs attention warning in the viewer. The finer study must not be accepted on its previous checks alone. Further work must resolve the top-surface representation and area selection before interpreting geometry sensitivity.

## Load-surface selection sensitivity

Run `python3 scripts/check_load_surface.py runs/<id> --manifest-sha256 <trusted-hash> --output <new-report.json>` for a read-only tolerance sweep. load-surface-sensitivity.json records the two clipped-load studies. Mesh values use the subdivided preview surface; face inclusion can differ slightly from the original quadratic-face mask.

For the finer study, the preview strip area grows from 114.937 mm² at 0.05 mm top-face tolerance to 130.415 mm² at 0.1 mm; the original STL remains 135.823 mm² at both tolerances. At 0.2 mm, the source selection grows to 148.039 mm², showing that a wider mask includes additional curved surface. The baseline is much less sensitive at 0.05–0.1 mm.

This identifies sensitivity to the remeshed top-surface representation and face mask. It does not quantify nearest-surface distance or prove the cause of mesh distortion. The production 0.05 mm mask and 5% source-area gate remain unchanged. Do not widen the tolerance simply to pass the gate; a validated surface tagging or geometry-preserving mesh procedure is still needed.

## Original surface partition probe

Run `docker compose exec -T structural python - --run-id <native-run-id> < scripts/probe_surface_partition.py` to inspect classified original STL entities without parameterizing, meshing or solving. The probe verifies the database run and downloaded STL hash before classification. surface-partition.json records the finer source at 20°/30°.

Neither classification isolates a top entity whose nodes (including boundary nodes) all lie in a horizontal plane within 0.0001 mm. At 30°, one candidate touching the free-end top region spans 3.5033 mm in z; another spans 0.2495 mm. Thus projecting whole classified entities to z≈3.5 would alter nonplanar portions of the source. This diagnoses partition membership, not exact remeshing error. A separate planar-patch partition or a geometry-preserving constrained mesh approach is needed; the existing source-area warning remains.

## Improved finer-STL classification

Fine-mesh probes on the unchanged 0.35 mm source measured source strip errors of 3.038% at 25°, 24.558% at 35°, and 15.539% at 45°. A new full 25° study c072e470-2fd9-452a-aee2-19d9cb2a2329 passes all five numerical gates, including source load-strip agreement, and archive-to-preview verification. Its fine displacement is 0.790682 mm and unconverged peak stress is 217.242 MPa. Full evidence is in finer-25deg-study.json.

New finer-source jobs use 25°; the baseline remains at 20°. No source geometry or load tolerance is changed. Existing 30° studies retain their retrospective warning. This addresses the area-agreement gate, not exact surface fidelity or engineering acceptance. Reproduce bounded probes with `docker compose exec -T structural python - --run-id <native-run-id> < scripts/probe_meshing_angles.py`. The source hash is checked and no solve/registered run is created by the probe.

## Regional peak diagnostics

The hotspot report now includes stress peaks after excluding elements whose corner centroids are within 1, 2 or 3 mm of either nominal rectangle: rear clamp x=0, y=0..30, z=3.5..40, or load strip z=3.5, x=55..60, y=0..30. The same element eligibility applies to its four integration points. These distances are not exact integration-point distances and do not remove physical stress concentrations rigorously.

For study c072e470, each regional maximum is 88.049 MPa while the unfiltered global peak remains 217.242 MPa. Included element counts are 15,953, 14,592 and 12,028 respectively. Evidence is in regional-stress-diagnostics.json. This identifies a diagnostic spatial pattern, not stress convergence, a safety factor or a permissible stress. The viewer keeps the global peak visible and marks regional values as not allowables.

## Regional stress refinement across archived meshes

The diagnostics repeat centroid-exclusion peak measurements at 2.5, 1.8 and 1.5 mm mesh targets. Evidence is in regional-stress-refinement.json. Baseline regional peaks are 95.32, 97.79 and 98.33 MPa (0.5512% final change). Finer-study peaks are 99.44, 102.98 and 88.05 MPa (14.4957% final change). These changes are informational, not convergence acceptance. Stable displacement does not establish stable stress; more refinement and validation remain required.

## Stress-energy / load-work consistency

For straight-sided C3D10 elements, the diagnostic integrates isotropic elastic energy density from the six printed stress components at four equal-weight tetrahedral integration points. Material E/Poisson ratio are read from the archived input. It compares this with one-half the sum of applied nodal forces times their signed solved displacements. This identity assumes small-strain linear elasticity and zero prescribed support displacement. Values are N·mm.

The baseline clipped-load study gives 39.03177802 N·mm and relative discrepancy 3.78e-10; finer 25° study gives 39.53407841 N·mm and discrepancy 6.66e-9. Source hashes and method are recorded in energy-consistency.json. A 0.1% demonstration tolerance is displayed as a diagnostic only. Printed output rounding affects the last digits. Agreement does not establish constitutive validity, stress convergence or physical acceptance, and does not change saved validation statuses.

## Exploratory 1.3 mm follow-up

A separate finer-mesh solve reaches 47,921 nodes and 26,442 elements within the existing solve budget. Compared with the saved 1.5 mm case, displacement changes 0.462%, global stress 7.129% and regional stress 7.517%. Stress convergence remains unresolved. A 1.2 mm candidate exceeds the node limit and is not solved. See [source-traced exploration](finer-mesh-exploration.md). This experiment does not modify the three-mesh saved study or its status.

## Local root refinement

Separate 0.9 and 0.75 mm local-root targets raise the global peak to 328.251 and 334.430 MPa while displacement remains within 0.21% of the saved study. The source load-strip area remains unchanged. This reinforces the need to resolve root stress sensitivity and justify the mounting model before using peak stress. See [source-traced root investigation](root-refinement-exploration.md). These values are exploratory, not accepted allowables.
