# Local root mesh refinement

Exploratory follow-up to saved study `c072e470-2fd9-452a-aee2-19d9cb2a2329`. Source STL, 25° classification, ideal rear clamp and 100 N clipped-strip loading are retained. Global mesh target is 1.5 mm; a local box covers x=[−1,3], y=[−1,31], z=[2.5,5] mm. Production study defaults and saved artifacts are unchanged.

| Root target | Nodes | Loaded displacement (mm) | Global peak (MPa) |
|---|---:|---:|---:|
| No local box (saved) | 35684 | 0.790682 | 217.242 |
| 0.9 mm | 37810 | 0.791973 | 328.251 |
| 0.75 mm | 39447 | 0.792300 | 334.430 |

Both refined solves remain below the 50,000-node budget, balance the applied force, and pass the energy/work identity check. The load-strip area is unchanged at 131.696532 mm². Displacement changes by less than 0.21%, while global peaks rise by more than 51% relative to the saved mesh. This shows significant sensitivity near the root; it does not prove stress convergence or establish a physical allowable. Two local refinement levels are insufficient to declare acceptance.

Source hashes, full precision, regional peaks, energy, centroid locations, solver/adapter identity and verified archive hashes are in [the evidence report](root-refinement-exploration.json). Raw archives/logs remain under `.local/studies/root-refinement-20261014/`. The source geometry and existing saved study are not modified.

Reproduce in the structural image using `scripts/probe_root_refinement.py --run-id <verified-bracket-study> --output <new-output-directory>`, with project modules on PYTHONPATH and the existing resource limits. The local targets are bounded to 0.9 and 0.75 mm, at 25° classification and 1.5 mm global target.
