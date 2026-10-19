# Bracket pressure loads and wall-shear estimates

This documents the historical one-sided estimator. A separate [native full-stress workflow](native-bracket-forces.md) now resolves the function-object runtime issue and compares full viscous loads with these unchanged estimates.

The website's **Calculate wall loads** action creates a registered derived study
from saved OpenFOAM fields. Select a bracket-flow case for one source case, or
its native design / mesh-domain comparison for the fixed six-case comparison:
baseline medium/fine far, targeted medium/fine far, targeted medium/fine outer.
The six compatible Compact v1 source cases must already exist; otherwise the
job gives an actionable error rather than launching unrequested solver cases.
Progress, cancellation, retry and saved-source links use the CFD job panel.
Existing registered cases are read and reverified, never rewritten.

## Method and SI conventions

Method version: `wall-face-traction-v1`.

The saved `bracket` patch has zero wall velocity and zero normal pressure
gradient. Each wall pressure therefore equals its owner-cell kinematic
pressure. With `Sf` pointing out of the fluid into the body, fluid-on-solid
pressure force is `rho * p_kinematic * Sf`. Density converts m²/s² to Pa;
forces are N. Uniform pressure offsets cancel on the closed bracket surface.

Polygon faces use an oriented vertex-mean triangle fan. Area vectors and
pressure moments are summed over triangles, including signed contributions on
concave faces. Pressure moments integrate each triangle's centroid cross area
vector, rather than replacing a warped face with a single flat polygon.
Moment origin is the source origin `(0,0,0)` m, and moments are N·m.

Viscous load is a **one-sided tangential wall-shear estimate**,
`mu * A * U_owner,t / d_normal`, where `mu=rho*nu` and `d_normal` is the positive
normal distance from independently reconstructed owner-cell volume centroid to
the face. Its moment uses the reconstructed face centroid. Normal viscous
traction and nonorthogonal corrections are omitted. No slip velocity is added.
The saved source geometry, centroid recipe and highly nonorthogonal wall cells
limit this estimate; minimum distance and maximum wall nonorthogonality are
reported. Absence of prism layers is a material limitation.

The installed pinned OpenFOAM 1912 runtime failed while initializing its native
force function object (`IOstream "sha1"`). This implementation does not patch
that runtime or claim native stress-tensor results. It uses the independently
implemented, explicitly labelled estimator above. The native definition is
provided for comparison in [OpenFOAM's force documentation](https://doc.openfoam.com/2306/tools/post-processing/function-objects/forces/forces/).

Total load and moment combine pressure with the viscous estimate, so **total
loads and coefficients are estimates too**. Coefficients use the declared
0.03×0.04 = 0.0012 m² bracket envelope area and `0.5*rho*U²*Aref`; it is not the
measured mesh silhouette. Existing exploratory Re=6 conditions remain fixed:
U=0.01 m/s, rho=1 kg/m³, nu=0.0001 m²/s. These small loads are unrelated to the
separate 100 N structural demonstration load.

## Independent analytical checks

A closed unit box in an affine pressure field checks signed pressure force,
density conversion and moments against exact volume integrals. A uniform
pressure offset checks cancellation on a closed surface. Plane Poiseuille's
quadratic analytical velocity profile checks wall-shear estimates at 8, 16 and
32 cells. Its relative force errors are 6.25%, 3.125% and 1.5625%, with observed
first-order differences, as expected for this one-sided derivative.

This is an integration/derivative benchmark on analytical fields, **not a new
OpenFOAM benchmark, independent solver validation or bracket wall-shear
accuracy assessment**. Source solver checks and bore gates are reported
separately. Surface vector and moment closure are internal checks, not force
convergence criteria.

## Website, exports and replay

The result view provides signed x/y/z pressure, viscous-estimate and
estimated-total force/moment charts, numerical tables, a source-case selector,
source links, comparison tables, benchmark results, CSV, JSON and a readable
report. Comparisons retain signed vector changes; near-zero components are not
used as percentage denominators. Fine far→outer includes the previously
recorded small grid spacing/alignment changes; it is not isolated boundary
sensitivity. Mesh/domain independence and engineering acceptance remain
unestablished. There is no automatic force transfer to structural FEA.

`POST /runs/{id}/flow-forces` creates the same fixed study synchronously;
`POST /cfd-jobs` with `kind:"forces"` is the website background workflow.
`GET /runs/{id}/force-verification` re-verifies source registry/manifests and
raw solver fields, then reproduces the wall-load calculation and comparison.
**Reproduce force evidence** exposes this in the viewer. It verifies evidence
reproducibility; it does not approve engineering use.

Registered manifests bind the parent design, every source run/manifest/archive,
implementation hashes and every derived artifact. `verification.csv` contains
three component rows per source with force, moment and coefficient values;
`cfd.json` / `result.json` also contain geometry diagnostics, bounded wall-face
samples, the analytical benchmark and comparisons. These derived runs use the
existing verified backup format. Source runs must accompany a migration for
raw-evidence replay; a derived report alone is not a complete source backup.

## Recorded verification — 19 October 2026

Registered six-case result: `61d76363-59ae-4b30-98bf-890f856f13f5`.
Manifest SHA-256:
`8b826e05248088f5f6eb4c678b79f5e1641f7129a8db245165c95b86cd830e07`.
The website cancelled job `2b01a57c` after three source cases were checked;
Retry created `8f1738c1`, which reused and reverified all six source cases and
completed the registered report. No additional solver case was required.

All analytical, source-solver, bore and internal force checks passed. For the
fine targeted outer case, x pressure force is about 2.920641e−7 N, x viscous
estimate 2.810275e−7 N and x total estimate 5.730916e−7 N. These are the existing
illustrative low-speed conditions, not a prediction at service conditions.
Maximum reported wall nonorthogonality is about 87.7°; this is measured using
the custom reconstructed owner-to-wall geometry and is distinct from native
`checkMesh`'s metric. It reinforces the stated shear-estimator limitation.

The 18 CSV component rows, five signed comparison vectors and all eight prior
fine outer-domain manifest hashes were independently checked. Regression
validation passed 244 backend tests, 88 viewer tests and 31 isolated service
integration checks. The isolated test creates a clearly labelled synthetic
hole-free L fixture to exercise force-job registration, raw replay, CSV and
tamper detection; it is not presented as PicoGK geometry validation. Browser
checks cover cancellation/retry, case switching, force/moment switching and
signed charts. Local receipts, logs and screenshots are in
`.local/verification/cfd-forces/`.
