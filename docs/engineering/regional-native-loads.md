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

## Area-weighted comparisons and common color scales

**Compare field distributions** loads and checks every source case of the selected native report, reusing cases already in the browser cache. Progress identifies the current case. It derives whole-wall and per-neighborhood distributions for pressure, viscous traction and total traction, with magnitude and signed x/y/z traction components. The chart shows min–max, the area-weighted P05–P95 interval and median; the table includes face count, wall area and mean.

`native-wall-area-distributions-v1` counts each native parent face once, using its area-vector magnitude as the area weight. Fan triangles are never counted as independent samples. A quantile is the first sorted face value whose cumulative area reaches the specified fraction; no interpolation is applied. Means and RMS values use area weights. Empty neighborhoods are unavailable, not zero-valued evidence.

After comparison, **Use shared color scales in the 3D view** locks each numerical field to the extrema across all compared source cases. Signed fields use a symmetric zero-centred range; magnitudes use zero to the common maximum. The original per-case scale remains selectable by disabling the checkbox. Highlighting a neighborhood does not recompute either range. The legend explicitly states whether the range is case-specific or shared.

The comparison JSON binds the native report manifest, every source manifest/archive/native evidence hash, field and regional implementation identities, all nine field distributions, all neighborhood distributions and the common ranges. Each checked wall-field payload is additionally bound by the SHA-256 of its compact JSON representation. This is a derived comparison snapshot, not a replacement registered study. Native source methods and historical exports are unchanged.

Surface populations and neighborhood membership differ across meshes. Area-weighted distribution changes are not matched-point errors, analytical accuracy estimates, mesh convergence, or physical validation. Pressure retains the saved outlet reference; common color scales improve comparability without resolving reference or discretization sensitivity.

## Hotspot tail investigation and spatial location

After loading a wall source, **Analyze hotspots** ranks native parent faces by absolute pressure, full viscous traction magnitude or total traction magnitude. Presets request the top 0.1%, 1% or 5% of wall area. The descending ranking includes whole faces until the target area is reached, then includes every exact tie at the threshold. The actual selected area is reported explicitly and can be much larger for ties or coarse meshes. Each parent face is counted once, regardless of its display triangulation.

`native-wall-hotspot-tail-v1` integrates the selected faces and the remainder separately for pressure, full viscous and total forces and moments about the origin. Both their sum and the full reconstructed load must agree with the recorded integrated native wall fields within 1e-9, normalized by the largest norm of the whole, selected and remainder group (floor 1e-30). This avoids dividing by nearly zero net vectors when opposing contributions cancel. The report retains all six vectors, closure differences, actual area, threshold, every selected face identity and regional contributions.

The table lists the first 12 ranked faces; JSON contains all selected faces. **Locate** highlights the face's diagnostic neighborhood, shows its native values and places a white marker at its native face centre. The camera target moves to that position. The marker deliberately renders through the mesh and is a location cue, not a force arrow, physical surface extent or scalar color. Changing source, returning to the original model or changing the rendered field clears the marker. Input changes hide stale hotspot evidence until analyzed again.

The hotspot JSON binds the report/source manifests, source and native archive identities, original field/regional implementation hashes and exact compact wall-field snapshot SHA-256. No original solver field, registered report or earlier diagnostic method is modified. A small selected area can carry substantial loads or opposing contributions; tail loads are not allowable structural stresses. Peaks may remain mesh-sensitive. This diagnostic alone does not identify a mathematical singularity, establish accuracy/convergence or prove a proposed refinement sufficient.

### Hotspot sensitivity across meshes

Field comparison exports include `native-wall-hotspot-comparison-v1` under `hotspots`. Each source mesh independently selects its own tails for absolute pressure and viscous/total traction magnitude at requested wall areas of 0.1%, 1% and 5%. Whole threshold faces and all ties are included; compare actual area fractions, especially on coarse meshes.

The viewer charts threshold and peak values in Pa and tabulates peak neighborhood/centre, tail total force and moment about the origin. The export retains all six load vectors, remainders, closure errors and regional contributions for every preset. Snapshot hashes and source manifests are bound by the enclosing field comparison. Peak face IDs belong only to their source mesh; peak movement and population differences do not provide matched-point errors, a convergence order, uncertainty or engineering acceptance.

### Fixed physical wall patches

Field comparison now includes `fixed_patches` with three fixed 2 mm radius selections: base upper (20,15,3.5), upright front (3.5,15,23), upright rear (0,15,23) mm. Signed fluid-patch normal directions are −z, −x and +x respectively, with cosine alignment at least 0.95. Every mesh uses the same targets. Whole parent faces whose centres lie in each sphere are area-weighted once; no interpolation or edge clipping is performed.

Exports retain selected native face IDs, sampled area/nominal disk area, sampled area centroid and target offset, nearest/farthest face-centre distance, mean pressure, viscous/total mean vectors and mean magnitudes. A missing patch is unavailable. These diagnostics make differing sampled areas explicit: they are not exact matched-point samples or discretization errors. Mean vector magnitude and mean magnitude are distinct. Source fingerprints remain in the enclosing comparison; engineering acceptance remains pending.

### Identical clipped wall footprints

`clipped_patches` in field comparison exports uses `native-wall-clipped-patch-comparison-v1`, with per-case method `native-wall-clipped-patches-v1`. Three common 4 × 4 mm squares share the previous physical centres and signed normal filters. Surface vertices and native face centres must lie within 0.05 mm of the target plane. Display triangles are clipped against the square; projected overlap fractions are summed per native face and multiply that face's native area. Display subdivisions do not count a native face twice. Original saved face fields remain piecewise constant.

Exports retain overlap and native weights, projected coverage, sampled centroid, pressure/traction vector means and mean magnitudes. Coverage within 0.1% of the nominal square is marked complete; partial and missing footprints remain explicit. This coverage gate checks the selected footprint, not flow accuracy. The square is distinct from the earlier circular face-centre selection; differences between those methods include footprint shape. These interior flat-wall patches do not resolve edge or bore sensitivity, and do not establish mesh convergence or an uncertainty bound.

### Targeted hotspot refinement study

The website's **Refine CFD hotspots** starts a cancellable/retryable `hotspot_refinement` job. It reuses the raw-reverified fine `wall-bore-history-fine-v2` baseline and solves a separate `wall-hotspot-history-v1` case. Both use the same fine background, far boundaries, Re=6 physics, level-4 surface/level-5 bore controls, three requested layers and 3000 recorded load iterations. Two level-5 volume boxes are added: root edge [−1,26,−2] to [8,32,9] mm and upright edge [−1,−2,35] to [6,6,43] mm. These target the previously observed lower-root and upper-upright extreme face locations.

The new recipe retains the 350,000-cell bound and fine-v2 skewness limits of 3.5. Standard `checkMesh` must report `Mesh OK.` before solving. Failed cases retain their diagnostics; no quality tolerance is silently relaxed. Historical case dictionaries are regenerated byte-for-byte for verification and remain unchanged.

Native postprocessing compares pressure/viscous/total force and moment vectors, records signed changes and target-normalized vector changes, replays full stresses, and checks final histories against postprocessed loads. Native analytical benchmark, source solver checks and bores remain explicit gates. Reports, all-source history CSV, paired history charts and implementation fingerprints are retained. Changed local topology/snapping and actual layer coverage mean this pair establishes sensitivity only, not a convergence order or engineering uncertainty.
