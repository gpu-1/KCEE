# Bracket-flow boundary-distance study

The fixed domain study changes the external boundary distances while holding
medium background spacing, nominal local refinement, fluid properties, source
STL, solver settings and physical probe requests constant. It is separate from
the background-mesh study described in [bracket-flow.md](bracket-flow.md).

## Controlled recipe

| Domain | Background cells | Minimum x/y/z (mm) | Maximum x/y/z (mm) |
|---|---|---|---|
| base | 32 × 20 × 22 | -120 / -90 / -100 | 240 / 120 / 140 |
| expanded | 40 × 28 × 30 | -165 / -132 / -143.63636 | 285 / 162 / 183.63636 |
| far | 48 × 36 × 38 | -210 / -174 / -187.27273 | 330 / 204 / 227.27273 |

Background spacing is 11.25 / 10.5 / 10.90909 mm. Each successive domain adds
four background cells at each face. This keeps the nominal spacing and grid
alignment fixed, instead of enlarging the same cell counts and inadvertently
coarsening the bracket region. Inputs retain unrounded floating-point bounds;
case vertices use 15 significant digits. Floating-point meshing and snapping
can still change individual cells near the bracket.

The source remains the default native PicoGK 60 × 30 × 40 mm bracket with
3.5 mm plates and four bores. Surface level 3, downstream box level 2, four
5 mm radius bore regions at level 4, nSmoothPatch 5 and nSmoothScale 8 are
unchanged. The fixed medium nominal bore target is 0.703125 mm. There are no
prism layers. Inlet speed is 0.01 m/s, kinematic viscosity 0.0001 m²/s and
Reynolds number 6 based on 60 mm. The inlet is uniform +x, sides slip, bracket
no-slip, and outlet kinematic pressure zero. Each case uses 1,500 SIMPLE
iterations with unchanged residual, conservation, mesh-quality and volume gates.

## Pressure-reference control

The outlet zero-pressure plane moves between cases. Directly comparing raw
pressures can therefore conflate spatial differences with pressure-reference
shifts. For every case and physical probe, the reported comparison value is

    p_kinematic(probe) - p_kinematic(upstream)

The upstream reference is fixed at (-30, 15, 20) mm. This removes a uniform
pressure shift; it does not remove physical boundary influence on the upstream
probe. Raw pressure and the actual upstream reference value are retained next
to the difference in CSV and JSON. The reference probe's difference is zero
by definition, which is not evidence of convergence at that point.

Successive velocity-vector changes use the 0.01 m/s inlet for normalization.
Successive referenced-pressure changes use 0.5 U² = 0.00005 m²/s². Values are
kinematic pressure differences, not Pa. These are sensitivity measures, not
analytical errors or engineering acceptance criteria.

All nine requests retain the positive tetrahedral interpolation supports,
weights, support radii and independently reconstructed triangulated-cell volume
centroids. The reconstruction and visibility limitations of the mesh study
still apply. Exact OpenFOAM native C fields are not exported.

## Execution and provenance

`POST /runs/{native-parent-id}/flow-domains` accepts an empty body only. It
uses the fixed three-domain sequence at medium resolution. The internal
worker permits only named recipes. Expanded domains use medium resolution;
the far domain also permits the bounded coarse/fine recipes documented in
[bracket-flow-combined.md](bracket-flow-combined.md).

A compatible saved base case can be reused. Before reuse, its registry record
and artifact hashes are checked; the current fixed dictionaries and source STL
must match the archived case byte for byte, and diagnostics/probes are
recomputed from raw mesh, fields and logs. A matching current base case avoids
repeating its solve. Reused status, original run ID and manifest hash are
recorded. Historical incompatible recipes are not treated as equivalent.

New domain cases are individually registered and retain meshes, case files,
fields, logs, source hashes, solver gates, bore samples and position audits.
The separate `bracket_flow_domain` comparison binds all three source run IDs,
manifest hashes and the original parent manifest. Schema
`kcee.bracket-flow-domain.v1` contains common settings, exact domain bounds,
background counts and spacing, boundary clearances, referenced probe values,
source reuse and successive changes. Report Markdown, JSON and 27-row CSV
are available together. Earlier completed cases survive a later failure.

The website provides **Check boundary distances**, case-specific field links,
clearances, mesh settings, execution checks, a referenced-pressure probe table
and report exports. Source field views retain raw outlet-referenced pressure;
the domain comparison labels the pressure subtraction explicitly.

## Interpretation limits

Actual snapped cells can change even though nominal resolution and alignment
are controlled. Domain changes remain entangled with local meshing and
interpolation differences at finite resolution. The earlier mesh study also
did not establish mesh independence. No asymptotic convergence order,
Richardson extrapolation, force accuracy, accepted domain independence,
service-condition validity or engineering acceptance is asserted.

## Recorded native-bracket domain study (16 October 2026)

Comparison run: `e78d8158-c6e4-4bc6-be0d-d2f75b6c7fd0`.
Source STL SHA-256: `83b470851e2d35844eb62b3c485c0772fc502d4716ef0b77d47daad15427c385`.

| Domain | Run ID | Cells | Reused verified case |
|---|---|---|---|
| base | `3c2b1a4e-a687-4617-8116-890f3f6a6112` | 62081 | True |
| expanded | `075dbc6f-67c8-4932-ad1f-ece8df803aa9` | 81601 | False |
| far | `2c7d216e-68a2-4ea5-90f6-829b11ce66c2` | 113665 | False |

All solver, mesh-quality, reconstructed-volume and finite bore gates passed.
All nine fixed-coordinate probes were available in every case. All three
source registry records, manifests and artifacts were verified, together with
the new comparison and 27 exported probe records. The API returned HTTP 201.

| Pair | Max velocity-vector change / inlet | Max referenced-pressure change / inlet dynamic scale |
|---|---|---|
| base → expanded | 4.14560% | 11.52641% |
| expanded → far | 1.72700% | 4.17691% |

The successive differences decrease, but the largest domain still differs
from the expanded case by 4.17691% of inlet dynamic scale in referenced
pressure. No acceptance threshold was predeclared, and no asymptotic or
combined mesh/domain-independence result is established. All six boundaries
move together; individual inlet, outlet and lateral boundary influences are
not isolated by this study.

Validation: 181 backend tests, 68 viewer unit tests and 30 isolated end-to-end
checks passed. Browser visual verification was not repeated because the earlier
automatic approval review had reached a usage limit. Backend API execution,
raw-case recomputation, registry and export checks were completed independently.
