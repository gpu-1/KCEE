# Native bracket geometry refinement

Generate the same bracket at 0.75, 0.5 and 0.35 mm voxel size with `python3 scripts/check_geometry_refinement.py --output .local/studies/<new-study-name>`. The destination must be new. Runs and original manifests remain local; the recorded summary is in geometry-refinement.json. No database registration or FEA solve is performed.

| Voxel size (mm) | Voxel volume (mm³) | STL volume (mm³) | Triangles |
|---|---:|---:|---:|
| 0.75 | 9727.117 | 9693.207 | 25776 |
| 0.5 | 9793.418 | 9811.611 | 63196 |
| 0.35 | 9843.418 | 9826.018 | 115044 |

Closed meshes and Euler characteristic −6 were verified at each resolution, consistent with the expected four through holes. Last voxel-volume change is 0.5105%; last surface-volume change is 0.1468%. The 0.5 mm STL hash matches the existing bracket FEA source.

These measurements do not establish asymptotic convergence, local hole/transition accuracy, or stress convergence. Repeated structural solves and local geometry measurements remain required.
