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
