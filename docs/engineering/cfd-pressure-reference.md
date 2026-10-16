# Pressure contrasts and targeted boundary sensitivity

**Pressure reference study** creates a new, immutable comparison using the four
Compact v1 wake/below cases and one new targeted medium outer-domain case.
Existing cases are reused only after raw archive replay. The new case retains
the same native PicoGK STL, fixed physics, bore level 4, physical refinement
boxes, surface levels and 1,500 SIMPLE iterations.

## Controlled boundary expansion

The medium far domain uses 48×36×38 background cells. The outer domain uses
56×44×46, extending every boundary by four original background cells. This
preserves background spacing and integer-cell alignment; nominal local cell
sizes remain fixed. All non-domain case dictionaries remain byte-identical.
The 250,000-cell and existing worker resource limits remain unchanged. Actual
snapped cells and topology can change, so this is a discrete domain sensitivity
comparison. Only medium resolution is expanded; it is not a complete mesh/domain
Cartesian study.

## Gauge-invariant comparisons

All pressure values are kinematic, in m²/s². Percent changes divide by the same
inlet scale ½U² = 0.00005 m²/s², not by the local pressure value.

The previously used field is `p(probe) − p(upstream)`. The new study also records
`p(probe) − p(above)`, with the above probe fixed at (0.030, 0.015, 0.060) m.
For any two source cases A and B:

```
Δ[p(probe) − p(upstream)]
  = Δ[p(probe) − p(above)] + Δ[p(above) − p(upstream)]
```

Every signed probe change is exported with both terms and its closure residual.
This identity is algebraic. It cannot uniquely assign physical error to the
reference, boundaries or local region. The above sample can itself be affected
by boundaries, discretization and interpolation. Both referenced fields are
invariant under a uniform pressure offset within either case. Raw
outlet-referenced pressure and raw upstream pressure are retained as diagnostics,
not interpreted as cross-domain physical pressure errors.

Four predeclared local contrasts provide additional gauge-invariant evidence:

| Contrast | First probe minus second probe |
|---|---|
| Wake gradient | Wake − far wake |
| Below vs above | Below − above |
| Base bores | Base bore 2 − base bore 1 |
| Upright bores | Upright bore 2 − upright bore 1 |

The chart compares maximum changes across the upstream-referenced probes, the
above-referenced local field and these four contrasts. The local-field maximum
excludes the upstream probe because that is explicitly the reference relation
being separated; the above probe is zero by construction. The local-pair
maximum covers only the selected four pairs. These maxima have different sample
sets and are not interchangeable error norms.

## Workflow and provenance

Three case pairs are compared: baseline far-domain medium→fine, targeted
far-domain medium→fine, and targeted medium far→outer. The website shows source
cases, numerical checks, a comparison selector, a signed probe decomposition,
local contrast changes, velocity sensitivity and CSV/JSON downloads. The saved
Markdown report includes all source IDs and hashes, full inputs, probe supports
and limits. The manifest binds every exported artifact and the source parent.

API: `POST /runs/{native_design_id}/flow-reference-study`, with an empty body.
The four original wake/below cases must already exist and pass their reuse
checks. The outer case is solved only if no compatible verified source exists.
Completed sources remain saved if a later step fails. Existing reports and
fields are not rewritten.

The study preserves [Compact v1 sampling](cfd-sampling-versions.md) and the
[wake/below profile](bracket-flow-local-refinement.md). Finite bore rays,
custom triangulated-polyhedron centroids, bounded candidate interpolation,
absent prism layers and exploratory steady laminar Re=6 flow retain their
limits. Mesh independence, domain convergence, wall-force accuracy and
engineering acceptance remain unestablished.

## Recorded verification (16 October 2026)

Final comparison: `1f6be6a4-429b-4100-badb-4e39ed7c0a93`.
Outer targeted medium source: `d07bda94-a652-4f88-a81e-4f30054fb350` with 198,375 cells.
The original targeted far medium case has 150,695 cells.

| Comparison | Upstream-reference max | Above-reference local max | Above−upstream term (signed) | Selected local-pair max | Velocity / inlet max |
|---|---:|---:|---:|---:|---:|
| Baseline mesh | 3.46127% | 2.73395% | 2.52949% | 1.75168% | 1.33651% |
| Targeted mesh | 3.42376% | 2.73887% | 2.51456% | 1.70896% | 1.34014% |
| Targeted far → outer | 1.95876% | 1.23665% | 1.81874% | 0.23972% | 0.84183% |

All solver, bore-opening, grid-alignment and decomposition checks passed.
The targeted mesh comparison still changes selected local contrasts by up to
1.70896%; the mesh variation cannot be described solely as a uniform reference
shift. In the medium far→outer comparison, the maximum upstream-referenced
change is 1.95876%, at wake. At that probe the decomposition is a +0.14002%
above-referenced change plus a +1.81874% above−upstream change. This identifies
an algebraic reference component; it does not identify an exact physical error.
The above-referenced local-field maximum is 1.23665%, at upright bore 1, while
the four selected local contrasts change by at most 0.23972% (below−above).
Different maxima cover different probe sets and must not be combined or
interpreted as equivalent error norms.

The new boundary pair is smaller in several diagnostics than the earlier
medium expanded→far baseline-domain pair, but its local refinement recipe is
different. It is not another point on that unchanged sequence and does not
establish domain convergence. A matched additional domain and finer-resolution
domain evidence would be needed before any independence claim.

The final evidence verifier checked seven manifests (parent, five sources and
comparison), exact original source hashes, unchanged non-domain case
dictionaries, fixed sampling/runtime metadata, saved probe interpolation,
all local contrasts, signed decomposition closure and all 39 CSV rows.
Cross-platform floating-point checks use relative tolerance 1e−12 and absolute
tolerance 1e−15; artifact hashes remain exact. Evidence is retained under
`.local/verification/reference-boundary/`, including `verification-receipt.json`
and `verify_final.py`. The registered report and exports are under
`runs/1f6be6a4-429b-4100-badb-4e39ed7c0a93/`.

Validation: 216 backend tests, 82 viewer tests and 30 isolated integration checks
passed. Invalid request checks returned 422 without starting solver work. The
actual website study was checked for charts, source cases, domain comparison
selection, signed tables and export links.

See [the fine outer-domain extension](cfd-fine-outer.md) for the targeted 2×2 comparison, explicit fine-grid audit and signed interaction.
