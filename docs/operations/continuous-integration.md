# Automated repository checks

.github/workflows/ci.yml runs on main pushes, pull requests and manual dispatch. It checks standard-library tests on Python 3.9/3.11, locked viewer dependencies/tests/build on Node 22, and the disposable Compose full-stack suite on Linux ARM64. The integration script creates a separate project with generated database credentials and cleans up its own volume.

Actions are pinned to commit hashes resolved from official action tags. Repository permissions are contents:read and checkout does not persist credentials. Runtime limits and cancellation of superseded runs bound execution. Repository settings can independently restrict whether Actions run.

CI uses committed source and synthetic test data. Local ignored models, credentials, runtime binaries and engineering runs are not included. Native macOS PicoGK generation, Metal AI, voice and real bracket reproduction are not validated by Linux CI; use documented local checks and migration acceptance tests. CI success does not establish engineering validation.

GitHub runner reference: https://docs.github.com/en/actions/reference/runners/github-hosted-runners

Integration failures emit a bounded public workflow annotation, with escaping tests for annotation text. Detailed logs remain in GitHub. Disposable API/test containers run with the invoking host UID/GID so Linux bind-mounted files can be cleaned up. The test checkout excludes .local and pre-creates its geometry mount; production container users are unchanged.
