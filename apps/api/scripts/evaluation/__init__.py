"""The evaluation runner: the benchmark through the real pipeline, scored step by step.

Offline tooling (`make eval-smoke`, `make eval`). It lives under `scripts/`, never in
`holdsup/`, so no request path can import it (eval/CLAUDE.md).
"""
