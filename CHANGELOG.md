# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] — 2026-11-14

### Added

- `bench/compare_footprint.py` measures the install footprint of the tools this
  one is compared with — DeepEval, promptfoo, Ragas, Giskard — and of PRIEMKA
  itself, so the "zero runtime dependencies" claim can be re-checked instead of
  taken on faith. The numbers and the method are in `BENCHMARKS.md`.
- The product page and the READMEs now state the position explicitly: verdict
  instead of a score, zero model calls, determinism as a property, the pack as
  the ceiling of coverage — together with the comparison and the limits. We are
  better at simplicity, speed and price, and not better at metric coverage,
  red teaming or platform features. Both halves are published.

### Changed

- `README.md` and `README_RU.md` open the value section with the engineering
  claim rather than a promise: one TOML file, one command, no model calls,
  0.090 ms per run, zero runtime dependencies, and an artifact a third party
  can check.

## [1.0.2] — 2026-11-14

### Added

- The package is published on [PyPI](https://pypi.org/project/priemka/). A trusted
  publisher (`Balanov/priemka`, workflow `release.yml`, environment `pypi`) lets
  GitHub Actions publish through OIDC, so `pipx install priemka` works without
  an API token and every release reaches PyPI from the same tag.
- `release.yml` accepts a manual run with an explicit tag, so a release can be
  rebuilt and re-published from `main` without moving a published tag.
- Install instructions now point at PyPI; the release wheel and
  `checksums.txt` stay attached to every GitHub release.

## [1.0.1] — 2026-11-14

### Fixed

- The published `1.0.0` artifacts were built before the signed-report work landed,
  so the wheel on the release page did not contain `priemka verify` nor the
  content-only report signature, even though the README described both. The
  artifacts are rebuilt from the current source and re-released here.

### Added

- `release.yml`: on a `v*` tag the workflow runs the tests, builds the wheel and
  the sdist, writes `checksums.txt` and publishes the GitHub release, so a
  release can be reproduced from the tag instead of assembled by hand.

## [1.0.0] — 2026-11-13

### Added

- Pack format v1: TOML pack with `system`, `stop_conditions` and `gates`.
- Eleven gate kinds: `not_empty`, `contains`, `not_contains`, `matches`,
  `citation`, `refusal`, `latency`, `cost`, `pii_leak`, `grounded`,
  `determinism`.
- Five measurement dimensions: quality, safety, access, performance,
  reproducibility.
- Readiness score (0–100) from weighted gates, plus a per-dimension breakdown.
- Fail-closed verdict: any failed blocking gate or an unreachable service means
  the system is not accepted. Exit code `1`.
- Reports: JSON and Markdown with per-gate evidence (answer SHA-256, latency,
  tokens, cost, excerpt), remediation hints and a signed report digest.
- Baseline comparison (`--baseline`): per-gate delta with regression detection.
- Recorded-fixture mode (`--fixture`): deterministic, offline runs for CI and
  demos.
- Commands: `init`, `run`, `rules`, `explain`.
- Benchmarks: harness overhead, report digest stability, input hashes.

### Notes

- Zero runtime dependencies; Python 3.11+.
- The report digest is computed over canonical JSON with timestamps removed, so
  the same pack and fixture always produce the same signature.
