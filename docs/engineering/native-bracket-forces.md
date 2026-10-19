# Native pressure and full viscous forces

**Calculate native wall loads** postprocesses the existing final OpenFOAM fields
without solving additional flow iterations. Select a saved bracket-flow case
for a single-case report, or its native design / comparison report for the six
existing Compact v1 mesh/domain cases. A native study is registered separately
from the historical `wall-face-traction-v1` estimates. Existing studies, meshes,
fields and reports remain immutable.

## Runtime issue and narrow repair

The pinned OpenFOAM 1912 library's SHA1 output stream implements bulk writes
but lacks the character-overflow operation needed by newer C++ libraries. This
caused any function-object dictionary initialization to fail in `IOstream
"sha1"`. The equivalent issue and fix are documented in the [upstream issue](https://github.com/OpenFOAM/OpenFOAM-9/issues/12)
and [upstream C++11 overflow fix](https://github.com/OpenFOAM/OpenFOAM-9/commit/b0c15bebd37142f3902901ed5e9a60e33ed456eb).

The worker now builds a small compatibility library from the exact [Debian
1912 source package](https://deb.debian.org/debian/pool/main/o/openfoam/openfoam_1912.200626-3.dsc).
The original source tarball SHA-256 is
`c75ca0f04cc4f49708296c1926cbde9d0138b3fef298fed54270dfe29e2df404`.
Only `Foam::dictionary::digest() const` is exported. Its ordinary dictionary
serialization and SHA1 calculation use the corrected stream. A linker export
map and build check enforce that one-symbol interface. Hashing is not disabled.

The build self-test checks SHA1 of mixed character/string writes against the
known `abc` digest and dictionary digest against independently serialized text.
The library is loaded through `LD_PRELOAD` for fixed native postprocessing commands. The versioned [force-history workflow](force-history-refinement.md) additionally scopes it to its fixed solver invocation. The normal worker environment, meshing commands and historical solves do not receive it. The stock solver executable is
unchanged and its digest must match the source run's recorded solver digest.
Build records bind source checksum, corrected header, compiler, compatibility
source files, export map, library and test executable. Native evidence also
records the package, solver and core/force/transport/turbulence library hashes.

Initial provisioning downloads the checksummed 45 MB public source archive and
build dependencies; subsequent Docker layers can be reused. Mac Studio uses
the same ARM64 container build. Replaying archived integration evidence in the
API needs no compiler. Fresh native processing requires a compatible pinned
solver binary; it does not silently substitute another build.

## Native stress and independent integration replay

Method: `openfoam-full-stress-v1`.

OpenFOAM's `forces` object computes pressure and full viscous forces/moments,
with `rhoInf=1 kg/m³`, `pRef=0 Pa`, no porous contribution and moment origin
`(0,0,0)` m. The saved solver's laminar model supplies `devReff`, including
normal viscous components and native gradient/nonorthogonal corrections.
`p` remains kinematic pressure in m²/s² and `devReff` kinematic stress in
m²/s². Density converts them to Pa. Forces are from fluid on solid; +x follows
the inlet. See the [native force definition](https://doc.openfoam.com/2306/tools/post-processing/function-objects/forces/forces/).

The evidence contains native pressure/viscous/total force and moment files,
full boundary symmetric stress tensors, native boundary face centres, exact
postprocessing dictionary, log and runtime fingerprints. An independent Python
replay reconstructs oriented area vectors `Sf` from the saved source mesh and
sums `rho*p*Sf`, `rho*(Sf & devReff)`, and native face-centre cross force. All
three components, totals, tensor trace and units are checked. Replay tolerance
is 1e−9 of the corresponding vector scale, with inlet force/length scales
protecting near-zero components. It does not divide by nearly zero individual
components.

This verifies integration of exported native stresses; it is not an independent
solution of the velocity-gradient field. Native face-centre pressure moments
can differ slightly from the old triangle-integrated moments on warped faces.
Uniform-pressure offset force and moment closure are retained as diagnostics;
finite native moment closure is not silently replaced with zero.

## Analytical native benchmark

A rectangular 0.06×0.02×0.03 m domain uses prescribed fields
`U=(0.4*x+3*y, -0.4*y, 0)` m/s and
`p_kinematic=0.7+0.3*x-0.2*z` m²/s². The velocity is divergence free, with
constant full viscous stress, including nonzero normal traction at the bottom
wall. Density is 2 kg/m³ and kinematic viscosity 0.002 m²/s.

Three structured meshes use 8/16/32 x-cells and half as many y/z cells. Native
processing is compared with exact surface integrals for pressure, shear and
normal viscous forces and all moments. Force and viscous-moment relative errors
must be below 1e−9. Affine pressure gives quadratic pressure-moment integrands;
face-midpoint quadrature must approach the exact moments at second order, with
fine-grid relative error below 1e−4. Independent exported-tensor integration
must also reproduce each native benchmark result.

**No flow PDE is solved by this benchmark.** It verifies the native constitutive
stress and integration path, not bracket flow-model accuracy, mesh independence
or service-condition suitability. Existing solver benchmarks remain separate.

## Website, jobs, exports and provenance

The native result view provides a saved-case selector, signed force/moment
charts, a native-versus-prior viscous comparison, five mesh/domain comparisons,
analytical benchmark errors, checks, source links, CSV, JSON, ZIP evidence and a
readable report. Native-minus-estimate differences are signed; they are not
presented as analytical errors. Near-zero components are never percentage
denominators. Coefficients retain the declared 0.0012 m² envelope area and
`0.5*rho*U²*Aref`, rather than a measured mesh silhouette.

Jobs use `kind:"native_forces"`. Progress distinguishes source verification,
benchmark processing, native postprocessing, integration replay and saving.
Cancel terminates a running command group or stops at a cooperative verification
checkpoint. Retry creates a new job ID and re-verifies the existing source
cases. A cancelled partial native postprocessing result is not registered as a
completed study. Existing registered source cases remain available; partial
native exports are not promised as standalone retained studies.

- `POST /runs/{id}/native-forces`: fixed synchronous equivalent.
- `GET /runs/{id}/native-force-verification`: source/raw-field verification and
  replay of the archived native stress integration; no worker solve required.

`native-forces.zip` contains one bounded evidence ZIP per source and a fixed
three-case benchmark ZIP. The worker accepts only whitelisted numeric ASCII
source members and fixed dictionaries. Includes, executable dictionary
statements, custom patches, commands and arbitrary paths are rejected.
Registered manifests bind every source manifest, source archive, native export,
implementation file and derived artifact. The standard verified backup format
supports native reports; original source runs must accompany migration for
full evidence replay.

No prism layers, mesh/domain convergence, turbulence model, mounting-wall
condition or realistic service load is added here. Fine far→outer comparison
still includes its recorded background spacing/alignment changes. Full native
stress integration improves the calculation method; engineering acceptance and
force accuracy remain unestablished. Loads are not automatically transferred
into structural FEA.

## Recorded verification — 19 October 2026

The website cancelled job `d10f39c8` while a native process was active. The
worker stopped and all six registered source links remained available. Retry
`aaf97eec` completed native result `c93cd7ad-9336-4b93-b71f-79f63849d52a`.
Manifest SHA-256:
`2eb2e8d9baf2f83982f55f60afe6f011d56fd9ad2a97a3bc594dd72df8c3c893`.
All recorded implementation and compatibility-source hashes matched the final
project files. The evidence ZIP is about 3.01 MiB.

All source solver/bore checks, native analytical benchmark checks and independent
native integration replays passed. Benchmark pressure-moment orders were
2.000000000006 and 2.000000000050. The six native viscous x-forces were about
15.7–22.8% higher than the earlier positive x estimates; these are method
comparisons, not measured errors or engineering acceptance. On the fine targeted
outer case, pressure x-force was 2.920641e−7 N, full native viscous x-force
3.269681e−7 N and total x-force 6.190322e−7 N. Prior estimate values were
reproduced exactly from the unchanged historical report.

Independent checks covered all 18 CSV component rows, five comparison vectors,
implementation fingerprints and ten unchanged prior manifest digests. Regression
validation passed 256 backend, 91 viewer and 31 isolated service tests. The
isolated native workflow includes registration, benchmark, source-binary identity
and archived stress replay, using an explicitly synthetic hole-free fixture
rather than claiming native geometry validation. Receipts, runtime diagnostics,
logs and browser previews are in `.local/verification/native-forces/`.

The website’s **Reproduce native evidence** action independently replayed all six source cases successfully. Force/moment switching and native-versus-estimate tables were visually checked at the normal narrow window size.
