# ADR-0001: Hybrid macOS and containers
Status: accepted initial architecture.

Keep Metal AI and PicoGK native; containerize portable orchestration/data/solver services. This preserves Apple Silicon acceleration and provides a migration path to Mac Studio. Tradeoff: native dependencies require reproducible version manifests and a restricted gateway, rather than a single all-in-one container.

References: https://github.com/ggml-org/llama.cpp ; https://picogk.org/doc/setup.html ; https://docs.docker.com/desktop/features/networking/networking-how-tos/
