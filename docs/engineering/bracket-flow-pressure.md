# Matched bore pressure sensitivity

This study follows the nonmonotonic 7.01954% medium-to-fine pressure change in
combined run `180ee968-e26d-4f10-9095-8e2316f5be4d`. It retains the exact
medium/far and fine/far level-4 cases and adds level-5 bore regions on each
background mesh. All four cases share the same native STL, far-domain bounds,
fluid, boundary conditions, general surface/wake refinements, smoothing and
1,500 SIMPLE iterations. Only the spherical bore-region refinement changes
within each matched background-mesh pair. Snapping and transition cells can
also change, so the study does not isolate a pressure-equation error.

Level 5 halves nominal bore-region spacing: medium 0.703125 → 0.3515625 mm;
fine 0.602679 → 0.301339 mm. The refined cases have explicit 250,000 local/global
cell budgets and a 250,000 accepted field-count ceiling. Historical level-4
limits remain 200,000 accepted cells. Worker memory, temporary storage, archive
limits and timeouts remain bounded as documented for combined verification.

## Native export audit

The existing packaged function-object route could not export a complete native
C field. A separate successful path uses `foamToVTK -legacy -ascii -poly-decomp
-no-boundary -no-point-data -noFunctionObjects -with-ids -fields '(U p)' -time
1500` on temporary copies of verified mesh and fields. The audit supplies its
own fixed control dictionary, extracts only selected archive files, and never
executes function objects from a source case. Duplicate/traversal paths and
oversized archives are rejected.

Additional decomposition points are matched to original cells through native
`cellID`. Multiple owners, nonfinite coordinates, invalid connectivity or IDs
are rejected. Standard-cell centres are not exposed by this export. Every case
therefore records actual native centre coverage and coverage of the four
support cells at each probe. Exported centres, source archive hash, exporter
binary hash, native-export hash and exporter log are retained in the comparison
JSON. Audit distance/coverage arithmetic is recomputed against each immutable
source field before registration. The original full VTK file is temporary;
its hash is an execution fingerprint, not a retained downloadable artifact.

This is a **partial native geometry audit**, not full native C, native probe
interpolation, a pressure error bound or validation of unsampled bore supports.
ASCII float coordinates also include export rounding. The native exporter
supports decomposed polyhedral output and cell IDs; see the [OpenFOAM VTK
mesh description](https://api.openfoam.com/2212/classFoam_1_1vtk_1_1vtuCells.html).
The installed v1912 command help and actual execution are recorded locally.

## Comparisons and provenance

Every pressure value is compared after subtracting the same upstream probe
(-30, 15, 20) mm within its case. Maxima use the nine unchanged fixed probes.
Pressure changes are normalized by 0.5 U² = 0.00005 m²/s² and velocity-vector
changes by 0.01 m/s. A gauge shift alone cannot create a referenced-pressure
change; physical reference-probe sensitivity remains possible.

The report separately plots medium → fine background-mesh changes at each
bore level and level 4 → 5 local-refinement changes on each background mesh.
These are matched sensitivities, not successive asymptotic errors or a combined
error bound. JSON retains individual signed probe changes and interpolation
supports. CSV contains 36 case/probe records. Source and derived studies remain
immutable and are registered independently.

Create source cases with `POST /runs/{native-parent}/flow` and JSON inputs
`mesh_name` medium/fine, `domain_name` far, `bore_level` 5. Defaults preserve
existing level-4/base-domain behavior. Unsupported input keys and bore levels
are rejected. Finalize from the project root with:

```
python3 scripts/verify_bore_pressure.py --combined COMBINED_RUN \
  --medium-refined MEDIUM_LEVEL5_RUN --fine-refined FINE_LEVEL5_RUN
```

The command audits existing cases through the installed local CFD container;
it does not rerun the solver or overwrite old artifacts. Native audit caches
are under `.local/verification/pressure-native/` and are bound to source archive
hashes. The derived `bracket_flow_pressure` study appears as **Bore pressure**
in the website, with two sensitivity plots, source-case links, checks and
Markdown/CSV/JSON downloads.

Residual, mesh-quality and finite bore-opening checks do not establish mesh
independence or engineering acceptance. No prism layers, forces, turbulence,
service conditions or thermal coupling are introduced by this study.

## Same-field interpolation check

A second diagnostic chooses an enclosing tetrahedron with the smallest maximum
support radius, then smallest summed support distances, from the same bounded
candidate pool and wall-visibility tests as the saved interpolator. Both methods
use positive weights and exactly the same solved cell fields and reconstructed
centroids. All compact probe values, supports, weights and signed referenced
pressure changes are retained, and their arithmetic is verified against source
fields. The compact method is linear-exact on a supporting tetrahedron; neither
method establishes accuracy in a curved pressure field. This is a stencil
sensitivity check, not native OpenFOAM interpolation or a new solver run.

The website's **Sampling view** switches both plots between saved interpolation
and the compact audit. Original production values and historical reports remain
unchanged. The report retains both matched comparison sequences.

## Recorded study (16 October 2026)

The matched source cases are:

| Background mesh | Bore level | Cells | Run ID |
|---|---|---|---|
| Medium | 4 | 113665 | `2c7d216e-68a2-4ea5-90f6-829b11ce66c2` |
| Fine | 4 | 162811 | `c88dbfb9-d355-4a35-90df-c8c7257d5a81` |
| Medium | 5 | 158413 | `7653f453-f3ed-4d1f-bb1e-ed85835746ab` |
| Fine | 5 | 226226 | `f5b96b88-a1d3-4c9d-a872-64662c4c792c` |

All four cases passed solver, mesh-quality, reconstructed-volume, boundary-mass
and finite bore-opening gates. The medium/level-5 case was preserved after an
unintended API restart interrupted its request. Its completed mesh, fields and
logs were recovered, then reproduced and verified through the normal bounded
archive/dictionary/source checks before registration. The fine/level-5 case
completed through the normal API. Recovery evidence remains under
`.local/verification/pressure-native/`; no historical registered run was edited.

| Medium → fine pressure sensitivity | Saved interpolation | Compact stencil audit |
|---|---|---|
| Bore level 4 | 7.01954% (upright bore 1) | 3.46127% (wake) |
| Bore level 5 | 6.24838% (below) | 6.31017% (below) |

At upright bore 1, the original level-4 mesh-pair difference changes from
7.01954% to approximately 0.20445% when the compact diagnostic is used. Its
**raw same-field fine-case bore pressure does not change**. Instead, the
fine/level-4 upstream reference stencil shrinks from 13.018827 to 6.838765 mm
maximum support radius. Its raw pressure shifts by approximately
−3.38780066×10⁻⁶ m²/s², propagating a 6.77560%-of-dynamic-scale shift to
referenced bore values. This explains why the original headline was strongly
sensitive to interpolation at the reference, rather than proving a local
bore-pressure error of that magnitude.

The finer bore meshes do not settle the remaining sensitivity: the final
compact medium-to-fine maximum is 6.31017% below the bracket. Local level-4 → 5
changes are 3.19893% medium / 10.70354% fine with saved interpolation, and
3.19386% / 3.92793% with compact stencils. These changes cannot be added into
an error bound or called a converged result.

The native exporter exposes only part of each mesh and none of the four saved
support centres at either upright bore probe. The partial native audit cannot
validate those bore sampling positions. Geometry-audit verification permits
relative 10⁻¹² / absolute 10⁻¹⁵ roundoff in scalar arithmetic for portability
between Python runtimes; source hashes and identities still match exactly.

Final comparison run: `d78f5d0a-022a-47ad-8f28-af8d97ee1471`.
Manifest SHA-256: `d2eb7e4f520c9dd6a97e64c7ec1bc92038f303da6120b38be61bbb04e86bfbfc`.
The earlier derived report `ed05d042-4e85-4eeb-9720-2ba7b3fd444d` remains
immutable; the final report adds the explicit upstream-reference diagnosis and
portable audit verifier. Source solver cases are identical.

All four source archives were checked against the current fixed case recipe
and their diagnostics reproduced before final registration. Independent Mac
checks verified source/derived manifest hashes, native and compact-stencil
arithmetic, 36 saved probe/CSV records and 36 compact diagnostic records.
The verification receipt is `.local/verification/pressure-native/verification-receipt.json`.

Validation: 197 backend tests, 74 viewer tests and 30 isolated integration checks
passed. Browser visual review was not repeated after the earlier automatic
approval-review usage-limit failure; chart conversions, method selection,
per-probe arithmetic, zero handling and missing evidence are unit-tested.
Reload the website, select **Bore pressure d78f5d0a**, and use **Sampling view**
and **Pressure probe** to review both interpolation methods. Engineering
acceptance, mesh independence and complete native bore sampling verification
remain unestablished.
