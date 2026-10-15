# Docker
Use docker compose config before startup. Base services are API and PostgreSQL; viewer uses profile viewer. Database has no host port. API and viewer publish only on 127.0.0.1. postgres volume is persistent; runs is a repository-relative bind mount.

API Python base image and pgvector image are digest-pinned; API requirements.lock freezes tested transitive versions. API/database were built/tested on ARM64. Viewer npm lock and image digest are recorded; saved-run client tests and ARM64 build verification accompany the viewer milestone. The internal bridge is not air-gapped: provision dependencies first, then enforce firewall/egress policy for offline operation. Native host calls are planned; configured URLs currently unused.

The `fea` engineering profile also starts the internal CFD verification worker (port 8007 within the Compose network, no host port). Engineering Start/Stop controls include CFD. Its first supported case is the fixed reduced plane-Poiseuille benchmark; see `docs/engineering/cfd-benchmark.md`.
