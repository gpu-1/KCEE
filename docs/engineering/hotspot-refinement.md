# Targeted CFD hotspot refinement

A paired fine-background sensitivity study adds two level-5 root/upright volume boxes to the existing fine v2 case. The background, far boundaries, Re=6 physics, global surface/bore controls and 3000 iterations are fixed. Local topology, snapping and achieved layer coverage can change.

| Case | Cells | Extruded candidate faces | Maximum skewness |
|---|---:|---:|---:|
| wall-bore-history-fine-v2 | 239644 | 96.868% | 3.454433 |
| wall-hotspot-history-v1 | 266294 | 97.070% | 3.474672 |

Both meshes pass standard `checkMesh` and the fixed 3.5 skewness recipe. All source solver, bore, native analytical benchmark, native stress integration and final history agreement checks pass. All six iterative-settling criteria pass for both histories.

| Quantity | Pressure change | Viscous change | Total change |
|---|---:|---:|---:|
| Force | 0.1244% | 0.1418% | 0.0431% |
| Moment about origin | 0.2004% | 0.2701% | 0.1255% |

Changes are norms of target-minus-baseline vectors divided by the targeted vector norm. They are sensitivity measures, not error estimates. The paired local refinement changes global loads relatively little, but does not resolve the earlier medium-to-fine mesh sensitivity or establish a convergence order. Engineering acceptance remains pending.

## Immutable evidence

- Baseline: `0bd937a6-5a73-4c28-a1a3-a3a79f8ced46`
- Target: `16eb44f0-af05-4bc4-baef-9f90b8c52a3a`
- Paired native report: `ad08c07d-33a8-4218-9b79-ee5d546162ac`
- Report manifest SHA-256: `4d509155446f8696e041aaafcad05692061ad8f6acf5aaee53714b1e53f6dafa`

The report retains raw native stresses, all six signed load changes, history CSV with 6000 source/iteration rows, source manifests and implementation fingerprints. The website provides paired charts, reports, replay verification and the Refine CFD hotspots job with cancellation/retry.
