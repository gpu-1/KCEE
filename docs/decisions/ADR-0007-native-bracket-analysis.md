# ADR-0007: Trace structural analysis to the native design
Status: accepted.

Mesh the verified native STL rather than substituting an analytical bar or regenerated ideal CAD. Preserve the source design as parent and its STL/manifest hashes. Use explicit idealized clamp/load conditions and a bounded refinement study. Keep numerical checks and engineering validation distinct, and retain diagnostic artifacts when meshing/solving fails.
