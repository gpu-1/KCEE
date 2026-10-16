# Versioned CFD probe sampling

New bracket-flow requests use **Compact v1**, stored as `compact-radius-v1`.
The worker records the complete sampling recipe in `sampling.json` inside the
solver archive. The result records it as `sampling`, with the version also in
`inputs.probe_sampling` and the source manifest. The API requires the returned
version to match the request and independently reproduces the diagnostics from
the raw archive under that declared version. Changing a label without matching
archive metadata or probe methods is rejected.

The candidate pool remains the nearest 256 cell locations, with at most two
wall-visible candidates per coordinate octant, up to 16 total. Compact v1
selects an enclosing nondegenerate tetrahedron by minimum maximum support
radius, then minimum summed support distances, then the original cell-ID tuple.
The four nonnegative normalized weights reproduce the requested point. There is
no nearest-cell fallback or extrapolation. This is a bounded-candidate optimum,
not a search over every possible four-cell combination in the entire mesh.

The position basis remains independently reconstructed volume centroids of
triangulated saved polyhedra. Neither these positions nor the probe interpolator
are native OpenFOAM sampling. Finite probe-to-cell wall-visibility rays do not
prove that the whole supporting tetrahedron is inside the fluid.

## Historical compatibility

Compatible unversioned 1,500-iteration, centroid-based archives retain
`first-enclosing-v1` behavior when replayed. The absent declaration is interpreted
as that historical recipe, never as Compact v1. Explicit legacy requests may
also use `sampling_version: first-enclosing-v1`; new requests default to compact.
Older nearest-cell, vertex-mean and 500/1,000-iteration reports retain their
recorded values and artifact verification, but are not interchangeable with the
current raw replay/mesh/domain recipe. Existing reports and archive files are
never rewritten. The viewer labels unversioned history using its saved report.

All mesh, domain and combined summaries require one consistent sampling version.
Compact metadata and probe method labels must agree. Domain schemas advance to
`kcee.bracket-flow-domain.v2`, combined schemas to
`kcee.bracket-flow-combined.v2`, and base-domain mesh summaries to
`kcee.bracket-flow-refinement.v4`. Historical schemas remain readable.

New compact base-mesh comparisons subtract their fixed upstream probe, matching
the existing domain/combined pressure-reference policy. Their table, CSV and
report distinguish raw pressure from pressure minus upstream. Historical mesh
comparison schemas retain their original raw outlet-referenced policy.
CSV exports and comparison manifests expose the sampling version; reports record
the full recipe and source manifests. The viewer shows **Sampling: Compact v1**
for new production studies and retains historical labels for original studies.

## Recomputing comparisons from unchanged solver fields

Only postprocessing changed: fluid, source STL, mesh dictionaries, boundary
conditions and saved PDE fields remain fixed. The migration command therefore
reuses solver output only after verifying its source registry record, parent
identity, manifest, source surface, exact case dictionaries and raw diagnostics.
It creates new source study IDs, recomputes centroid/vertex-mean probe audits
under Compact v1, and verifies the new archive/result again before registration.

Each new source manifest and requirements record `sampling_origin`: original
run ID, manifest hash, original solver-archive hash, original sampling version,
operation and `solver_reexecuted: false`. Every raw member is preserved byte for
byte except the new sampling declaration. The new archive has its own hash.
Raw cell fields and source geometry remain unchanged. New source and comparison
reports make this a postprocessing recomputation, not another CFD solver run.

Inside the API environment, with its registry and `/data/runs` available:

```
PYTHONPATH=/app python scripts/resample_flow_studies.py --combined ORIGINAL_COMBINED_RUN
```

Stage the command into the API container if the script is not installed there.
The command verifies the original combined and embedded domain evidence,
recomputes five unique source cases, creates a new three-domain comparison and
creates a new three-mesh far-domain comparison. The exact new medium/far run ID
and manifest are shared between both comparisons. Completed source cases remain
registered if a later step fails. This command does not repeat the PDE solver.

Normal website/API workflows also use Compact v1. Domain studies reuse compatible
verified medium base/expanded/far cases; combined studies require a compact
domain study and reuse compatible far-domain coarse/fine cases. Every reused
archive is reverified. Missing compatible cases are solved with the new default;
legacy cases cannot silently enter a new comparison. Reuse does not change the
recorded validation status or establish physical accuracy.

## Interpretation

The earlier pressure study identified sensitivity at the **upstream reference**:
using a more compact stencil on the saved original fine case changed that
reference enough to shift all referenced bore pressures, while the raw pressure
at upright bore 1 stayed unchanged. Consistent interpolation removes that method
mixture from comparisons; it does not prove that the new sampling is exact.

Sensitivity is still normalized by inlet speed 0.01 m/s and kinematic dynamic
scale 0.00005 m²/s². No analytical pressure error, Richardson order, acceptance
threshold, native bore-sampling proof or joint mesh/domain error bound is added.
The prior finer-bore study remains separate evidence with its recorded limits.

## Recorded verification (16 October 2026)

The migration used original combined run
`180ee968-e26d-4f10-9095-8e2316f5be4d`. Five unchanged raw solver cases produced
new Compact v1 source runs. Both normal API endpoints were then exercised and
reused the compatible sources after raw replay; neither endpoint needed another
PDE solve.

Final API domain comparison: `e2174256-5bda-484c-ad92-608043ddcf81`.
Final API combined comparison: `7bbe2b82-916b-473d-a9d4-66417c416d19`.
Their exact shared medium/far source is
`33126ea2-3a2c-4c8a-ad80-4fa0e648ebdb`.
The migration's earlier domain/combined reports remain separate immutable runs.

| Comparison sequence | Pair | Velocity change / inlet | Referenced pressure change / ½U² |
|---|---|---|---|
| Far-domain mesh | Coarse → medium | 1.21760% | 4.30967% |
| Far-domain mesh | Medium → fine | 1.33651% | 3.46127% |
| Medium-mesh domain | Base → expanded | 4.14560% | 11.53018% |
| Medium-mesh domain | Expanded → far | 1.72700% | 4.17856% |

The prior historical medium-to-fine headline was 7.01954% with first-enclosing
interpolation. Under consistent Compact v1 it is 3.46127%. This is a changed
sampling comparison on unchanged solver fields, not a demonstrated reduction in
physical error. The velocity mesh differences do not decrease on the finer pair.
Mesh, domain and joint independence remain unestablished.

One **fresh PDE solve** also completed through the normal API with an empty
request body, demonstrating the Compact v1 default end to end:
`86e0a745-6e75-4256-b1e7-f5484dae047e`, coarse/base, 31,949 cells.
All its solver, mesh-quality, reconstructed-volume and finite bore-opening checks
passed; its archive contains the compact sampling declaration. This is still an
exploratory Re=6 case, not engineering validation.

A separate base-domain mesh comparison exercised schema v4 and the updated
pressure-reference CSV/table:
`42477ddb-8c8e-4ec3-9fb9-5d46f979f2cc`. It uses the fresh coarse solve, the
recomputed medium/base source `20786e80-6c31-4be3-8867-c8a34d386200`, and a
sixth recomputed source, fine/base
`2767a05d-9844-402d-ac72-82f92737ef46`. The latter preserves raw source
`96e006be-8b70-4b17-b1a1-9318daf4bf77`. There are seven unique Compact v1 cases
in the checked source set: six postprocessing recomputations and one fresh
solver run.

Independent checks verified original and new registry/manifest hashes, source
lineage, unchanged geometry and field CSV hashes, and every original raw archive
member byte for byte. New sampling declarations, nonnegative normalized weights,
source-cell interpolation arithmetic, shared medium/far identity and pressure
subtraction were checked. Final CSVs contain 54 combined context rows, 27 domain
rows and 27 base-mesh rows, each explicitly tagged with the sampling version.
Evidence is under `.local/verification/sampling/`, including the verification
receipt, raw-replay logs and browser screenshot.

Validation: 205 backend tests, 77 viewer tests and 30 isolated end-to-end checks
passed. Browser review confirmed the new compact label and both plots, original
historical labels, and the base-mesh upstream-pressure table label. The sidebar
layout fix remains in place. Select **CFD verification 7bbe2b82** to review the
new combined result; its CSV, JSON and Markdown report are available there.
