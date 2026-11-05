# Task 16 report

## Status

Complete.

## Commit

`2c43a24` — `test: add frozen case sets`

## Tests

- `python3 -m unittest tests.test_cases`: 6 passed.
- `python3 -m unittest discover -s tests`: 178 run, 1 skipped, with only the expected screenshot test failing.
- `git diff --check`: passed.
- Linter: no errors in `tests/test_cases.py`.

## Files

- Expanded `data/clients.json` to 29 fictional profiles while preserving `lin`.
- Added 50 final cases in `cases/inputs.jsonl` and 20 tuning cases in `cases/tuning.jsonl`.
- Added case-set validation in `tests/test_cases.py`.
- Froze the version in `docs/coverage.md`.
- Added step 23 to `log/LOG.md` with its screenshot left `PENDING`.

## Client mapping

The 70 rows use 28 clients. Each used client serves two or three rows; every row matches the approved tier and relationship. Scenario 3 clients own the named product, and scenario 4 clients have an old visit date and a matching note. The original `lin` fixture remains available but is not assigned to a case.

## Concerns

The approved `t01` timestamp is five days before the 2026 Spring Festival date, outside the three-day resolver window. That case uses the schema's `occasion` override, `生日和春节`, so its resolved occasion still matches the approved coverage note without changing the table or festival calendar.
