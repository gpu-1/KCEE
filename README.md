# Kaobra Computational Engineering Engine
Private computational engineering platform for Apple Silicon. Working bracket demonstrator with native geometry, structural analysis and traceable results. Engineering validation remains pending.

## Run the bracket demonstrator
```sh
python3 -m kcee.demo --output runs
python3 -m unittest discover -s tests -v
```
Each run creates a watertight L-bracket STL, analytical cantilever screening, thickness search, report, speech summary, and SHA-256 provenance manifest. Geometry defaults to a deterministic mesh fallback. Native PicoGK generation with mounting holes is available using `--geometry-backend picogk`; see [native setup](host/macos/picogk/README.md). The first native-bracket FEA uses idealized clamp/load conditions; engineering validation remains pending. No AI or solver result is fabricated.

## Start the provisioned local workspace
```sh
python3 scripts/start_kcee.py
# After source changes, rebuild as well:
python3 scripts/start_kcee.py --build
```
This starts the native PicoGK queue worker and the database, API, viewer and structural containers, waits for container health, and saves a unique readiness report under `.local/readiness/`. Configure `.env` and provision PicoGK first. Re-running is safe; startup failures retain existing services and data. This checks the geometry/FEA demonstrator. AI, voice and other physics integrations remain pending.

To stop the workspace while retaining its data:
```sh
python3 scripts/stop_kcee.py
```
This stops containers and requests graceful shutdown of the verified project geometry worker. Restart with the startup command above.

## Local services
```sh
cp .env.example .env
# Set POSTGRES_PASSWORD and KCEE_APP_DB_PASSWORD in .env
 docker compose config
 docker compose up --build -d
```
API: http://localhost:8000/health. Viewer: http://localhost:5173 (run with `docker compose --profile viewer up --build -d`). POST `/runs/bracket` with `{}` to run the demo; artifacts are served under `/artifacts/<run-id>/`.

The viewer browses saved runs, creates bracket demos and shows verified geometry, analytical results, assumptions and provenance. Local STL imports remain available. See [viewer guide](docs/tutorials/viewer.md). Container startup needs downloaded dependencies; the Python demo runs offline with the standard library. Run persistence, integrity checks and the CalculiX structural adapter are implemented. AI, voice, thermal, CFD and chemistry integrations remain scaffolds. See [run registry](docs/operations/run-registry.md). See [architecture](docs/architecture/overview.md), [installation](docs/operations/install-macos.md), [demo](docs/tutorials/bracket.md), and [roadmap](docs/ROADMAP.md).

For native viewer generation, provision PicoGK and run `python3 scripts/start_geometry_worker.py`; then refresh the viewer. See [native worker](docs/operations/native-geometry-worker.md).

Run the structural verification worker with `docker compose --profile viewer --profile fea up --build -d --wait`, then choose Run cantilever benchmark. See [benchmark scope and checks](docs/engineering/structural-benchmark.md). This is separate from bracket validation.

For the actual native bracket, select its saved run and use Analyze selected bracket. This creates a traced structural child run using the original STL. See [assumptions and numerical limits](docs/engineering/bracket-structural-study.md). Engineering validation remains pending.

The viewer includes separate displacement/stress colors, explicit deformation scales, nominal load/support markers, numerical checks and native bore measurements. The ? icon beside Geometry explains the two generation options. Remove from list asks for confirmation and retains artifacts; Show removed models allows restoration. See [backup/restore](docs/operations/backups.md), [geometry refinement](docs/engineering/geometry-refinement.md) and [Mac Studio readiness](docs/operations/migration.md).

## Website service controls

After `python3 scripts/start_kcee.py`, the website's Engineering services panel can start native PicoGK and the structural worker or stop them with confirmation. The website, API and database stay running, so saved studies remain readable and services can be restarted. Controls use a separate local signed-queue supervisor; no Docker socket or signing key is exposed to browser code. Restart the supervisor with the startup command if controls show unavailable.
