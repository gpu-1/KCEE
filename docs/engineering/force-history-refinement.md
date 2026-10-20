# Native load histories and wall/bore refinement

**Check force convergence · 3 meshes** starts a fixed `force_convergence` job. It compares pressure, full viscous and total loads separately, with native force and moment histories recorded at every iteration. It preserves the earlier two-level layer comparison and its component-cancellation finding.

## Fixed recipe

Version `wall-bore-history-v1` uses the original far-domain bounds, default PicoGK bracket, +x inlet 0.01 m/s, kinematic viscosity 0.0001 m²/s and density 1 kg/m³. It remains a laminar Re=6 demonstrator. Surface refinement increases from level 3 to 4 and bore refinement from level 4 to 5. Wake/below boxes retain their previous levels. Three wall layers are requested with expansion 1.2, relative final thickness 0.5 and relative minimum thickness 0.05. Actual extrusion coverage is reported for each case.

| Name | Background cells | Surface level | Bore level | SIMPLE iterations |
|---|---|---|---|---|
| Coarse | 28 × 21 × 23 | 4 | 5 | 3000 |
| Medium | 35 × 27 × 29 | 4 | 5 | 3000 |
| Fine | 44 × 33 × 37 | 4 | 5 | 3000 |

Names belong to this recipe; its surface/bore refinement differs from the older medium/fine layer recipe. The background counts are deliberately bounded to keep the surface-refined meshes within the 350,000-cell analysis limit. Historical background counts, dictionaries and 1,500-iteration workflows are unchanged. Each new source retains meshing/solver logs, final fields and complete force/moment output in its hash-bound CFD archive. Compact v1 probes, bore preservation, mesh quality, residual and mass-balance checks remain available.

## Scoped compatibility change

OpenFOAM's existing one-symbol dictionary-digest compatibility repair is now permitted for **two fixed invocations**: native stress postprocessing and this versioned force-history `simpleFoam` solve. Meshing and historical solves do not preload it. The command environment uses the pinned local library path; callers cannot supply code, libraries or arbitrary functions. The fixed force object records `solverLoads` on the bracket with rho=1 and moment origin (0,0,0), every iteration. It does not export volume stress fields every iteration.

The updated build descriptor is `dictionary::digest only; LD_PRELOAD restricted to fixed native CFD commands`. The old postprocessing-only descriptor remains accepted for historical evidence. Each history source records the actual overlay, source, compiler, solver, library and implementation fingerprints plus the exact solver invocation scope. Hashing remains enabled; no numerical solver symbol is replaced. See [the native load implementation](native-bracket-forces.md) for the pinned upstream source and overflow fix.

## Settling diagnostics

All 3,000 samples must have contiguous iteration identities, finite vectors and pressure + viscous = total closure for forces and moments. The last 100 samples are compared with the preceding 100. For each of the six component-vector groups, record:

- Norm of the difference between window means, normalized by the larger of the final mean-vector norm and the dynamic reference scale; limit 0.1%.
- Largest norm of a sample's deviation from the last-window mean using the same normalization; limit 0.2%.

The force floor is 0.5 rho U² Aref = 6e-8 N with Aref=0.0012 m²; the moment floor multiplies that by 0.06 m. This prevents division by tiny lateral components. Thresholds assess recorded drift; they are not residual error bounds. Pressure, viscous and total groups are tested separately so cancellation cannot hide drift.

Final full-stress postprocessing independently exports wall stresses and face centres and replays their integrals. Each final force/moment vector must also match its last online history value within 1e-6 relative to the larger of that vector norm and the reference scale. The native affine-field integration benchmark is repeated. It verifies implementation, not bracket physics.

## Mesh comparisons and exports

The combined native study records adjacent coarse→medium and medium→fine signed changes for all pressure, viscous and total force and moment vectors. Relative changes divide by the finer vector norm; near-zero results are undefined. All iteration samples are exported in `force-history.csv`, while JSON retains settling statistics and native/source evidence. CSV, JSON, native ZIP, Markdown and manifest links remain available.

The website provides per-case force/moment histories, pressure/viscous/total selection, the last 400 iterations or full history, and three-mesh x-component curves. Full vector mesh changes appear alongside the curves. The evidence replay endpoint rechecks saved source archives, history parsing/window statistics, final native stress integration and benchmark; it does not rerun the PDE.

Partial layering and local refinement produce a nonuniform sequence. Three levels alone do not justify a Richardson order, extrapolated continuum value, grid convergence index, uncertainty bound, physical validation or structural acceptance. Settled iteration histories and mesh independence are separate questions. Larger component changes remain visible even when total changes are small.

## Interfaces and recovery

`POST /cfd-jobs` with `{"kind":"force_convergence","parent_id":"<native bracket UUID>","options":{}}` uses the existing durable progress, Cancel and Retry controls. Compatible source recipes are reused only after raw-evidence verification. Completed cases survive cancellation; partial PDE work is not promised as a restart checkpoint. `/runs/{id}/force-convergence` is the synchronous fixed-input counterpart. `/runs/{id}/native-force-verification` replays the combined report.

## Fine-mesh quality revision

The original fine `wall-bore-history-v1` case settled its loads but failed standard `checkMesh`: two faces had maximum skewness 4.697, above the checker limit. Its failed quality gate and evidence remain saved; it is not an accepted source for the current three-level comparison.

The replacement `wall-bore-history-fine-v2` retains the fine background counts, surface/bore refinement, requested layers, physics and iteration budget. It tightens **mesh generation** boundary and internal skewness limits to 3.5, and requires standard `checkMesh` to pass before starting the solver. The checker is not relaxed. Coarse and medium v1 cases remain reusable. This quality-control difference is recorded in the fine source recipe and is another reason not to infer a uniform-refinement error estimate automatically.
