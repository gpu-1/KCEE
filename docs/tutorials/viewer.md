# Saved-run workspace
Set both database passwords in .env, then `docker compose --profile viewer up --build -d`. Open http://localhost:5173. Create a bracket demo or select a saved run. CLI runs must first be imported using the run-registry guide.

The workspace shows paginated history, selected thickness/mass, analytical stress/deflection/factor of safety, assumptions and provenance. Selection verifies all registered artifacts through the API, then independently checks downloaded STL/result bytes against stored hashes before display. Integrity is distinct from engineering validation; every sample result remains unvalidated. Files stay local.

Switching runs clears the previous model/results and cancels pending requests. Verification failure shows an error without rendering the failed model. Local STL imports clear saved-run results and are explicitly unverified. Reports/manifests can be downloaded for review; artifact download endpoints remain raw files.

The Vite preview service proxies /api to the local API container, avoiding browser CORS configuration. This is a local development workspace, not a public production server. Local Node development uses `npm ci`, `npm test`, `npm run dev`; API target defaults to localhost:8000 or set API_PROXY_TARGET. Dependencies and image digest are pinned after ARM64 build verification.

Regression checks: `python3 scripts/check_integration.py --viewer` builds an isolated database/API/viewer stack, checks the API proxy including run creation and artifact downloads, then cleans up its own test volume. Viewer client tests run during its image build.

Native creation: provision PicoGK, start `python3 scripts/start_geometry_worker.py`, and refresh. Select Native PicoGK, then Create bracket demo. An unavailable worker disables native creation. Baseline mesh is a separate explicit choice.

## Structural results and geometry checks

Follow the [current bracket walkthrough](bracket.md) for the native generation/FEA sequence. Solver colors explicitly select displacement in mm or averaged nodal von Mises stress in MPa. Deformation scale is a display setting; numerical results remain unchanged. Load/support markers stay on the undeformed reference and show nominal regions. Numerical checks and hole measurements have explicit validation limitations.

## Model list management

Select a saved model and choose Remove from list. The confirmation shows its name and UUID. Confirming hides only that run; cancel leaves the list unchanged. Show removed models switches to hidden entries. Select one and confirm Restore to list to return it. This preserves files, provenance and independent parent/child results. Removal is disabled during job creation.

## Compare saved bracket studies

Select a Bracket FEA run and choose Use as comparison reference, then select another Bracket FEA run. Both records/artifacts are verified before displaying geometry, mesh settings, load-patch area, displacement and unconverged peak stress. Clear comparison removes the reference. The reference lasts for the current viewer session. Different geometry/meshing/load discretization prevents attributing changes to one factor.

Download comparison (JSON) exports the verified reference/selected source hashes, full-precision comparison values, export time and validation limitations. The comparison file is a derived review artifact; keep the original run bundles for complete solver evidence. Browser download handling depends on the browser used.
