# Regional native load diagnostics

The native load report now includes **Where loads change → Analyze regions**. It replays the existing source evidence, then partitions every native wall face exactly once. No PDE is rerun and no registered report is modified.

`native-regional-loads-v1` uses native face centres in metres. Four radius-5-mm spheres surround the nominal bore centres (0.033, 0.015, 0.00175), (0.048, 0.015, 0.00175), (0.00175, 0.015, 0.016), (0.00175, 0.015, 0.030). First sphere wins. Remaining faces with x ≤ 0.008 and z ≤ 0.008 form the root neighborhood; remaining z ≤ 0.008 faces form the base remainder; the rest form the upright remainder. These are diagnostic neighborhoods, including adjacent plate faces, rather than exact bore-wall or manufacturing regions.

Pressure force is rho*p*Sf. Viscous force is rho*(Sf & devReff), using the exported native full tensor. Moments use native face centre crossed with force about (0,0,0) m. All six regional sums must reproduce the verified native totals within 1e-9 normalized by the larger of the load-vector magnitude and the declared dynamic force/moment scale. Each region retains face count and summed face area.

Pressure contributions on an open region depend on the outlet reference. The area-vector sum and sum of centre × area-vector record regional force and moment changes for a +1 Pa uniform physical pressure offset. They are sensitivities, not pressure uncertainties or kinematic-pressure offsets. The website JSON and CSV retain these diagnostics.

Controls select a pair of cases, pressure/viscous/total, force/moment and x/y/z. Charts and tables show signed regional changes. Adjacent pairs show their mesh, profile and domain identities; they do not imply a controlled one-variable study. Regional membership can change across meshes. No Richardson/GCI estimate, mesh convergence, physical validation or structural acceptance is inferred.

`GET /runs/{uuid}/regional-forces` returns JSON; `?format=csv` returns a CSV attachment. Both recheck source manifests, archive identities and the original native integration before partitioning. JSON binds the parent report, native archive, source manifests/archives/native evidence and regional implementation SHA-256. Browser exports are snapshots of that checked response. The endpoint is read-only and uses the original saved report's recorded physics.

The old native integration implementation and report inventories are unchanged, allowing historical reports to replay byte-for-byte. New diagnostics are identified separately by their version and implementation hash.

## Recorded three-mesh study

Report `2493f3ee-9cc2-4494-ae02-78f70256fa32`, manifest `7fc9e058b591a088d261d6ae8ccde6f4a591a8aa0757495125051a463a455ed1`. All 7,323 / 11,746 / 17,846 native wall faces were partitioned once. Maximum relative closure difference across all force/moment groups was 4.92e-15.

Medium → fine signed x-force changes (N):

| Neighborhood | Pressure | Viscous | Total |
|---|---:|---:|---:|
| Base bore 1 neighborhood | 5.97837e-12 | -3.3364e-11 | -2.73857e-11 |
| Base bore 2 neighborhood | 9.02725e-13 | -1.02059e-10 | -1.01157e-10 |
| Upright bore 1 neighborhood | 2.36836e-10 | 2.90986e-11 | 2.65935e-10 |
| Upright bore 2 neighborhood | 8.32146e-11 | 2.62744e-11 | 1.09489e-10 |
| Root neighborhood | -5.53779e-09 | 2.22363e-09 | -3.31416e-09 |
| Base remainder | 1.51048e-09 | -9.89505e-10 | 5.20975e-10 |
| Upright remainder | -7.54748e-09 | 9.24672e-09 | 1.69924e-09 |

The largest individual pressure and viscous changes are in the upright remainder, with substantial root changes. Opposing component and regional changes cancel in the whole-bracket total. These results identify diagnostic targets; centroid membership, quality-recipe changes and pressure-reference dependence prevent an error or convergence claim.
