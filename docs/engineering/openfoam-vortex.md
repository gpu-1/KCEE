# OpenFOAM velocity–pressure verification workflow

This first general CFD integration runs Debian's ARM64/AMD64 OpenFOAM 1912
`blockMesh`, `checkMesh` and `icoFoam` in the local CFD worker. Unlike the reduced
channel momentum benchmark, icoFoam solves transient incompressible momentum
and pressure correction with PISO. The current interface exposes one fixed,
2D periodic reference case, not arbitrary geometry or bracket flow.

## Reference problem

The square is [0, 2π] × [0, 2π] m with periodic x/y boundaries. One 0.1 m-thick
cell layer uses empty front/back boundaries. Initial amplitude is 1 m/s,
kinematic viscosity is 0.1 m²/s, density is a reporting convention of 1 kg/m³,
and final time is 0.5 s. The time step is 0.005 s. The analytical solution is

- u = sin(x) cos(y) exp(-2νt)
- v = -cos(x) sin(y) exp(-2νt)
- p/ρ = [cos(2x) + cos(2y)] exp(-4νt) / 4 + C
- Spatial mean kinetic energy per unit mass = exp(-4νt) / 4.

These equations are independently checked against momentum and continuity by a
unit test. The Taylor–Green analytical vortex is a standard solver verification
problem; see the [OpenFOAM community reference](https://gitlab.com/openfoam/community/verification-and-validation/-/tree/main/cases/Taylor-Green-vortex).
Our periodic domain and dimensional parameters are defined above, rather than
copied from that case. The [icoFoam tutorial](https://www.openfoam.com/documentation/tutorial-guide/2-incompressible-flow/2.1-lid-driven-cavity-flow)
provides background on the solver and blockMesh workflow.

## Numerical settings and checks

Uniform 16², 32² and 64² hexahedral meshes are generated and checked. Time uses
backward differencing; spatial interpolation, gradients and convection use
central linear schemes. Three PISO pressure corrections use a PCG/DIC pressure
solve with absolute tolerance 1e-10. Pressure is anchored at cell 0. For error
comparison and visualization, each numerical pressure field has its spatial
mean removed; analytical pressure has zero spatial mean. OpenFOAM p is
**kinematic pressure in m²/s²**, not Pa.

Acceptance gates for this implementation benchmark, chosen before integration:

| Check | Criterion |
|---|---|
| Fine velocity relative L2 error | < 0.02 |
| Fine mean-adjusted pressure relative L2 error | < 0.05 |
| Fine mean kinetic-energy relative error | < 0.04 |
| Velocity and pressure refinement | Error decreases on each finer mesh |
| Solver face-flux continuity | All recorded local errors < 1e-7 |
| Mesh validity | checkMesh reports Mesh OK on every mesh |

The face-flux continuity quantity is OpenFOAM's local time-step diagnostic,
not the maximum pointwise divergence in s⁻¹. The separately reported
cell-centre central-difference divergence does not equal the solver's
conservative face-flux continuity operator. It is retained without conflating
the two. A decreasing spatial error does not establish a convergence order or
time-step convergence. No manufactured forcing is added; analytical fields
initialize the transient solve and independently assess its final fields.

## Saved evidence and website

Choose **Run OpenFOAM vortex**. The API verifies all raw initial fields and case
dictionaries against the fixed generator, parses final U and p, recomputes
field errors/energy/diagnostics, checks the complete 100-step/300-correction
history, and compares the independently recomputed summary to the worker
response before registration. Solver execution has a 90-second timeout per
command, and the worker allows only one vortex job at a time. There is no
case-file upload or command entry. The API does not rerun the solver.

The viewer offers velocity magnitude, kinematic pressure, velocity-error
magnitude and signed pressure error at each saved resolution, optional mesh
outlines, and velocity-direction segments with endpoint dots. Every view
shows its own scale and units. Colors are based on saved computed fields.
The 3D box is only the domain envelope.

Each run saves result.json, cfd.json, field.csv (fine grid), requirements.json,
report.md, an illustrative domain STL and cfd-artifacts.zip. The ZIP includes
all generated cases, meshes, initial/final solver fields, logs and runtime.json
with package version, architecture and binary SHA-256 fingerprints. Manifest
hashes bind every artifact and the adapter source. The signed native AI
assistant and two-channel-case comparison currently remain separate workflows;
vortex runs are available through field views, reports and raw evidence.

The worker image has a read-only root, a bounded 256 MB temporary workspace,
1 GB memory limit, one CPU and no published port. OpenFOAM is pinned to the
Debian package version 1912.200626-3+b1. Source and case generation are portable
to Mac Studio via the existing Docker Compose layout.

Physical validation, turbulence, arbitrary-domain meshing, time-step studies,
3D flows and coupled thermal-fluid engineering acceptance remain pending.
