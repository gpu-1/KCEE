# Verified plane Poiseuille flow benchmark

This is KCEE's reduced fully developed laminar-flow verification, implemented in Python without external solver dependencies. It is not an OpenFOAM/MFiX execution or a general pressure–velocity solver, and it does not analyze flow around the bracket.

## Equations and fixed SI inputs

For two infinite no-slip parallel plates with gap H, constant viscosity mu and a driving gradient G = -dp/dx > 0, the steady momentum equation reduces to `-mu*u'' = G`. The exact solution is `u(y)=G*y*(H-y)/(2*mu)`. Integrated flow per unit span is `q=G*H^3/(12*mu)` and wall-shear magnitude is `G*H/2`.

Analytical reference: [DOE NETL MFiX FLD01 verification documentation](https://mfix.netl.doe.gov/doc/vvuq-manual/main/html/fluid/fld-01.html), description/equations 3.1–3.2. KCEE implements its own reduced FV system; it does not reproduce that product's multidimensional implementation.

- Gap: 0.01 m; driving gradient: 0.1 Pa/m.
- Dynamic viscosity: 0.001 Pa·s; density: 1000 kg/m³. These are illustrative fixed values.
- Analytical peak: 0.00125 m/s; mean: 0.0008333333 m/s.
- Analytical flow per span: 8.3333333e-6 m²/s; wall shear: 0.0005 Pa.
- Reynolds number uses analytical mean velocity and hydraulic diameter 2H: 16.6667.

## Numerical verification

Uniform cell-centred finite volumes use 16, 32, 64 and 128 cells across the gap. Interior diagonal entries are 2 and adjacent coefficients -1; wall diagonal entries are 3 using the half-cell distance and reflected no-slip ghost values. A tridiagonal direct solve computes cell-centre velocities. The analytical curve is evaluated independently at the same coordinates. For this stencil the relative maximum profile error is `1/N²` and relative integrated-flow error is `2/N²`, giving a second-order trend. The finest flow error is about 0.012207%. These are discretization errors, not physical uncertainty estimates.

Stored checks: fine profile/flow error, observed order, momentum force balance, equation residual and symmetry. Explicit tolerances are retained in JSON and the Markdown report. Mass continuity follows from the assumed streamwise invariance and zero transverse velocity; it is not a separate pressure-correction test. Flow rates are per unit span, not a claimed finite-width volumetric flow.

## Workflow and provenance

Start engineering services, select Run CFD channel benchmark, and inspect the registered result. Change profile resolution to compare the numerical/analytical curves and review refinement errors. The 200 × 20 × 10 mm STL is only a display envelope: width is illustrative and sidewall drag is excluded. Structural/thermal bracket controls and the study assistant remain unavailable for this different study kind.

`POST /runs/cfd-benchmark` accepts an empty body or empty JSON object; parameters are rejected. The API reproduces the worker result and requires all checks before registration. This transport reproduction uses the same numerical implementation, while verification uses the analytical reference and refinement/conservation identities. Artifacts include result, fixed requirements, CFD details, velocity CSV, readable report, a provenance-only voice-summary artifact and the display STL. The manifest records adapter/solver-source and every artifact hash. Altered worker results or stored CSV files fail verification.

The CFD Compose service is internal-only, read-only, CPU/memory bounded and included in engineering start/stop controls. No model inference or network service is used by the numerical solve. General 2D/3D flow, turbulence, arbitrary geometry, entry conditions, thermal-fluid coupling and engineering acceptance remain future work.
