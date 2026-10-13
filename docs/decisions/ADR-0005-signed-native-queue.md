# ADR-0005: Signed local queue for native geometry
Status: accepted.

Connect Docker orchestration and native PicoGK through a shared filesystem job queue. Authenticate jobs/results/heartbeat with a local HMAC key, constrain request shape and native execution, and verify downloaded STL bytes. This keeps host service access local without exposing a network listener. Tradeoffs: shared local storage, single-worker throughput and explicit startup after reboot. Container API and local host account remain trusted. A future remote deployment would require a different authenticated transport.
