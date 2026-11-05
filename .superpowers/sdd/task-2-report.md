# Task 2 report: case schema and validation

## Built
`ca/schema.py` (SCENARIOS, CaseError, Case, Message, prose_is_chinese, validate_case), empty `ca/__init__.py`, `tests/test_schema.py` (8 tests: brief's 6 plus scenario 6 subtype markers and bad timestamp/sender/ids), log row 9.

## RED
`python3 -m unittest tests.test_schema` -> `FAILED (errors=1)` (ModuleNotFoundError: ca).

## GREEN
`python3 -m unittest tests.test_schema` -> `Ran 8 tests ... OK`.
`python3 -m unittest discover -s tests` -> 17 tests, 1 failure: the by-design screenshot test (PENDING rows).

## Self-review
No extra code beyond the brief. Case fields after `timestamp` have defaults so the brief's test constructor works. Tests assert behavior and `.field`.

## Concerns
- Brief Step 5 says "Do not commit"; your instructions said commit, so I committed.
- The new log row is PENDING (screenshot not captured).
- Scenario 6 marker check accepts any client message with a marker for that subtype.
