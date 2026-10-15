# CFD verification worker

Internal port 8007. `GET /health` reports reduced plane-Poiseuille scope. Empty `POST /benchmark` runs four fixed cell-centred finite-volume grids and returns analytical comparisons, checks and limits. No arbitrary input parameters are accepted.

The container uses the pinned project Python base, runs with a read-only filesystem and no host port, and is part of the `fea` engineering profile/start-stop controls. See `docs/engineering/cfd-benchmark.md` for equations, tolerances, scope and source attribution.

This first verified worker is a reduced fully developed laminar momentum benchmark, not a general 3D CFD adapter.
