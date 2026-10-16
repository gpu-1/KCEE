# Wake and below-bracket refinement

The website's **Refine wake & below** action compares four independently verified
OpenFOAM cases: medium and fine backgrounds, each with the baseline recipe and
with the versioned `wake-below-v1` profile. The action requires existing Compact
v1 medium/fine far-domain baseline cases; it reuses compatible cases only after
replaying their raw archives. Missing targeted cases are solved and registered.
Completed source cases remain available if a later calculation fails.

## Controlled recipe

All four cases use the same native PicoGK STL, far-domain bounds, boundary
conditions, steady laminar Re=6 flow, 1,500 SIMPLE iterations, level-3 bracket
surface, level-2 general wake box and level-4 bore spheres. Medium and fine
background counts remain 48×36×38 and 56×40×44. The targeted profile adds these
physical boxes to `snappyHexMesh`, with inside refinement level 3:

| Region | Minimum (m) | Maximum (m) |
|---|---|---|
| Wake | (0.065, −0.002, 0.002) | (0.135, 0.032, 0.038) |
| Below bracket | (0.015, 0.003, −0.030) | (0.045, 0.027, −0.010) |

The targeted cell limit is 250,000; runtime memory/CPU limits remain unchanged.
The nominal level-3 size is about 1.40625 mm on medium and 1.20536 mm on fine.
Actual snapped cells and transitions vary. Both boxes change together, and
snapping can alter topology outside them. This comparison cannot isolate each
box's contribution or establish an asymptotic error order.

Compact v1 sampling, nine fixed probes and within-case upstream pressure
subtraction are identical across the study. Velocity differences compare the
full velocity vector and normalize by inlet speed 0.01 m/s. Referenced kinematic
pressure differences normalize by ½U² = 0.00005 m²/s². See the
[versioned sampling explanation](cfd-sampling-versions.md) for interpolation
limits and historical compatibility.

## Evidence and interpretation

The result includes two matched comparisons: medium→fine for each profile, and
baseline→targeted for each background. The viewer shows both charts, all four
source cases, numerical checks and a probe selector with signed pressure minus
upstream, speed and interpolation support radius. Source buttons open the
individual field views. JSON, CSV, report and manifest downloads retain source
run IDs, source manifest hashes, STL hash and sampling metadata.

The API endpoint is `POST /runs/{native_design_id}/flow-local-refinement` with an
empty JSON body. Individual flow requests can specify
`local_profile: wake-below-v1`, but only with medium/fine, far domain, bore level
4 and Compact v1. Baseline reuse explicitly excludes targeted profiles, so new
local cases cannot silently enter ordinary domain or mesh comparisons.

The archive verifier regenerates the exact case dictionaries from the recorded
profile, verifies runtime and sampling metadata, and reproduces diagnostics from
saved mesh and fields. Relabeling a targeted archive as baseline is rejected.
Derived manifests bind the full result, source evidence, CSV and report.

Passing mesh, residual, mass conservation and finite bore-ray gates is necessary
for this exploratory comparison. It does not prove hydraulic area, wall-force
accuracy, mesh/domain independence or engineering acceptance. There are no
prism layers. The centroid reconstruction and bounded candidate interpolation
are custom postprocessing, not native OpenFOAM sampling. Upstream-reference
boundary sensitivity remains an open limitation.

## Recorded verification (16 October 2026)

Final comparison: `6a43a100-1369-42e1-9c13-a1130be72344`.
Native parent: `2fa09ea6-4874-4401-ad53-1269fb21426a`.
Source STL SHA-256:
`83b470851e2d35844eb62b3c485c0772fc502d4716ef0b77d47daad15427c385`.

| Background / profile | Cells | Source run |
|---|---:|---|
| Medium baseline | 113,665 | `33126ea2-3a2c-4c8a-ad80-4fa0e648ebdb` |
| Fine baseline | 162,811 | `7a5f1f1c-b2e6-49ca-9450-ce713e9278d0` |
| Medium targeted | 150,695 | `d2991c00-e153-47cc-9be6-8a447cbb3f08` |
| Fine targeted | 221,723 | `8adfb893-d067-42c4-b991-6ec53f74829e` |

| Comparison | Maximum velocity change / inlet | Maximum referenced pressure change / ½U² | Largest pressure probe |
|---|---:|---:|---|
| Baseline medium → fine | 1.33651% | 3.46127% | Wake |
| Targeted medium → fine | 1.34014% | 3.42376% | Below |
| Medium baseline → targeted | 0.07929% | 0.63080% | Below |
| Fine baseline → targeted | 0.37967% | 0.43063% | Base bore 2 |

All four solver and bore-opening gates passed. Added cells alone did not resolve
the sensitivity: the maximum referenced pressure mesh difference changed only
slightly, and the maximum velocity difference increased slightly. The below
probe's pressure mesh difference increased from 3.13303% to 3.42376%, while its
velocity-vector difference decreased from 0.58950% to 0.16990%. The wake pressure
mesh difference changed from 3.46127% to 3.41438%. The global velocity maximum
remains at the upstream reference probe. No threshold-based acceptance or mesh
independence is claimed.

The original baseline manifest hashes were checked against the previous Compact
v1 verification receipt. The two new PDE solves were raw-replayed before
registration. Independent final checks verified all six manifests (parent, four
sources and comparison), all probe weights/positions/field arithmetic, all four
matched comparison maxima and all 36 CSV rows. Cross-platform recomputed floats
use relative tolerance 1e−12 and absolute tolerance 1e−15; file hashes are exact.
Evidence is retained under `.local/verification/local-refinement/`, including
`verification-receipt.json` and `verify_final.py`. Registered report and exports
are under `runs/6a43a100-1369-42e1-9c13-a1130be72344/`.

Validation: 211 backend tests, 79 viewer tests and 30 isolated integration checks
passed. The website was checked with the actual saved comparison, including
Compact v1 labeling, both charts, four source cases, probe selection and exports.

See [pressure contrasts and targeted boundary sensitivity](cfd-pressure-reference.md) for local probe differences, signed reference decomposition and the additional outer-domain comparison.

See [the fine outer-domain extension](cfd-fine-outer.md) for the targeted 2×2 comparison, explicit fine-grid audit and signed interaction.
