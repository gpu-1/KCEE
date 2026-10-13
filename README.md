# Kaobra Computational Engineering Engine
Private computational engineering platform for Apple Silicon. Initial scaffold, not a validated engineering product.

## Run the bracket demonstrator
```sh
python3 -m kcee.demo --output runs
python3 -m unittest discover -s tests -v
```
Each run creates a watertight L-bracket STL, analytical cantilever screening, thickness search, report, speech summary, and SHA-256 provenance manifest. Geometry defaults to a deterministic mesh fallback. Native PicoGK generation with mounting holes is available using `--geometry-backend picogk`; see [native setup](host/macos/picogk/README.md). FEA remains pending. No AI or solver result is fabricated.

## Local services
```sh
cp .env.example .env
# Set POSTGRES_PASSWORD and KCEE_APP_DB_PASSWORD in .env
 docker compose config
 docker compose up --build -d
```
API: http://localhost:8000/health. Viewer: http://localhost:5173 (run with `docker compose --profile viewer up --build -d`). POST `/runs/bracket` with `{}` to run the demo; artifacts are served under `/artifacts/<run-id>/`.

The viewer browses saved runs, creates bracket demos and shows verified geometry, analytical results, assumptions and provenance. Local STL imports remain available. See [viewer guide](docs/tutorials/viewer.md). Container startup needs downloaded dependencies; the Python demo runs offline with the standard library. Run persistence and integrity checks are implemented; real solver adapters remain pending. See [run registry](docs/operations/run-registry.md). See [architecture](docs/architecture/overview.md), [installation](docs/operations/install-macos.md), [demo](docs/tutorials/bracket.md), and [roadmap](docs/ROADMAP.md).
