# CA message app

A command-line tool that drafts three Chinese WeChat messages for a Client Advisor at a fictional luxury house, 澄白 (Chengbai). It takes a client, a scenario, the conversation so far, and the products involved, and returns three candidates in different strategies. It covers six scenarios: birthday and festive greetings, product recommendation, post-purchase care, reactivation, event invitation, and price objection.

Everything here is fictional: the house, the clients, the products, and the chats. The written brief that set the challenge is not included and must not be published.

**Final result.** On the 50 test cases, 40 are good, as judged by a second model. The ten that are not are listed in `docs/evaluation-report.md`.

## Quick start

```sh
pip install -r requirements.txt          # Langfuse, optional
cp .env.example .env                     # then add the GLM key and two model names
python3 -m ca generate --case cases/example.json
```

This prints three messages and the folder under `runs/` that keeps every prompt and reply. To try another input, copy `cases/example.json` and change the client, scenario, history, or products. Clients are in `data/clients.json` and products in `data/brand/catalog.json`.

It was developed on Python 3.14 and runs in the Python 3.12 Docker image. Only the model calls need the network; the tests, `report`, and `export` run offline.

## Commands

```sh
python3 -m ca batch                                  # the 20 tuning cases
python3 -m ca batch --cases cases/inputs.jsonl       # the 50 final cases
python3 -m ca evaluate --run <run_id>                # judge every candidate
python3 -m ca report --run <run_id>                  # good cases, scores, problems; saved as report.txt in the run folder
python3 -m ca report --run <run_id> --out FILE       # save the report in FILE instead
python3 -m ca export --run <run_id>                  # write cases/cases.csv
python3 -m ca export --before <run_id> --after <run_id>
```

Each run is kept in `runs/<generator version>/<run_id>/` and is never overwritten. `runs/` is not committed.

## Tests

```sh
python3 -m unittest discover -s tests
```

The tests run on a fake model with no network. One test, `test_step_screenshots_are_real_pngs_and_the_log_links_them`, fails until every row of `log/LOG.md` has a screenshot.

## Docker

```sh
docker build -t ca-messages .
docker run --rm --env-file .env -v "$PWD/runs:/app/runs" -v "$PWD/data:/app/data" ca-messages python -m ca batch
```

Any command above works after `ca-messages`, for example `python -m ca generate --case cases/example.json`.

## What is in the repo

| Path | What it holds |
| --- | --- |
| `ca/` | The tool: the pipeline, code checks, judge, run store, Langfuse telemetry, and command line |
| `data/` | The brand (voice, rules, strategy menus, catalog, events, festivals), the clients, and the GLM price list |
| `cases/` | The 50 final and 20 tuning cases, `cases/cases.csv` with the 50 results, and `cases/example.json` |
| `tests/` | The tests |
| `log/` | The work log and its screenshots |
| `docs/` | The documents below |

## Submission documents

| Element | File |
| --- | --- |
| A. Work log | `log/LOG.md` |
| B. Methodology | `docs/methodology.md`, with the rubric in `docs/rubric.md` |
| C. 50 test cases | `cases/cases.csv` |
| D. Evaluation report | `docs/evaluation-report.md`, with the raw `report` output in `docs/final-run-report.txt` |
| E. Defects and next steps | `docs/defects-and-next-steps.md`, and `docs/future-implementation.md` |
| Bonus: architecture | `docs/architecture.md`, as Mermaid diagrams |

The design is in `docs/superpowers/specs/2026-11-04-ca-message-app-design.md`. Rules for agents working in the repo are in `AGENT.md`.
