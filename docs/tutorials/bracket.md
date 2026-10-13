# First bracket

## Start the workspace

For a new installation, follow [macOS installation](../operations/install-macos.md) and configure `.env`. Existing installations should keep their current passwords and database. Provision native geometry with `python3 scripts/provision_picogk.py`, then start `python3 scripts/start_geometry_worker.py`. Start the viewer and structural worker:

```sh
docker compose --profile viewer --profile fea up --build -d --wait
```

Open http://localhost:5173 and refresh. Native PicoGK ready and the structural worker status indicate that generation and analysis are available.

## Generate and analyze

1. Select Native PicoGK and choose Create bracket demo. The default sample is a 60 × 30 × 40 mm L bracket with four 5 mm holes and a rounded voxel root transition. Analytical thickness screening selects 3.5 mm for the sample material/load.
2. Select the saved native run and choose Analyze selected bracket. Gmsh meshes the original STL; CalculiX solves three refinement levels. A separate Bracket FEA child run retains the parent ID and original STL hash.
3. Inspect numerical checks, assumptions and provenance. The study fixes the rear upright face in all directions and distributes 100 N downward over the free-end strip. It does not model bolts/contact.
4. Enable Solver colors and select Displacement (mm) or Von Mises stress (MPa). Scale changes displayed deformation only; Undeformed shows the original solver surface. Nodal stress colors are averaged/extrapolated values, distinct from integration-point peaks in the refinement table.
5. Enable Load & support to show nominal regions on the undeformed reference. Inspect Hole geometry measurements for three through-thickness radial envelopes. These are not manufacturing acceptance.

The baseline mesh creates a simple sharp L shape without holes or rounding. It supports analytical screening, not the current native-bracket FEA path. The ? icon beside Geometry explains this distinction. Run cantilever benchmark creates a separate bar verification example; it is not a bracket model.

## Save, remove and verify

Reports, manifests and solver archives can be downloaded. Remove from list requires confirmation and retains files/provenance. Show removed models lets you select a hidden model and confirm Restore to list. Parent/child results are preserved independently.

[Verified backups](../operations/backups.md) preserve individual saved runs. Read-only checks are available in `scripts/check_bracket_fea.py` (use `--analysis-run-id` to avoid a new solve), `scripts/check_bracket_fields.py` and `scripts/check_host_readiness.py`. See their help and [migration instructions](../operations/migration.md).

Numerical checks and artifact integrity do not establish engineering validation. Geometry resolution/local bore studies are recorded in [geometry refinement](../engineering/geometry-refinement.md). Stress convergence, realistic mounting, material allowables and physical validation remain pending. Local AI/voice and other physics workers are not exercised by this demonstrator.

For the dependency-free baseline CLI, use `python3 -m kcee.demo --output runs`; follow [run registration](../operations/run-registry.md) before viewing CLI-generated runs in the workspace.
