# Saved-run workspace
Set both database passwords in .env, then `docker compose --profile viewer up --build -d`. Open http://localhost:5173. Create a bracket demo or select a saved run. CLI runs must first be imported using the run-registry guide.

The workspace shows paginated history, selected thickness/mass, analytical stress/deflection/factor of safety, assumptions and provenance. Selection verifies all registered artifacts through the API, then independently checks downloaded STL/result bytes against stored hashes before display. Integrity is distinct from engineering validation; every sample result remains unvalidated. Files stay local.

Switching runs clears the previous model/results and cancels pending requests. Verification failure shows an error without rendering the failed model. Local STL imports clear saved-run results and are explicitly unverified. Reports/manifests can be downloaded for review; artifact download endpoints remain raw files.

The Vite preview service proxies /api to the local API container, avoiding browser CORS configuration. This is a local development workspace, not a public production server. Local Node development uses `npm ci`, `npm test`, `npm run dev`; API target defaults to localhost:8000 or set API_PROXY_TARGET. Dependencies and image digest are pinned after ARM64 build verification.

Regression checks: `python3 scripts/check_integration.py --viewer` builds an isolated database/API/viewer stack, checks the API proxy including run creation and artifact downloads, then cleans up its own test volume. Viewer client tests run during its image build.

Native creation: provision PicoGK, start `python3 scripts/start_geometry_worker.py`, and refresh. Select Native PicoGK, then Create bracket demo. An unavailable worker disables native creation. Baseline mesh is a separate explicit choice.
