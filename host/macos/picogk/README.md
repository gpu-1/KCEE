# Native PicoGK bracket adapter

Pinned PicoGK 2.3.0 with Microsoft .NET SDK 9.0.318 on macOS ARM64. The SDK archive is SHA-512 checked against official Microsoft release metadata; NuGet packages use packages.lock.json and locked restore. Native binaries/cache are private local files under .local/, excluded from Git. No system installation or HTTP listener is required.

Provision: `python3 scripts/provision_picogk.py`. This downloads official dependencies on first setup. Generate: `python3 -m kcee.demo --geometry-backend picogk --output runs`. Import the printed UUID using `docker compose exec api python -m kcee.registry register /data/runs/RUN_UUID`, then refresh the viewer. Container API creation continues to use the mesh baseline until an authenticated native gateway is implemented.

Default geometry: L bracket, four 5 mm mounting holes (two base and two upright), 1 mm fillet-like voxel operation, 0.5 mm voxel size. Native geometry settings are recorded in geometry-request.json and geometry.json. Customize geometry_options in a requirements JSON: voxel_size_mm, fillet_radius_mm, hole_diameter_mm, mounting_holes. Bound dimensions/resolution and a 120-second subprocess timeout limit the demo. No silent fallback on kernel failure; failure.json retains diagnostics and no success manifest is issued.

Provenance captures package/kernel version, build information, native-library and adapter-assembly hashes, voxel size, exported triangle count, duplicate-vertex triangle cleanup, voxel volume and bounding box. Mass uses voxel volume. Analytical stress/deflection still approximate an ideal rectangular cantilever and omit the holes, contact and fillet effects. Geometry generation is not engineering validation.

Checks: `PYTHONPATH=. python3 scripts/check_picogk.py`. Verifies closed oriented STL meshes, four-hole topology, provenance, and plain-bracket volume within 3% of analytical volume. Refinement/mesh convergence and actual FEA remain pending. Voxel fillet-like operations are not exact CAD fillets; exported STL units are mm by contract.

Migration: copy code, lock files and historical runs; provision .local/ on the destination Apple Silicon Mac. Generate launch paths from repository location. PicoGK is Apache-2.0; retain upstream licenses distributed with the packages.

Official references: https://picogk.org/doc/setup.html ; https://github.com/leap71/PicoGK ; https://builds.dotnet.microsoft.com/dotnet/release-metadata/9.0/releases.json
