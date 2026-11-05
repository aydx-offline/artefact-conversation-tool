# Task 3 report: Brand data in Chinese

## Built
- `data/brand/`: `voice.md` (Chinese brand voice prose), `rules.json`, `menus.json` (8 scenario labels from `SCENARIOS`, 5 verbatim Chinese strategies each), `catalog.json` (4 products), `events.json` (object keyed by `winter`, `spring`; spring capacity `null`), `festivals.json` (20 rows).
- `ca/brand.py`: `Brand` dataclass and `load_brand(root)`.
- `tests/test_brand.py`: shape, rules, Chinese prose (voice, menus, catalog text), event capacity.
- `log/LOG.md`: row 10, screenshot cell `PENDING: screenshots/step-10-brand-data.png`.

## RED
`python3 -m unittest tests.test_brand` -> `ModuleNotFoundError: No module named 'ca.brand'`, FAILED (errors=1).

## GREEN
`python3 -m unittest tests.test_brand` -> Ran 4 tests, OK.

Full suite: 21 tests, 1 failure, only `test_step_screenshots_are_real_pngs_and_the_log_links_them` (by design).

## Self-review
- Menu strings match the brief's table verbatim; keys are the `SCENARIOS` labels, not duplicated.
- `voice.md` passes `prose_is_chinese` with `Chengbai`. No comments in code.
- Catalog `line`, `materials`, `care` and event `place` were not specified; I invented fictional Chinese values (line names 云纹/素缎/月光/月白系列).
- Events is a dict keyed by id, catalog a list, festivals a list of `{name, date}`; the brief did not fix these shapes beyond the test's needs.

## Concerns
- The brief's Step 5 says "Do not commit"; the task prompt said to commit, so I committed.
- Row 10 stays PENDING until `log/capture_step.py` runs.
