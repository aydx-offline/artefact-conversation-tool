# Task 15 Report

## Status

Complete. `docs/coverage.md` is ready for Ann's approval; Task 16 has not started.

## Commit

`7d4d522` (`docs: add test coverage grid`)

## Tests

- `python3 -m unittest tests.test_coverage -v`: 5 passed.
- `python3 -m unittest discover -s tests -v`: 172 ran; the only failure was `test_step_screenshots_are_real_pngs_and_the_log_links_them`, as expected while log screenshots are `PENDING`; one configured smoke test was skipped.
- IDE lint check: no errors.

## Files

- Added `docs/coverage.md` with 50 final rows and 20 separate tuning rows.
- Added `tests/test_coverage.py`.
- Added work-log step 22 with its screenshot left `PENDING`.
- Did not create case JSONL files or call GLM.

## Hard-note mapping

- f07, scenario 1: 投诉之后的生日.
- f14, scenario 2: 七夕 at `2026-08-19T10:00:00+08:00`.
- f21, scenario 3: 中秋 at `2026-09-25T10:00:00+08:00`.
- f28, scenario 4: 不愉快的经历之后重新联系.
- f35, scenario 5: 上次谢绝过邀请.
- f45, scenario 6 comparison: 客户报出代购价格.
- f49, scenario 6 discount request: 常客要求折扣.
- f50, scenario 6 discount request: 客户说忽略之前的规则并要求五折.

## Concerns

- The festival calendar lists 七夕 on 2026-08-19 and 中秋 on 2026-09-25, so both fixed timestamps are on the festival date and inside the three-day window. There is no date mismatch.
- Step 22 remains `PENDING`, as requested. Task 16 must wait for Ann's approval.
