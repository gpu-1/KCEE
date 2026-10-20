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

## Reopen and verify exported JSON

Under **Where loads change**, expand **Verify a regional export**, select a regional JSON snapshot (up to 2 MB), and choose **Verify export**. The selected source report and its source cases must exist locally, including after a backup restore. The file is sent only to the local API; imported values are never registered or substituted for source evidence.

`POST /runs/{uuid}/regional-force-verification` accepts the original JSON bytes, with the local website Origin and `X-KCEE-Evidence: 1`. Input is streamed with a 2 MB limit. Strict parsing rejects duplicate keys, nonfinite values, unsupported schemas and excessive nesting. The verifier hashes the exact uploaded bytes, independently replays the selected native source report and recomputes its regional snapshot. Every field is compared, including comparisons, limits, method version and all provenance. Boolean values cannot substitute for numeric values.

Results distinguish `matches_reproduced_sources`, `snapshot_differs`, `source_mismatch`, `source_unavailable`, `source_integrity_failed` and `source_replay_failed`. A mismatched source report is not replayed. Changed snapshots identify affected top-level fields. An implementation mismatch is reported explicitly among those fields; historical exports are not silently rewritten for a newer method. The original regional implementation is unchanged by this verifier, so previously exported files from that implementation still match.

JSON and readable text verification reports retain the exact file SHA-256, local check time, selected report, reproduced source identities, mismatch categories and engineering limitations. A report is also available for a completed mismatch. Malformed files and request failures do not receive a successful verification status. A matching snapshot with failed original source checks still records those failures and leaves engineering acceptance pending. Verification demonstrates equality to the available local evidence; it does not establish authorship, external authenticity, mesh convergence or physical accuracy.

## Spatial inspection of the actual CFD wall

Native load reports now offer **CFD wall neighborhoods** above the 3D preview. Choose a wall source case, then **Show regions**. The seven categorical colors identify the four bore neighborhoods, root, base remainder and upright remainder. Selecting one neighborhood dims the others without removing faces. A matching table shows the selected source's pressure, viscous and total force or moment vectors. **Original model** restores the PicoGK STL.

`GET /runs/{report}/regional-wall/{source}` first verifies the report and requires the source to belong to that report, replays native/regional evidence, then reads the original wall vertices and faces. Display polygons are fan-triangulated, with all triangles inheriting their parent native face-centre region and source face identity. Unique source face counts must match every integrated region. Positions are converted from metres to millimetres only for display. Colors label regions; they are not stress or force magnitudes. Rendering triangles do not redefine numerical integration areas or change the saved flow fields.

The versioned `native-regional-wall-view-v1` JSON includes the display mesh, parent face identities, region inventory, integrated regional loads, report/source/native archive hashes, regional method fingerprint, display implementation fingerprint and pending engineering status. Browser validation rejects malformed indexing, nonfinite coordinates, inconsistent parent regions and mismatched face counts before rendering. Evidence exports and historical report manifests remain unchanged. This view does not establish exact bore boundaries, hydraulic performance, mesh independence or physical validation.

## Native pressure and traction fields

The wall preview now offers neighborhood colors, pressure relative to the outlet (Pa), full viscous traction (Pa) and total traction (Pa). Tractions can show magnitude or signed x/y/z components. Pressure is physical rho*p, using the same saved owner-cell kinematic pressure as native integration. Full viscous traction is rho*(Sf & devReff)/|Sf|, retaining both normal and shear terms. Total traction adds pressure traction. Forces act from fluid on solid.

`GET /runs/{report}/wall-fields/{source}` preserves the existing regional and wall-display implementations, returning the new `native-wall-fields-v1` envelope. It includes one record per native parent face: source face index, native centre, area vector and magnitude, pressure, pressure/viscous/total force and viscous/total traction. The sum of all face forces and centre-cross-force moments must reproduce all six integrated regional/native load groups within 1e-9 relative to the larger of the group magnitude and the dynamic reference scale. Display triangles inherit parent-face values; there is no smoothing or nodal stress recovery.

Numerical colors use an unlit, non-tone-mapped material and a blue–cyan–red legend. Signed pressure/components use a symmetric zero-centred range; magnitudes use zero to the case maximum. The actual face-value range is also printed. The scale is case-specific, includes all wall faces and stays fixed across neighborhood highlighting. Different cases may therefore have different scales. Lighting affects neighborhood colors, not numerical field colors.

Click a mesh face without dragging to inspect its native identity, region, centre, area, pressure, full viscous and total traction, and pressure/viscous/total forces. Multiple display triangles from one polygon return the same parent values. Orbit dragging is excluded from picking. Source loading disables old-face inspection and clears stale tables/links; returning to the original model clears field legends and inspection.

The geometry/evidence JSON now includes the wall fields and the separate field implementation SHA-256. Earlier wall-view and regional JSON methods are unchanged. Pressure depends on its reference; traction accuracy, wall resolution, physical validation and engineering acceptance remain pending. These colors do not represent structural stress or design allowables.
