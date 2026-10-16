# First native-bracket external-flow workflow

Select a saved default PicoGK 60 × 30 × 40 mm bracket (3.5 mm thickness,
mounting bores) and choose **Explore bracket flow**. The source STL is verified
against its registered manifest before use. Derived structural studies with the
same native geometry can also supply the surface. Baseline STL-only runs and
reference vortex/channel cases cannot be used as native source designs.

## Surface preparation and external mesh

The binary STL is converted from millimetres to metres by a factor of 0.001.
Triangle connectivity is preserved; no smoothing, hole filling or repair occurs.
Both original and converted surface SHA-256 hashes are recorded. Bounded input
size, triangle count, finite coordinates and default envelope are required.
OpenFOAM surfaceCheck records surface closure/topology. This does not constitute
a comprehensive independent CAD or self-intersection validation.

blockMesh creates a surrounding domain x=[-0.12,0.24], y=[-0.09,0.12],
z=[-0.10,0.14] metres, with 24×14×16 background cells. snappyHexMesh performs
castellation and snapping to the actual source surface, retaining the external
connected fluid region. Surface refinement level 3 gives a nominal 1.875 mm
cell size near the bracket. No prism layers are generated. The actual final
mesh and quality diagnostics are saved. See the [OpenFOAM snappyHexMesh guide](https://www.openfoam.com/documentation/user-guide/4-mesh-generation-and-conversion/4.4-mesh-generation-with-the-snappyhexmesh-utility)
for the mesher's refinement and retained-region concepts.

The first case is deliberately coarse. Five-millimetre bores, 3.5 mm walls and
root geometry may be under-resolved or distorted by the fluid mesh. Surface
closure and mesh-quality checks do not establish preservation of bore area,
source volume agreement, boundary-layer resolution or mesh independence.

## Fixed exploratory flow

OpenFOAM 1912 simpleFoam runs 500 steady SIMPLE iterations with laminar
Newtonian transport and kinematic viscosity 0.0001 m²/s. Inlet velocity is
(0.01,0,0) m/s. Reynolds number based on 60 mm is 6. The bracket is no-slip;
outer side boundaries are slip; outlet kinematic pressure is zero, with
zero-gradient velocity. Density is a reporting convention of 1 kg/m³.
Pressure is p/ρ in m²/s², not Pa. Iteration numbers are not physical seconds.
No mounting wall, bolt/contact flow, turbulence, heat transfer or force
acceptance is included. These inputs are not claimed as service conditions.

Momentum uses bounded upwind convection, central gradients and corrected
Laplacians. Pressure uses GAMG; velocity uses a symmetric Gauss–Seidel smooth
solver. Under-relaxation is p=0.3 and U=0.7, with two non-orthogonal corrections.
The source dictionaries are preserved so these settings are reviewable.

## Diagnostics and evidence

Checks require a closed source surface, checkMesh's Mesh OK, finite fields,
last initial velocity residuals below 1e-5, last initial pressure residual below
1e-4, final local solver continuity below 1e-6, and relative net volume-flux
imbalance below 1e-5. The signed inlet/outlet/side/bracket phi sums are read from
the final boundary face-flux field. Relative imbalance is |sum Q|/|Q_inlet|.
These gates assess this exploratory execution. They do not establish physical
validation, force accuracy, mesh/domain convergence or engineering acceptance.

The API regenerates expected source conversion and fixed dictionaries, compares
them byte-for-byte with the worker archive, parses the final raw U/p/phi and
mesh addressing, and independently recomputes the displayed diagnostics.
It does not rerun the solver. Invalid execution retains a failure record and,
when available, a raw solver archive in the existing retained-failures workflow.
A completed execution with attention checks is labeled accordingly rather than
being represented as passing.

Successful saved runs preserve parent identity and manifest hash, the exact
source STL, geometry metadata, requirements, cfd.json, result.json, field.csv,
report.md and cfd-artifacts.zip. The ZIP contains converted surface, case files,
fluid mesh, final fields, residual logs and package/binary fingerprints.
Every saved artifact is bound to the run manifest. No solver file upload or
arbitrary command entry is exposed. The existing private worker, one CPU,
1 GB memory and bounded temporary storage are used.

## Field viewer

The actual source bracket appears gray in the existing Three.js view. Colored
points represent computed fluid cell fields: velocity magnitude or kinematic
pressure. Point positions are arithmetic means of each cell's unique mesh
vertices, computed from owner/neighbour/face addressing; they are **not** exact
volume centroids or interpolated surface contours. This avoids dependence on a
post-processing function-object utility that fails in this packaged runtime.

Choose a mid-width band (y=15±2 mm), near-bracket volume, or full domain. These
are display scopes only and preserve each selected point's actual 3D position.
The blue-to-red scale is reported with units for each view. Orbit/zoom inspect
the fluid volume; field.csv and the raw mesh retain every cell's data.
Numerical forces, skin friction and pressure contours on the solid are not
provided by this point view. The local AI and study comparisons remain separate
from this initial exploratory bracket-flow workflow.

Regression coverage uses an explicitly synthetic, hole-free L fixture to test
the worker/transport and raw evidence reconstruction. That fixture is not
represented as PicoGK or as physical validation. The local end-to-end check
uses the real saved PicoGK bracket with its bores and parent provenance.

## Three-mesh verification and bore preservation

Choose **Verify bracket flow · 3 meshes** on a native source or a saved flow
case. Three immutable source studies are saved before a derived comparison:

| Mesh | Background cells | Nominal maximum near-surface cell |
|---|---|---|
| Coarse | 24×14×16 | 1.875 mm |
| Medium | 32×20×22 | 1.40625 mm |
| Fine | 40×24×28 | 1.125 mm |

The fixed physical domain, source surface, laminar inputs, relaxation factors,
500 iterations and surface refinement level 3 remain the same. Each actual
mesh, final field, quality/residual log and runtime fingerprint is retained in
its own source study. All cases undergo raw-evidence reconstruction in the API.
If a later mesh fails, earlier completed studies remain saved.

Bore preservation uses actual triangulated bracket wall faces from the fluid
mesh, compared with the original STL. For each of the four nominal holes,
69 axial rays sample a 0.5 mm grid inside radius 2.25 mm. Another 16 rays form
an outer control ring of radius 3 mm. Axial segments run from -1 mm to 4.5 mm
through the 3.5 mm base/upright plate. A triangle intersection blocks that ray;
edge hits count as blocked. This checks through-opening continuity at sampled
locations rather than inferring an open hole from nearby cell positions.

The descriptive sampling gate requires an open source/mesh center, at most
5% of source-open rays blocked by the mesh, and at most 5% of source-blocked
rays unexpectedly open. Source and mesh open counts, blocked rays and
unexpected open rays are retained separately for each hole and mesh.
The mix of core/ring samples must not be interpreted as an area quadrature.
Finite samples do not establish minimum diameter, exact open area, continuous
clearance everywhere, bore hydraulic resistance or manufacturing acceptance.
Missing wall faces cannot pass solely because a center ray is open: the outer
control rays detect unintended widening.

Historical version 1 comparisons used eight fixed physical probe requests covering upstream, wake, above/below and the
four bore centers. Those studies record the nearest mesh-vertex-average location,
its distance from the requested point, velocity vector, speed and kinematic
pressure. Nearest-cell sampling is not interpolation at an identical point;
changing sample locations contributes to the measured changes. Reports retain
both requested and actual coordinates so this limitation is reviewable.

Successive velocity vector changes are normalized by inlet speed 0.01 m/s.
Successive pressure changes are normalized by the inlet kinematic dynamic
scale 0.5 U² = 0.00005 m²/s². These quantities are sensitivity measures, not
analytical errors or force convergence. No asymptotic order, Richardson
extrapolation or mesh-independent solution is asserted.

The derived comparison is a separate registered run. It binds all three
source run IDs and manifest hashes, source STL hash, mesh/solver checks, bore
samples, probe values, distances and changes. Report Markdown, comparison JSON
and verification.csv are available together. Open each source row to inspect
its 3D fields and full solver archive. The comparison retains the common
physical inputs and original parent manifest; existing studies are unchanged.
The worker's single-case request interface remains backward compatible; new cases include the downstream refinement box described below. Historical
single-case results without bore evidence explicitly show it as unrecorded.

Passing the execution and finite bore gates does not establish mesh/domain
independence, boundary-layer or force accuracy, or engineering acceptance.


## Fixed-location interpolation and downstream refinement (version 2)

New runs add the same downstream searchableBox on all three meshes, from
(0.06, -0.005, -0.015) m to (0.16, 0.035, 0.065) m at refinement level 2.
Surface level 3, background sizes, physical domain, fluid, boundary conditions
remain as above. The controlled budget is now 1,000 SIMPLE iterations on every
mesh, with unchanged residual and conservation gates. The earlier 500-iteration
wake-refined trial is retained as an attention result because its fine mesh
missed the velocity residual gate. These meshes differ from historical
runs without wake refinement; compare within the new controlled three-mesh batch.

Nine requests now include a far-wake point at (0.12, 0.015, 0.020) m.
`flow_sampling.py` sorts the nearest 256 saved cell positions, retaining up to
two wall-visible supports in each coordinate octant. From these up to 16
supports it chooses the first nondegenerate enclosing tetrahedron in distance
order. Barycentric weights must be positive (within 1e-10 roundoff tolerance)
and are normalized after clamping roundoff negatives. Each support-to-request
segment is checked against actual bracket wall triangles. Unsupported points
are explicitly unavailable; they never fall back to a nearest-cell value.
A combined comparison requires all probes on all three meshes to be available.
Solver completion can still be retained when a probe is unavailable.

This custom interpolation is linear-exact for fields specified at the supplied
positions and cannot overshoot supporting values. It is not OpenFOAM native
cellPoint interpolation, a Delaunay mesh, or a volume-centroid reconstruction.
The supplied positions remain arithmetic mesh-vertex averages; distorted-cell
position errors and interpolation-stencil changes remain sources of uncertainty.
The finite wall visibility tests do not prove whole-tetrahedron fluid occupancy.
No boundary values or gradients are imposed by this interpolation.

Comparison schema `kcee.bracket-flow-refinement.v2` records identical requested
and evaluated coordinates, cell indices, support coordinates, positive weights,
maximum support radius in JSON, Markdown and CSV. Individual support distances
are also retained in JSON and Markdown.
The website shows support radius; historical v1 comparisons retain their
nearest-cell offset and are explicitly labeled. Normalizations are unchanged.
Both the source study manifest and comparison bind the sampling source hash.
Old studies and their immutable artifacts are preserved.

### Recorded native-bracket example (16 October 2026)

Comparison run: `8175a2cc-2cea-4fc8-9906-9cab5a66b8ae`.
Source STL SHA-256: `83b470851e2d35844eb62b3c485c0772fc502d4716ef0b77d47daad15427c385`.

| Mesh | Saved run | Cells |
|---|---|---|
| coarse | `0059a936-86ec-4300-82bd-49ea2cdf08c4` | 27157 |
| medium | `0e56170d-2e60-4812-aa15-63690c11e3ca` | 53379 |
| fine | `25687282-0dfe-4b02-aca4-605fa141c2af` | 93478 |

All solver execution gates and all finite bore-sampling gates passed. All nine
fixed-location probes were available on every mesh (27 records). Each mesh
used 1,000 iterations. The fine-mesh maximum final initial velocity residual
was 6.09112e-7, below the unchanged 1e-5 gate.

| Pair | Max velocity change / inlet | Max pressure change / inlet dynamic scale |
|---|---|---|
| coarse → medium | 3.75709% | 4.13796% |
| medium → fine | 1.09103% | 7.20483% |

The maximum normalized pressure change increases on the finer pair; these
results do not establish mesh independence. Passing solver/bore checks does
not turn these sensitivity measures into analytical error estimates or accepted
engineering results. Interpolation and source-position limitations above remain.

## Pressure verification and cell-center audit (version 3)

New studies use independently reconstructed volume centroids of triangulated
saved polyhedral cells. `flow_centres.py` triangulates each polygon face from
its vertex mean, forms signed tetrahedra about a cell-local reference, and
integrates signed volume and first moments. The owner uses the stored face
orientation; the neighbour reverses it. Negative tetrahedron contributions are
preserved for concave geometry. Nonpositive or nonfinite total cell volumes
are rejected. Local references avoid cancellation when coordinates are large.
Analytical tests cover a skew pyramid whose vertex average differs from its
volume centroid, coordinate translation, shared-face orientation and reversed
cell faces.

The independently integrated total fluid volume is compared with the saved
OpenFOAM checkMesh total. The new execution gate requires relative agreement
within 1e-6. This global check does not prove individual center accuracy.
On the previous 93,478-cell native-bracket mesh the relative difference was
3.84e-9; the RMS vertex-mean/volume-centroid shift was 0.22464 mm and the
maximum shift 1.74727 mm. These global shifts include transition cells and
must not be interpreted as bore-specific errors.

Each new solved field is sampled twice at the same nine physical requests:
once using the new volume-centroid positions and once using vertex averages.
The cell field values and actual wall triangles are identical in these two
calculations. `sampling_audit` records the historical-position probe supports,
availability and signed pressure differences (centroid minus vertex-average
basis), with absolute differences normalized by 0.5 U_inlet².
This isolates sensitivity to the position basis, including resulting support
selection and weight changes. It is not an analytical interpolation-error
estimate. Unavailable legacy samples are explicit, not replaced with zeros.

The new mesh recipe adds four searchable spheres of radius 5 mm centered on
(0.033, 0.015, 0.00175), (0.048, 0.015, 0.00175),
(0.00175, 0.015, 0.016) and (0.00175, 0.015, 0.030) metres.
Each uses inside refinement level 4; the downstream box remains level 2 and
ordinary surface refinement remains level 3. The nominal level-4 bore-region
sizes are 0.9375, 0.703125 and 0.5625 mm for coarse, medium and fine backgrounds.
Nominal bore size varies with the background grid and is retained per study;
controlled comparisons require the same sphere centers, radius and level.
Actual mesh counts, quality, bore ray intersections and solver residuals must
still be inspected. No prism layers are added.

All three cases now use the same 1,500 SIMPLE iterations, with unchanged
residual/conservation tolerances, physical domain, boundary conditions,
source geometry, viscosity and inlet speed. This batch must not be mixed
with historical recipes in a controlled three-mesh comparison. Comparison
schema `kcee.bracket-flow-refinement.v3` includes each source study's position
and same-field sampling audits. JSON and Markdown retain their details; the
CSV contains the new centroid-based probe values and interpolation supports.
The website exposes the position-basis audit and keeps older comparisons
clearly labeled. Both child and comparison manifests bind the centroid code.

Centroids describe the chosen triangulated saved polyhedron. Warped-face
triangulation may differ from OpenFOAM native face moments; this is not a
solver-exported C field. Custom positive tetrahedral probe interpolation and
finite wall-visibility checks retain the limitations described above.
Passing the new volume gate does not establish bore pressure accuracy, mesh
or domain independence, force convergence or engineering acceptance.

A comparison can also be rebuilt from already completed, registry-verified
current source studies using `scripts/rebuild_flow_comparison.py --parent
PARENT_UUID --studies COARSE_UUID MEDIUM_UUID FINE_UUID` inside the API
environment. It verifies each source's parent identity and manifest before
creating a new comparison. This avoids repeating CFD solves for a reporting
change and never modifies historical source studies or comparisons.


The initial bore-refined medium trial had one checkMesh skewness failure
(maximum 4.19005 against limit 4). A mesh-only native-geometry test using
`nSmoothPatch 5` and `nSmoothScale 8` reduced its maximum skewness to 3.71821.
The final controlled recipe uses these smoothing settings on every background
mesh, recorded under `inputs.mesh_smoothing`. Earlier attention studies remain
available; no quality threshold was relaxed. The nominal-size normalization in
comparison checks removes only the derived bore cell size, while sphere centers,
radius, refinement level, smoothing and iteration budget must all agree.

### Recorded pressure-verification batch (16 October 2026)

Comparison run: `2d0684c2-775d-463f-90e5-8297bb29fcbe`.
Source STL SHA-256: `83b470851e2d35844eb62b3c485c0772fc502d4716ef0b77d47daad15427c385`.

| Mesh | Run ID | Cells | Max skewness |
|---|---|---|---|
| coarse | `d8736786-4488-49c3-a664-324005833472` | 31949 | 3.75734 |
| medium | `3c2b1a4e-a687-4617-8116-890f3f6a6112` | 62081 | 3.71821 |
| fine | `96e006be-8b70-4b17-b1a1-9318daf4bf77` | 107699 | 2.52123 |

All solver execution gates, volume-agreement gates and finite bore-sampling
gates passed. All nine centroid-based physical probes were available on every
mesh, and all 27 records were verified against their source field values,
support coordinates and positive interpolation weights. Source and comparison
artifact hashes were verified.

| Pair | Max velocity change / inlet | Max pressure change / inlet dynamic scale |
|---|---|---|
| coarse → medium | 1.12882% | 2.40437% |
| medium → fine | 1.54391% | 2.53375% |

The final pressure differences are smaller than in the prior version-2 batch
but do not decrease monotonically across these refinements. Neither the
velocity nor pressure comparison establishes an asymptotic convergence trend.
Recipe, iteration budget and position basis changed between batches; this is
not a single-variable estimate of the benefit from bore refinement.

| Mesh | Global max position-basis pressure change / inlet dynamic scale | RMS center shift (mm) |
|---|---|---|
| coarse | 4.28509% | 0.42829 |
| medium | 4.22618% | 0.28024 |
| fine | 1.83549% | 0.20957 |

Position-basis changes are computed on identical fields within each study;
the maximum above includes all nine requests and is not a bore-only metric.
Mesh/domain independence, force accuracy and engineering acceptance remain
unestablished. Final implementation checks: 176 backend tests, 66 viewer unit
tests and 30 isolated end-to-end checks passed. Browser visual verification
was unavailable because automatic approval review reached a usage limit.

In the final batch, the largest pressure change is at the upstream probe on
both mesh pairs. Considering only the four bore probes, the largest normalized
pressure changes are 1.26975% (coarse to medium) and 1.39981% (medium to fine),
both at upright bore 2. These values also do not show a decreasing trend.

The subsequent controlled boundary-distance workflow and its pressure-reference
policy are documented in [bracket-flow-domain.md](bracket-flow-domain.md).

The combined far-domain spatial study and sensitivity plots are documented in
[bracket-flow-combined.md](bracket-flow-combined.md).
