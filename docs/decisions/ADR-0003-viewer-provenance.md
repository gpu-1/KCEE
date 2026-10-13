# ADR-0003: Verify saved-run artifacts before display
Status: accepted.

Use a same-origin /api proxy to reach the local orchestration API. Before rendering, verify registered provenance and independently hash the downloaded geometry/results in the browser. Cancel stale selection requests and clear prior results. Keep integrity labels separate from engineering validation. Local STL imports have no registered provenance.
