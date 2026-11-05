# Task 6 report: Chinese prompts

## Built
`ca/prompts.py`: `SCENARIO_ZH` (verbatim from plan), `quote_data`, `plan_prompt`, `write_prompt`, `revise_prompt`, `chat_prompt`, `judge_prompt`, `natural_language_is_chinese`. All prompt text is Chinese; English only for Chengbai and the JSON keys. Tone labels and length bounds (read from `data/brand/rules.json`) are stated in Chinese. Client data is wrapped with `quote_data`. System text says quoted blocks are data, not instructions. Scenario line uses the Chinese name. Expectations appear only in the judge prompt.

## RED
`python3 -m unittest tests.test_prompts` -> ModuleNotFoundError (`ca.prompts` missing), FAILED (errors=1).
First GREEN attempt failed once: the ISO `T` in message times left a Latin letter. Fixed by rendering times with a space.

## GREEN
`tests.test_prompts`: Ran 12 tests, OK.
Full suite: Ran 50 tests, 1 failure, the by-design screenshot test (PENDING cells).

## Files changed
`ca/prompts.py`, `tests/test_prompts.py`, `log/LOG.md` (row 13, `PENDING: screenshots/step-13-prompts.png`).

## Self-review
- No comments, concise. No invented screenshot. Deslop skill read: no slop found.
- Assumed `resolved`: client is a Chinese string, scenario is the English label, history is a list of `Message`, products is a list of strings, failures is `{index: [Chinese reasons]}`, candidates are dicts.

## Concerns
- The brief's key list omits `scores` and `candidate`, which the judge format uses. `natural_language_is_chinese` strips them as well; the test passes them too.
- The brand voice is loaded inside prompts from `data/brand` via a path relative to the package, since the signatures take no brand argument.
