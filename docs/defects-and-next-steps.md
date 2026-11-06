# Defects and next steps

This file is submission element E. The steps behind each change are in `log/LOG.md`, and the final results are in `docs/evaluation-report.md`.

## Versions and what each change did

Each result carries the generator version that wrote it and the judge version that scored it. Judge versions differ between rows, so compare only within a row.

| Generator | What changed | Effect | Run |
| --- | --- | --- | --- |
| 0.1.1 | First live runs. The writer's reasoning was never off: Paratera ignores `thinking: disabled`. | 20 tuning cases took 22.7 minutes; 6 timed out and 2 failed a false length check. | tuning rounds 1 and 2 |
| 0.1.2 | `reasoning_effort` sent; two false checks fixed; timeouts not retried. | 68 seconds for 20 cases. | `0.1.2/20261106T152913749Z` |
| 0.1.3 | Date facts in the prompt; writer reasoning `high`. | Date errors in 2 cases, from 4. 14 of 20 good. | `0.1.3/20261106T155815344Z` |
| 0.1.5 | Answer her last message first; softer brand wording. | 16 of 20 good. | `0.1.5/20261106T163051818Z` |
| 0.1.7 | Chinese-only prompts and keys; product and event details; 180 characters. | 15 of 20 good; no English words. | `0.1.7/20261106T170439193Z` |
| 0.1.9 | Brand phrases and examples; revise back; optional length and reason. | 15 of 19 good; all 20 finished. | `0.1.9/20261106T175158630Z` |
| 0.1.10 | Colour of each purchase; a discount reply may offer care or a gift. | 16 of 19 good; the colour of her own piece no longer guessed. | `0.1.10/20261106T183623165Z` |
| 0.1.11 | First run of the final 50. | 40 of 49 good. Discount requests 1 of 5: the brand voice still said no gifts. | `0.1.11/20261106T184710617Z` |
| 0.1.12 | Brand voice fixed; free care bounded to one visit; birthday rule and purchase ages in code. | 39 of 49 good. Discount requests 3 of 5. | `0.1.12/20261106T191408482Z` |
| 0.1.13 | Prompts frozen. Code checks for English letters, newness, and discount replies; tildes stripped in code. | 32 of 44 judged; no English; revise broke two cases. | `0.1.13/20261106T194354973Z` |
| **0.1.14** | A copied strategy cut back to the menu item; the judge asks up to three times. **The submitted version.** | **40 of 50 good, all judged.** | `0.1.14/20261106T195636316Z` |

## Known defects in the submitted version

We stopped fixing at 0.1.14. These are in the 50 submitted results, and `docs/evaluation-report.md` lists each case.

1. **Invented details.** A guessed colour or a made-up weaving method still gets through (f33, f36). Newness is a check, but nothing checks every other claim. Next step: for each product, list what is known and say nothing else is.
2. **A wrong date or span.** f03 says a birthday and 中秋 are two days apart when it is one. A fact-check call, or a festival note computed in code like the birthday note, would catch it.
3. **A reply that skips what was just said.** f07 handles the complaint and leaves out the birthday; f45 does not explain how the shop's service differs.
4. **Revise leaves a repeated or off-menu strategy** (f02, f47, f48). The spec allows one revise. A replacement could be picked from unused menu items in code.
5. **Free care outside its rule** (f27, f37), a message longer than the case asked (f29), and a generic message (f02).
6. **The judge** is a model that was never checked against people, and it is not always consistent. Each version was run once.
7. **Housekeeping.** 57 of 70 cases have empty expectations. Langfuse traces are ended in the code but this was not checked on screen. 15 work-log rows still need screenshots.

## Code defects found in review

A code review of `ca/` and `tests/` found ten defects. Seven are fixed, each with a test written first:

- a 29 February birthday crashed the date logic in most years;
- a revise reply with an index such as `1.0` or `true` crashed the case;
- a client without a birthday or preferences crashed the prompt;
- an unknown client id stopped a run with a bare `KeyError`; it now names the case;
- a case id with `/` or `..` could write outside the case folder; ids are now checked;
- the manifest recorded the current version, not the version folder the run sat in;
- a failed case write aborted the batch; it now fails that case only;
- a null or empty model reply became the word "None", and a rejected request (400, 401, 403, 404) was retried.

Three are recorded and not fixed:

1. **A failed second draft discards a valid first draft.** If attempt 1 returns three candidates that are not yet ready and attempt 2 times out, the case fails with no candidates, and attempt 1's tokens are missing from the case file.
2. **The judge keeps only its last call.** After retries, the earlier calls' cost, latency, and raw replies are lost, so Langfuse undercounts judge cost for those cases.
3. **Langfuse timings are skewed, and cases are traced twice.** Spans start at upload time and end at upload time plus the recorded latency. `generate` and `evaluate` each trace the same case, so Langfuse shows duplicate traces and check scores.

## Next steps

`docs/future-implementation.md` has the plan: a benchmark of real 话术, reading client history through a WeChat MCP server, an agent with a state-tracking page, a daily work list, and a feedback loop.
