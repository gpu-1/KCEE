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
