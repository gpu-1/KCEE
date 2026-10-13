# ADR-0006: Verify the solver before bracket analysis
Status: accepted.

Use an isolated, pinned ARM64 CalculiX worker and a quadratic-solid cantilever benchmark with independent analytical comparison, mesh refinement and force balance. Store raw solver outputs and hashes. Label the benchmark separately from bracket engineering validation; do not apply its acceptance or peak stress to a different geometry.
