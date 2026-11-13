# Contributing

Thanks for considering a change.

## Ground rules

- **Zero runtime dependencies.** The tool must run on a stock Python 3.11+ with no
  install step beyond `pip install .`. A new dependency needs a reason that
  survives the question "can this be 40 lines of stdlib instead?".
- **Deterministic gates.** The same pack and the same answers must produce the
  same verdict and the same report digest. If a gate depends on the clock, the
  network or a random source, it belongs in the evidence, not in the verdict.
- **Evidence over opinion.** Every gate result carries what produced it: the
  answer hash, the latency, the excerpt. A gate that cannot show its evidence
  is not finished.
- **Fail-closed.** Do not add a path that skips a gate, softens a failure or
  turns an unreachable service into a pass.

## Workflow

```bash
python -m venv .venv && . .venv/Scripts/activate
python -m unittest discover -s tests -v
python bench/benchmark.py --out bench/results/local.json
```

If you change gate behaviour, update:

- `README.md` and `README_RU.md` (the gate table and the demo output),
- `CHANGELOG.md`,
- the benchmark raw results, if the numbers moved.

## Adding a gate kind

1. Implement the check in `priemka/checks.py` and register it in `CHECKS`.
2. Add its documentation to `GATE_DOCS` in `priemka/cli.py` so `priemka rules`
   and `priemka explain` describe it.
3. Add it to the starter pack in `priemka/policy.py` if it is a sensible default.
4. Cover it with a test that shows both the passing and the failing case.

## Commits and releases

- One logical change per commit, message in the imperative mood.
- Bump the version in `pyproject.toml` and `priemka/__init__.py` together.
- Add a `CHANGELOG.md` entry with the user-visible effect, not the diff.

## Reporting a problem

Open an issue with the pack you used, the target, the verdict you got and the
verdict you expected. If a gate failed, the report already contains the answer
that caused it — attaching `acceptance-report.json` is enough.

## Security

Do not open a public issue for a security problem. See [SECURITY.md](SECURITY.md).
