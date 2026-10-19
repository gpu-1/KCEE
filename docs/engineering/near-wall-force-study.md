# Near-wall layer force sensitivity

The **Compare near-wall layers** website action runs a fixed, cancellable `layer_forces` job. The existing far-domain medium/fine `wake-below-v1` cases are compared with newly solved medium/fine `wall-layers-v1` cases. Compatible source cases are reused only after their manifests, archives and diagnostics are independently verified. Completed cases survive cancellation and can be reused by Retry.

## Recipe

All cases use the same default PicoGK bracket, far-domain bounds, inlet speed 0.01 m/s, kinematic viscosity 0.0001 m²/s, density 1 kg/m³, laminar SIMPLE solver and 1,500 iterations. Surface and bore refinement and the wake/below refinement boxes match the prior targeted recipe. Historical dictionaries are unchanged.

The new version changes only `snappyHexMeshDict`: layer addition enabled; three surface layers requested on `bracket`; relative thicknesses; expansion ratio 1.2; final layer thickness 0.5; minimum thickness 0.05. These thicknesses are fractions of the local undistorted cell size, not metres. Remaining meshing and quality controls retain the targeted recipe. No globally preloaded runtime override is used for meshing or solving.

Actual extrusion coverage is read from the final `Extruding ... out of ... faces` mesher-log record, rather than inferred from `nSurfaceLayers`. Its numerator and denominator and the full log are retained. Coverage counts faces; it is not area coverage or a guarantee that all three requested layers exist everywhere. Partial extrusion and local collapse near bores and edges are expected limitations. A missing coverage record or zero extrusion does not pass the layer-presence gate.

## Native loads and comparisons

Native OpenFOAM full pressure and deviatoric viscous stresses are integrated for all four source cases. The existing pinned hash-compatibility overlay is scoped to native postprocessing. The affine-field analytical stress benchmark is repeated. Saved native stress tensors, native face centres, source mesh area vectors and force/moment output are independently replayed; source archives and runtime fingerprints are checked.

The registered `bracket_flow_native_forces` report contains four source identities, layer audits, signed force and moment changes, benchmark checks, native evidence ZIP, CSV and Markdown. Its manifest additionally binds the layer orchestration and mesh implementation. Read-only `/runs/{id}/native-force-verification` reproduces the four-case report from saved evidence without solving again.

Comparisons cover medium-to-fine changes within each recipe and the effect of adding layers at each resolution. For a force vector F, the reported relative mesh change is `norm(F_fine − F_medium) / norm(F_fine)`; a near-zero denominator is reported as undefined. It is a sensitivity metric, not a discretization error estimate. The website chart shows total x-force at medium and fine resolution, together with layer coverage for each selected source. Force and moment component charts remain available.

Two resolutions do not establish an observed convergence order, Richardson extrapolation, grid convergence index, physical validation or structural load-transfer acceptance. Layer addition moves wall-adjacent cells, changes local topology and may fail on some faces. A smaller force change would support further investigation; a larger one must remain visible. Boundary distances are held fixed for this batch, but domain independence remains a separate unresolved question.

## Interfaces

- `POST /cfd-jobs`: `{"kind":"layer_forces","parent_id":"<native bracket UUID>","options":{}}`
- Existing job status, Cancel and Retry controls apply.
- `POST /runs/{id}/layer-forces`: synchronous fixed-input counterpart.
- Individual flow jobs accept `local_profile: "wall-layers-v1"` with medium/fine far/outer domain and bore level 4. The comparison itself fixes the far domain.
- Existing native force and six-case comparison workflows remain supported.
