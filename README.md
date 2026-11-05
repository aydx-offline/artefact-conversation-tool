# CA message app

This local tool drafts three Chinese WeChat messages for a fictional luxury house. Copy `.env.example` to `.env` and add the GLM model names and API key. Langfuse settings are optional.

## Docker

Build and run the web page with the challenge commands:

```sh
docker build -t ca-messages .
docker run --env-file .env -p 8765:8765 -v "$PWD/runs:/app/runs" -v "$PWD/data:/app/data" ca-messages
```

Open `http://127.0.0.1:8765`. The image listens on `0.0.0.0` so Docker can publish the service; bind the published port to host loopback to keep it off the local network:

```sh
docker run --env-file .env -p 127.0.0.1:8765:8765 -v "$PWD/runs:/app/runs" -v "$PWD/data:/app/data" ca-messages
```

Run the default tuning batch through the CLI:

```sh
docker run --rm --env-file .env -v "$PWD/runs:/app/runs" -v "$PWD/data:/app/data" ca-messages python -m ca batch
```

Project guidance and records are in `AGENT.md`, `log/LOG.md`, `docs/rubric.md`, and `cases/cases.csv`. Do not publish the brief. Submission is due 2026-11-09.
