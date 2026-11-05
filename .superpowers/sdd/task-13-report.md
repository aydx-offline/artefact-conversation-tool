# Task 13 report

## Status

COMPLETE

## Commit

`1a7cdfa` (`Add CLI workflow`)

## Tests

- `python3 -m unittest tests/test_cli.py tests/test_schema.py tests/test_smoke.py -v`: 18 ran; 17 passed and 1 skipped.
- `python3 -m unittest discover -s tests -v`: 131 ran; only the expected screenshot-log test failed, and the live GLM smoke test skipped.
- Python compilation, `git diff --check`, and IDE lint checks passed.

## Files

- Added `.env.example`, `ca/cli.py`, `ca/__main__.py`, `tests/test_cli.py`, and `tests/test_smoke.py`.
- Updated `ca/schema.py`, `ca/store.py`, `tests/test_schema.py`, and `log/LOG.md`.

## Decisions

- Added `load_case` to `ca/schema.py`; both one-case JSON and batch JSONL rows use it.
- Runs default to `<cwd>/runs`; tests can pass `root` to `main`.
- Real runs use `WRITER_MODEL` for generation and `JUDGE_MODEL` for evaluation through `require_models`. Tests may inject `model`, with `judge_model` available when a separate fake is needed.
- `evaluate` appends `evaluate_case` rows. A `JudgeError` appends one failed row with its raw reply and continues.
- Export renders saved resolved values as readable text, puts the client name first, labels history speakers in Chinese, and writes UTF-8 with BOM for Excel.
- Submission export refuses tuning and incomplete runs. It overwrites the generated `cases/cases.csv`; comparison export likewise overwrites `cases/before-after.csv`.
- Before-and-after export allows different test-set versions because the spec allows version comparison; it includes only shared cases whose three-message output set changed.
- Readers merge `manifest.json` with `manifest.end.json`. Evaluation appends scores to the run's original generator-version directory.

## Concerns

- The expected screenshot test remains red because all log screenshots, including step 20, are intentionally `PENDING`.
- The live GLM smoke test was skipped because `GLM_API_KEY` and `WRITER_MODEL` were not set.

## Fix round 1

- Fix commit: `a873fda` (`Fix CLI edge cases`).
- Full suite: 139 tests; only the expected screenshot-log test failed, and the live GLM smoke test skipped.
- Remaining minor: telemetry wiring is inconsistent; `generate` traces a case, while `batch` and `evaluate` only flush.
