# CalculiX cantilever verification

The first structural worker solves a separate 60 × 10 × 3.5 mm rectangular cantilever with C3D20 quadratic solid elements, E=69,000 MPa, Poisson ratio 0.33, fully fixed translations at x=0 and a uniform total 10 N downward end load. Consistent quadratic-face nodal loads integrate to exactly 10 N. Reference displacement uses Euler–Bernoulli beam theory: 4 F L³/(E b t³) = 0.292052 mm.

Three meshes contain 16, 128 and 432 elements. The fine-mesh work-conjugate tip displacement is approximately 0.287810 mm: 1.452% from the beam reference. Change from the preceding mesh is 0.346%; support reaction is approximately 10 N. Acceptance thresholds are <5% analytical displacement error, <2% last-mesh displacement change and <0.1% force imbalance. This verifies this benchmark implementation only. Root peak stress is mesh/boundary sensitive and is not accepted as a converged allowable.

Inputs, logs, nodal displacement, integration-point stress, mesh and field output are retained in fea-artifacts.zip for every completed benchmark. The design manifest hashes the archive, result and report. Solver binary, adapter source, version and architecture are recorded. No dependency is downloaded while solving.

Run `docker compose --profile viewer --profile fea up --build -d --wait`, then use Run FEA benchmark in the viewer. Native bracket creation remains separate. Worker is internal-only, read-only, limited to two CPUs and 512 MB, with a temporary scratch directory and one benchmark at a time. CalculiX uses one solver thread and a 90-second limit per mesh. Results are labeled benchmark_verified_only.

Next: volume meshing of the PicoGK bracket with resolved holes/fillet, realistic bolt/contact boundary conditions, load transfer and independent convergence checks. The current benchmark does not analyze that bracket, thermal loads, fatigue or buckling. Source: https://www.dhondt.de/ ; package: https://packages.debian.org/bookworm/calculix-ccx

Regression command: `python3 scripts/check_integration.py --viewer --fea` builds an isolated database/API/viewer/solver stack, solves the real benchmark and verifies stored artifacts, then removes its own test services.
