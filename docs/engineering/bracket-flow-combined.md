# Combined CFD mesh and domain verification

This workflow connects the fixed-medium boundary-distance study with mesh
refinement inside its largest domain. It adds two solves, reuses the exact
verified medium/far case and keeps the original domain comparison immutable.
It does not repeat the entire Cartesian matrix of mesh sizes and domains.

## Fixed-domain spatial sequence

All three mesh cases use the same far-domain bounds in metres:
minimum (-0.21, -0.174, -0.18727272727) and maximum
(0.33, 0.204, 0.22727272727). Stored inputs retain full floating precision.

| Mesh | Background cells | Largest background spacing (mm) | Nominal near-surface size (mm) | Nominal bore size (mm) |
|---|---|---|---|---|
| coarse | 36 × 25 × 28 | 15.12000 | 1.89000 | 0.94500 |
| medium | 48 × 36 × 38 | 11.25000 | 1.40625 | 0.703125 |
| fine | 56 × 40 × 44 | 9.642857 | 1.205357 | 0.602679 |

The counts are deliberately bounded for local execution and refinement ratios
are not uniform. No asymptotic convergence order is fitted. The source bracket,
fluid properties, boundary types, source-relative local refinement regions,
smoothing settings and 1,500 SIMPLE iterations are fixed. Actual mesh quality,
volumes, residuals, boundary fluxes and finite bore rays are still checked.

The fine/far case has a 200,000 local-cell budget; the global cell cap and
accepted field count remain 200,000. Other cases retain the 150,000 local-cell
budget. These are capacity ceilings, not target discretization sizes. Worker
memory is bounded at 2 GiB and temporary storage at 512 MiB. Solver execution
is bounded at 900 seconds per case. Archive, unpacked archive and response
limits are 36, 192 and 96 MiB respectively. Read-only worker roots and local
network isolation remain in place.

## Shared pressure reference and source identity

Both sensitivity sequences use kinematic pressure at a physical probe minus
kinematic pressure at the fixed upstream probe (-30, 15, 20) mm. The
normalization is 0.5 U_inlet² = 0.00005 m²/s². Velocity-vector differences
are normalized by inlet speed 0.01 m/s. Moving an outlet pressure reference
therefore cannot alone create a referenced-pressure difference. Physical
boundary effects at the reference probe can still affect the result.

The combined report requires the medium/far mesh row to reference exactly
the same run ID and manifest hash as the largest-domain row in the domain
comparison. Before reuse, source registry records and hashes are verified,
current case dictionaries/source surface are compared with the archive and
all medium/far diagnostics are recomputed from raw fields, mesh and logs.
Different physical settings, local refinement recipes, pressure references,
source surfaces or fixed-domain bounds are rejected.

## Interface, plots and exports

`POST /runs/{native-parent-id}/flow-combined` accepts an empty body only. A
compatible registered domain comparison must already exist. Completed source
cases remain registered if a later solve or comparison fails.

The website provides **Combined CFD verification**, case-specific field
links, the original domain-evidence link, probe values, numerical gates and
two sensitivity plots. The first plot shows coarse-to-medium and
medium-to-fine differences in the far domain. The second retains the original
base-to-expanded and expanded-to-far domain differences at medium resolution.
Axes show linear percentages; true zero differences remain zero. Curves are
not analytical errors, convergence-order fits or acceptance thresholds.

The new `bracket_flow_combined` run binds source IDs/hashes, the domain
comparison ID/hash, actual counts, bounds, settings, interpolation supports,
pressure references, bore checks and original unaltered domain report. Schema
`kcee.bracket-flow-combined.v1` is exported as JSON together with Markdown
and CSV. The CSV contains 54 context rows: 27 far-mesh and 27 domain rows.
The shared medium/far case intentionally appears in both contexts, giving
45 unique case/probe evaluations across five unique solver cases.

## Interpretation

This crossed subset of studies does not establish joint mesh/domain
independence or a combined error bound. The domain study uses medium
resolution; the spatial study uses the far domain. Additional combinations
could change either trend. Residual/mesh/bore gates establish execution and
sampling checks, not engineering acceptance. The same centroid-reconstruction,
custom interpolation, finite bore-ray, no-prism-layer and exploratory Re=6
limitations documented in the earlier studies still apply.

## Recorded native-bracket combined study (16 October 2026)

Combined run: `180ee968-e26d-4f10-9095-8e2316f5be4d`.
Domain comparison: `e78d8158-c6e4-4bc6-be0d-d2f75b6c7fd0`.
Source STL SHA-256: `83b470851e2d35844eb62b3c485c0772fc502d4716ef0b77d47daad15427c385`.

| Far-domain mesh | Run ID | Cells | Reused |
|---|---|---|---|
| coarse | `d64aca19-7f31-49cf-ac4f-7cde687ce032` | 50530 | False |
| medium | `2c7d216e-68a2-4ea5-90f6-829b11ce66c2` | 113665 | True |
| fine | `c88dbfb9-d355-4a35-90df-c8c7257d5a81` | 162811 | False |

All far-mesh solver, mesh-quality, reconstructed-volume and finite bore
gates passed. Every original domain gate also passed. The shared medium/far
run ID and manifest hash match exactly, and its raw case and diagnostics
were reverified before reuse. Source and combined artifacts, original domain
report text, pressure subtraction and interpolation supports were verified.

| Far-mesh pair | Max velocity change / inlet | Max referenced-pressure change / inlet dynamic scale |
|---|---|---|
| coarse → medium | 1.29439% | 4.54508% |
| medium → fine | 2.24735% | 7.01954% |

The far-domain mesh differences increase on the finer pair. The largest
medium-to-fine referenced-pressure change is 7.01954% of inlet dynamic scale,
and the velocity-vector change is 2.24735% of inlet speed. This does not
establish a decreasing spatial trend. The retained domain result is 4.17691%
referenced-pressure change and 1.72700% velocity change on its last pair.
These are different sensitivity sequences, not quantities that can be added
or combined into a justified joint error bound.

All 54 CSV context rows (45 unique case/probe evaluations across five unique
solver cases) were checked against source values and pressure references.
Validation: 186 backend tests, 70 viewer unit tests and 30 isolated end-to-end
checks passed; the combined API returned HTTP 201. Browser visual verification
was not repeated after the earlier automatic approval-review usage-limit
failure. SVG chart arithmetic and zero/nonfinite handling were unit-tested.
Mesh, domain and joint independence and engineering acceptance remain
unestablished.
