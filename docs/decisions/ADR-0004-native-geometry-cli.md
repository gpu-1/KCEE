# ADR-0004: Native PicoGK process boundary
Status: accepted.

Use a pinned, bounded command-line process for native geometry before implementing network access. Keep the container API baseline explicit. Host-generated runs are imported into the same registry and viewer. Preserve kernel/configuration/library hashes and actual voxel volume. Fail explicitly when native execution is unavailable. A future authenticated gateway will enable direct viewer/API native generation.
