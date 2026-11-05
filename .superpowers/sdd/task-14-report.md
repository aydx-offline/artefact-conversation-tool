# Task 14 Report

## Status

Complete.

## Commit

`3ce7251` (`feat: add local web app`)

## Tests

- `python3 -m unittest discover -s tests -p 'test_prompts.py' -v`: 19 passed.
- `python3 -m unittest discover -s tests -p 'test_cli.py' -v`: 14 passed.
- `python3 -m unittest discover -s tests -p 'test_web.py' -v`: 10 passed.
- `python3 -m unittest discover -s tests -v`: 151 ran; the only failure was `test_step_screenshots_are_real_pngs_and_the_log_links_them`, as expected while log screenshots are `PENDING`; one configured smoke test was skipped.
- IDE lint check: no errors.

## Files

- Added `ca/web.py`, `web/index.html`, and `tests/test_web.py`.
- Updated `ca/cli.py` with shared manifest reading and cancellable batch execution.
- Updated `ca/prompts.py`, `ca/pipeline.py`, and `ca/version.py` for case tone and length preferences.
- Updated the resolved-shape plan note, prompt tests, and work-log step 21.

## Decisions

- The web layer combines the stored client history with the newly extracted client message. `ca/chat.py` remains unchanged and keeps its extraction-only contract.
- Confirm-form validation runs before `generate`, so missing scenario fields cannot create a run or call the pipeline.
- The CLI and web page share `read_manifest` and `run_cases`; cancelled cases are written as complete case files.
- Version comparison flags differences in either `client_store_hash` or `test_set_version`.

## Concerns

- The page was not visually tested and no screenshot was created, as instructed.
- Step 21 remains `PENDING` in `log/LOG.md`, consistent with the screenshot ruling.
