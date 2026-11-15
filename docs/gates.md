# Acceptance gate reference

Run the commands below from the repository root. Each uses synthetic local data, performs one failing check and prints `False`. The snippets call the check functions directly; they do not contact the configured target or run a model. They demonstrate detection, not a full acceptance verdict.

| Kind | Example pack gate ids | Failure caught | Smallest local reproduction |
| --- | --- | --- | --- |
| `not_empty` | answer-not-empty | Empty or whitespace-only answer | `python -c 'from priemka.checks import CHECKS; from priemka.targets import Answer; print(CHECKS["not_empty"]({}, Answer("")).passed)'` |
| `contains` | Not used in this pack | Required text absent | `python -c 'from priemka.checks import CHECKS; from priemka.targets import Answer; print(CHECKS["contains"]({"value": "required"}, Answer("absent")).passed)'` |
| `not_contains` | no-internal-instruction-leak | Forbidden text present | `python -c 'from priemka.checks import CHECKS; from priemka.targets import Answer; print(CHECKS["not_contains"]({"value": "private"}, Answer("private")).passed)'` |
| `matches` | answer-is-specific | Required regular expression does not match | `python -c 'from priemka.checks import CHECKS; from priemka.targets import Answer; print(CHECKS["matches"]({"pattern": "[0-9]+"}, Answer("words")).passed)'` |
| `citation` | answer-has-source | No recognizable source citation | `python -c 'from priemka.checks import CHECKS; from priemka.targets import Answer; print(CHECKS["citation"]({}, Answer("An unsupported answer.")).passed)'` |
| `refusal` | injection-refused | No refusal marker in the answer | `python -c 'from priemka.checks import CHECKS; from priemka.targets import Answer; print(CHECKS["refusal"]({}, Answer("Here is the requested data.")).passed)'` |
| `latency` | latency-budget | Measured latency exceeds the budget | `python -c 'from priemka.checks import CHECKS; from priemka.targets import Answer; print(CHECKS["latency"]({"max_ms": 1}, Answer("reply", latency_ms=2)).passed)'` |
| `cost` | Not used in this pack | Measured answer cost exceeds the budget | `python -c 'from priemka.checks import CHECKS; from priemka.targets import Answer; print(CHECKS["cost"]({"max_cost": 0.01}, Answer("reply", cost=0.02)).passed)'` |
| `pii_leak` | personal-data-refused | Personal-data pattern detected | `python -c 'from priemka.checks import CHECKS; from priemka.targets import Answer; print(CHECKS["pii_leak"]({}, Answer("sample@example.com")).passed)'` |
| `grounded` | answer-grounded | Required context terms absent | `python -c 'from priemka.checks import CHECKS; from priemka.targets import Answer; print(CHECKS["grounded"]({"context": "required"}, Answer("absent")).passed)'` |
| `determinism` | repeatable-answer | Normalized repeated answers differ | `python -c 'from priemka.checks import check_determinism; from priemka.targets import Answer; print(check_determinism({}, Answer("second"), Answer("first")).passed)'` |

Run the complete checked-in pack without a live endpoint:

```sh
python -m priemka run --pack examples/pack-rag.toml --fixture examples/fixture-rag.json
```

A successful command invocation can still exit 1 when the fixture fails acceptance. `priemka explain <kind>` describes the corresponding check and how to configure it.
