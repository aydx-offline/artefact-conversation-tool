# CA message app

This command-line tool drafts three Chinese WeChat messages for a fictional luxury house. Copy `.env.example` to `.env` and add the GLM model names and API key. Langfuse settings are optional.

## Run one case

```sh
python3 -m ca generate --case cases/example.json
```

This prints the three messages and the folder under `runs/` that keeps every prompt and reply. To try another input, copy `cases/example.json` and change the client, scenario, history, or products. Clients are in `data/clients.json`, products in `data/brand/catalog.json`.

## Run, score, and export

```sh
python3 -m ca batch                                  # the 20 tuning cases
python3 -m ca batch --cases cases/inputs.jsonl       # the 50 final cases
python3 -m ca evaluate --run <run_id>                # judge every candidate
python3 -m ca report --run <run_id>                  # good cases, scores, problems
python3 -m ca export --run <run_id>                  # write cases/cases.csv
python3 -m ca export --before <run_id> --after <run_id>
```

Architecture diagrams are in `docs/architecture.md`.

## Docker

```sh
docker build -t ca-messages .
docker run --rm --env-file .env -v "$PWD/runs:/app/runs" -v "$PWD/data:/app/data" ca-messages python -m ca batch
```

Any command above works after `ca-messages`, for example `python -m ca generate --case cases/example.json`.

Project guidance and records are in `AGENT.md`, `log/LOG.md`, `docs/rubric.md`, and `cases/cases.csv`. Do not publish the brief. Submission is due 2026-11-09.
