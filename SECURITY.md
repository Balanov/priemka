# Security policy

## Scope

`priemka` sends questions to the system under test and writes what came back
into a report. Two things follow from that, and they are the whole security
story of this tool:

1. **Answers can contain sensitive data.** A report may contain an excerpt of a
   real answer, including fragments your system should not have revealed. Treat
   `acceptance-report.json` and `acceptance-report.md` as sensitive artifacts:
   keep them out of public CI logs, restrict access to the repository, and set a
   retention period.
2. **The tool holds no credentials.** It does not need any: it calls the
   address in `system.target` with a question and reads the answer. There is no
   account, no telemetry and no network call other than the one you configured.

## What the tool does not do

- It does not send anything anywhere except the configured target.
- It does not store, proxy or forward answers to third parties.
- It does not execute code from the system under test.
- It does not modify the system under test: only `POST` with a question.

## Reporting a vulnerability

Report privately to `office@balanov.pro`. Include the pack, the target and the
reproduction. Fixes for confirmed issues ship as a patch release, and the report
is credited unless you prefer otherwise.

## Hardening a CI run

- Run the gate suite against a staging system, never against production data.
- Restrict the job's artifact retention: `retention-days: 3` is usually enough
  for a verdict and a signature.
- If the answers themselves are sensitive, run the suite against a fixture
  (`--fixture`) for the pull request and against the live service only on the
  release branch.
