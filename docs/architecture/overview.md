# Architecture
Native macOS: local Metal inference (llama.cpp), PicoGK (.NET/Apple Silicon), Kokoro audio output, whisper.cpp input. Containers: orchestration API, PostgreSQL/pgvector, Three.js viewer, future isolated structural/thermal/CFD/Cantera workers.

Flow: requirements → deterministic engineering rules → geometry → mesh → solver → manufacturing checks → optimization → validation → artifact/provenance → viewer and concise voice feedback. AI proposes structured changes; deterministic checks and human validation gate engineering acceptance.

Current executable path: requirements → analytical thickness search → fallback STL → JSON/Markdown/manifest. No runtime cloud APIs. Containers and model provisioning need network downloads; runtime egress isolation is not enforced by this initial bridge network.

Host URLs are configuration, not working integrations. `host.docker.internal` resolves the Mac from Docker Desktop. A service bound only to loopback may be unreachable from containers; use an authenticated restricted host gateway before enabling adapters. Do not expose unauthenticated model/audio services to the LAN.
