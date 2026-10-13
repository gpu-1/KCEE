# Native bracket geometry refinement

Generate the same bracket at 0.75, 0.5 and 0.35 mm voxel size with `python3 scripts/check_geometry_refinement.py --output .local/studies/<new-study-name>`. The destination must be new. Runs and original manifests remain local; the recorded summary is in geometry-refinement.json. No database registration or FEA solve is performed.

| Voxel size (mm) | Voxel volume (mm³) | STL volume (mm³) | Triangles |
|---|---:|---:|---:|
| 0.75 | 9727.117 | 9693.207 | 25776 |
| 0.5 | 9793.418 | 9811.611 | 63196 |
| 0.35 | 9843.418 | 9826.018 | 115044 |

Closed meshes and Euler characteristic −6 were verified at each resolution, consistent with the expected four through holes. Last voxel-volume change is 0.5105%; last surface-volume change is 0.1468%. The 0.5 mm STL hash matches the existing bracket FEA source.

These measurements do not establish asymptotic convergence, local hole/transition accuracy, or stress convergence. Repeated structural solves and local geometry measurements remain required.

## Mid-thickness hole sections

Use `python3 scripts/check_hole_accuracy.py .local/studies/<study>/geometry-refinement.json --output <new-report.json>` to measure the original verified STLs. The tool intersects each bore at mid-thickness and measures twice the radial extrema about its nominal center, including segment interiors. These are radial envelopes, not fitted diameters or manufacturing tolerances.

Across four holes, radial envelopes at 0.75 mm voxels span approximately 4.864–5.000 mm; at 0.5 mm, 4.937–5.000 mm; at 0.35 mm, 4.969–4.999 mm. Nominal diameter is 5 mm. Full values and source hashes are recorded in hole-accuracy.json. The extraction method is tested against square-prism sections with known radial bounds. Only these default bore locations and this one axial section are measured; root transition and positional accuracy remain pending.

## Bore profile across thickness

The hole measurement command now samples 0.875, 1.75 and 2.625 mm through the 3.5 mm plate, verifies source dimensions and nominal hole settings, and rejects incompatible geometry. Recorded values are in hole-profile.json; the earlier mid-section report remains unchanged.

Combined radial envelopes across all holes and sampled depths are 4.864–5.255 mm at 0.75 mm voxels, 4.937–5.000 mm at 0.5 mm, and 4.969–4.999 mm at 0.35 mm. The coarse geometry has a local widening not apparent in the mid-section alone. These are radial section envelopes, not fitted bore diameters. Entry/exit surfaces, exact hole-center deviations, root geometry and manufacturing acceptance remain unverified.

## Structural sensitivity attempt

The 0.35 mm source was registered as native run 15802ef9-5085-40b6-979b-91f03d7c6841 and submitted to the same bracket study. Gmsh failed parametrization at 20°. A temporary 10° probe passed parametrization but failed volume meshing with overlapping boundary facets. No structural result or success manifest was generated. Diagnostics remain in the local failed runs; identifiers and error evidence are recorded in geometry-fea-sensitivity.json. The production adapter retains the existing validated 20° settings.

This shows that closed edge topology, bore measurements and global volume checks are insufficient to establish STL suitability for volumetric meshing. Further work must characterize overlaps/near-coincident facets or choose a validated alternative meshing method before comparing structural responses across geometry resolutions. Do not infer fine-resolution stress convergence from the geometry study.

## Successful finer structural study

Further unmodified-STL probes meshed at 30°/45°. The completed 0.35 mm study uses explicit 30° classification and a 1 mm local size field around the load strip, including a compatible global minimum. The existing 0.5 mm path keeps its original 20° settings. Both choices are recorded in solver provenance. Run edac2bbf-2163-42ea-8a64-0f9647d92fb2 passes numerical checks and archive-to-preview verification.

Fine loaded-patch displacement is 0.783595 mm versus 0.780281 mm baseline (+0.425%). Peak integration-point von Mises stress is 257.407 MPa versus 100.199 MPa baseline. The load patch area is 114.411 mm² versus 130.849 mm² baseline. Geometry and meshing/load discretization changed together, so these differences cannot be attributed solely to voxel resolution. Stress convergence and physical acceptance remain unresolved. Earlier failed diagnostics are retained.
