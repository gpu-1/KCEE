# Implementation roadmap
1. API dependencies and API/database image digests locked; ARM64 registry integration tested. Viewer dependencies/image digest now locked; saved-run viewer builds and client checks included.
2. Run persistence, append-only history and integrity checks implemented. Next: local knowledge ingestion/embedding model.
3. Restricted native gateway; Metal AI structured proposal API and runtime manifests.
4. Native PicoGK bracket, mounting holes, fillet-like voxel transition and closed-mesh/volume checks implemented. Signed native queue now connects viewer/API generation. Native bracket structural FEA implemented. Three-resolution geometry volume/topology study recorded. Next: local feature accuracy and FEA sensitivity to geometry resolution.
5. CalculiX cantilever verification benchmark implemented. Native-STL Gmsh/C3D10 bracket study now implemented with ideal clamp/load conditions. Next: stronger formulation/geometry convergence checks, realistic mounting/contact and thermal worker; then FEniCSx, SU2/OpenFOAM and Cantera profiles with validated examples.
6. Materials/process rule database and solver-backed optimization.
7. Kokoro priority queue/audio playback, whisper.cpp opt-in recording/transcription.
8. Saved-run Three.js history/results/provenance implemented. Archived solver displacement/stress fields, load/support markers and numerical checks now displayed. Next: full failure provenance, backup/restore and Mac Studio acceptance test.
