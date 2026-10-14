# Finer mesh exploration

Exploratory follow-up to verified saved study `c072e470-2fd9-452a-aee2-19d9cb2a2329` using the same .35 mm PicoGK STL, 25° classification, ideal clamp, 100 N clipped-strip loading and linear-elastic material. Saved studies are unchanged.

| Target | Nodes | Elements | Loaded displacement | Global stress peak |
|---|---:|---:|---:|---:|
| 1.5 mm (saved) | 35684 | 19124 | 0.790682 mm | 217.242 MPa |
| 1.3 mm (exploratory) | 47921 | 26442 | 0.794338 mm | 232.729 MPa |

Displacement changes by 0.462%; global peak stress changes by 7.129%. This does not establish stress convergence. The 1.2 mm candidate has 59,797 nodes, exceeding the existing 50,000-node solve budget, so it was meshed but not solved. The 1.3 mm source load-strip area error remains about 3.019%.

Full precision, regional peaks, energy checks, source manifest/STL identity, adapter/solver hashes and exploratory archive hash are in [the evidence report](finer-mesh-exploration.json). Local mesh/solver artifacts are retained under `.local/studies/finer-solve-20261014/`. No engineering acceptance or allowable stress is claimed.

The bounded probe runs inside the structural image with `scripts/probe_finer_mesh.py --run-id <saved-bracket-study> --output <new-output-directory> --solve`. It requires API access and the project modules on PYTHONPATH; keep the existing resource limits.

The extracted shared solver procedure independently reproduces the saved 1.5 mm mesh summary within relative/absolute tolerances of 1e-8. All 60 standard-library regression tests pass.
