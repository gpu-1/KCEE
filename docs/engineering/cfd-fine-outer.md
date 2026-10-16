# Joint targeted mesh and domain sensitivity

**Compare meshes & domains** extends the pressure-reference study with a fine
outer-domain solve. The new `kcee.bracket-flow-reference.v2` report keeps the five
original sources and adds one source. Original v1 reports remain readable and
unchanged. Targeted medium/fine cases now cover the same far and outer physical
domains. Two baseline far-domain cases remain as context.

## Domain and grid controls

The outer bounds were originally constructed by extending the medium far grid
by four cells on each side. Those physical bounds are not integer-cell shifts
of the existing fine far grid. The fine outer case therefore uses 65×49×53
background cells, with the exact medium outer physical bounds. Relative to the
fine far case, its background spacing changes by +0.51282%, −0.22676% and
+0.49652% in x, y and z. Fine-grid alignment also changes. Derived nominal bore
and near-surface cell sizes follow the actual background spacing.

This keeps physical domain bounds identical within each medium→fine mesh pair.
The medium far→outer pair still preserves its background spacing and alignment.
The fine far→outer pair is explicitly **domain-plus-grid sensitivity**. Its
changes and the interaction cannot be attributed solely to boundary distances.
Obtaining both identical physical bounds and exact fine-grid alignment would
require a different matched domain/grid construction and additional solves.

The source STL, physical wake/below boxes, surface levels, bore level 4, fluid,
boundary types, 1,500 SIMPLE iterations and Compact v1 sampling stay fixed. The
fine outer mesh cap is 350,000 cells. Worker memory and CPU limits remain
fixed; only this case receives a bounded 128 MiB API response allowance, versus
96 MiB for other cases. Fine outer raw archives are bounded to 48 MiB compressed and 256 MiB unpacked; other cases retain their 36/192 MiB bounds. The meshing log is checked for cell-cap termination.

## Comparisons and interaction

The report includes baseline far medium→fine, targeted far medium→fine,
targeted medium far→outer, targeted outer medium→fine and targeted fine
far→outer. Each retains the upstream-reference, above-reference, selected local
pressure contrasts and velocity-vector diagnostics described in the
[pressure-reference study](cfd-pressure-reference.md).

The signed interaction is:

```
(fine outer − fine far) − (medium outer − medium far)
  = (fine outer − medium outer) − (fine far − medium far)
```

The identity is evaluated for each referenced pressure and local contrast.
Velocity interaction uses the norm of the signed vector difference of
differences, not subtraction of velocity-change magnitudes. Four source IDs and
manifest hashes bind the interaction. It measures how the recorded domain
change depends on the mesh recipe; it is not an error bound or proof of
independence. The upstream/above pressure decomposition still closes
algebraically and retains its interpretation limits.

The chart shows the five direct comparisons. The comparison selector also shows
signed interaction probe and local-pair tables. JSON and Markdown retain the
full interaction and grid audit. CSV contains 65 direct-comparison rows (five
pairs × nine probes plus four local contrasts); interaction is in JSON/report.

API: `POST /runs/{native_design_id}/flow-joint-study`, empty JSON body. Five
compatible source cases are raw-reverified; the fine outer solve is reused if
available and compatible. Completed cases remain registered on later failure.
Mesh/domain independence and engineering acceptance remain unestablished.

## Recorded verification (16 October 2026)

Final comparison: `7d674933-9d37-4b7f-aae7-ab24bbcb0830`.
Fine outer source: `751abae6-f97c-49a6-a9ed-4d00fd8aaf5a`, 292,125 cells.

| Comparison | Upstream-reference max | Above-reference local max | Above−upstream term (signed) | Selected local-pair max | Velocity / inlet max |
|---|---:|---:|---:|---:|---:|
| Baseline mesh | 3.46127% | 2.73395% | 2.52949% | 1.75168% | 1.33651% |
| Targeted mesh | 3.42376% | 2.73887% | 2.51456% | 1.70896% | 1.34014% |
| Targeted far → outer | 1.95876% | 1.23665% | 1.81874% | 0.23972% | 0.84183% |
| Outer medium → fine | 3.13542% | 2.15191% | 0.98351% | 0.76460% | 0.72257% |
| Fine far → outer + grid | 3.37730% | 3.08961% | 0.28769% | 0.95081% | 1.97287% |
| Mesh/domain interaction | 2.79521% | 4.32626% | -1.53104% | 1.14444% | 1.41431% |

All six source solver and bore checks passed. The final fine meshing log confirms
that refinement did not stop at the cell limit. A mesh-only precheck independently
produced the same 292,125-cell count and passed bore/mesh gates. An initial
300,000-cell attempt reached the cap during refinement despite a lower final
count after snapping; it was interrupted and is excluded from the comparison.
Its observed cap messages and the corrected precheck logs are retained in the
local evidence folder. Full archive capture of that interrupted attempt was
unavailable; the final successful run has its complete raw archive.

The targeted pressure mesh maximum changes from 3.42376% in the far domain to
3.13542% in the outer domain. The corresponding selected local-pair maximum
changes from 1.70896% to 0.76460%. However, the fine far→outer pair changes the
upstream-referenced field by up to 3.37730%, and the signed pressure interaction
reaches 2.79521% (upstream reference) or 4.32626% (above reference, excluding
upstream). These do not establish joint independence. Fine domain and interaction
results include the documented spacing/alignment changes. Maxima cover different
probe sets; they are not additive error bounds or interchangeable field norms.

Final checks verified eight manifests (parent, six sources and comparison),
unchanged original source hashes, fixed-case/sampling/runtime archive evidence,
probe interpolation arithmetic, both equivalent signed interaction paths,
velocity-vector interaction, decomposition closure, the grid/cap audits and all
65 CSV rows. Hashes are exact. Cross-platform floating-point recomputation uses
relative tolerance 1e−12 and absolute tolerance 1e−15.

Evidence: `.local/verification/fine-outer/verification-receipt.json`,
`verify_final.py`, `mesh-check.log` and regression/browser proof files.
Registered reports and exports:
`runs/7d674933-9d37-4b7f-aae7-ab24bbcb0830/`.
Validation: 223 backend tests, 83 viewer tests and 30 isolated integration checks
passed (336 total). The actual website report, all five chart groups, six source
cases, grid-change notice, signed interaction selector and export links were
checked.
