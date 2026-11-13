# Measurements

Every number below is produced by a script in this repository and stored as raw
JSON in [`bench/results/`](bench/results). Nothing here is a claim about model
quality: these are measurements of the harness itself.

## Reproduce

```bash
python bench/benchmark.py --out bench/results/local.json         # harness overhead, report stability
python bench/page_measurements.py                                # the numbers used on the product page
```

Both scripts record the Python build and the platform, so a run on another
machine can be compared line by line.

## Harness overhead

A run of the nine-gate example pack against the recorded fixture, repeated 25
times on the reference machine:

| Metric | Value |
|--------|-------|
| Gates per run | 9 |
| Repeats | 25 |
| Mean | 0.113 ms |
| Median | 0.090 ms |
| Min | 0.087 ms |
| Max | 0.586 ms |

## What the check costs next to the system it checks

The harness is measurement overhead, not the cost of the system under test. To
put both on the same scale, the same machine was asked one question from a local
model (`qwen3:8b` via Ollama), three times:

| Measurement | Value |
|-------------|-------|
| PRIEMKA — 9 acceptance gates, median | 0.090 ms |
| One call to a local model, median | 674.3 ms |

The acceptance run costs about **0.013 %** of a single model call. Against a
live service the run time is dominated by the service's own latency, and the
report records that latency per gate rather than hiding it.

## Local footprint

| Measurement | Value |
|-------------|-------|
| PRIEMKA — runtime dependencies | 0 bytes |
| PRIEMKA — implementation | 8 files, 1 134 lines of Python |
| pytest + requests + httpx + pyyaml (wheel sizes, PyPI) | 714 797 bytes |

The comparison row is the measured sum of the wheel sizes of the four packages a
typical Python test stack pulls in, downloaded with
`pip download --no-deps pytest requests httpx pyyaml`. PRIEMKA needs none of them.

## Report stability

| Metric | Value |
|--------|-------|
| Repeats | 5 |
| Report digest identical across runs | yes |
| Verdict identical across runs | yes |
| Digest | `f98ef351a798de4ee4c14d6c022a2a351010592b6ca252279bfb13b1af92e04a` |
| Markdown report size | 3 615 bytes |

The digest is computed over the canonical JSON of the report with the timestamps
removed. Two runs over the same pack and the same fixture produce the same
digest, which is what makes the signature in the report meaningful: it identifies
*what was checked*, independently of when it was checked.

## Inputs

| File | Bytes | SHA-256 |
|------|------:|---------|
| `examples/fixture-rag.json` | 2 315 | `e530e258435b50c6aeea1cde7062c0e039c4b2bea224989aef50419b9cdfb744` |
| `examples/pack-rag.toml` | — | `53265422c7e637f6a9618169745d3e094fde3dbe0913251121e64945cdb36a63` |

## What is not measured here

- Answer quality of any model. The tool measures claims you wrote, against
  answers you supplied or recorded.
- Throughput of the system under test. The harness never batches requests and
  never hides latency: each gate reports the delay it observed.
- Statistical significance across model versions. `priemka` is a gate runner,
  not a benchmark; use the `determinism` and `grounded` gates to catch
  regressions between two versions of your system.

Reference machine: `Windows-11-10.0.28020-SP0`, CPython 3.14.7.
