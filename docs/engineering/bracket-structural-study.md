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
