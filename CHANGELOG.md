# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

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
