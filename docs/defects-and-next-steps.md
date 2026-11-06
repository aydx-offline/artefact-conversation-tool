# Defects and next steps

This file is submission element E. Method is in `docs/methodology.md`; the steps behind each change are in `log/LOG.md`.

## Versions

Every run records the generator version that wrote it and the judge version that scored it. Scores from different judge versions are not compared.

| Generator | What changed | Runs |
| --- | --- | --- |
| 0.1.1 | First live runs. Writer reasoning never actually off. | Tuning rounds 1 and 2 |
| 0.1.2 | `reasoning_effort` sent; revise removed; two false checks fixed. | `runs/0.1.2/20261106T152913749Z` |
| 0.1.3 | Date facts in the prompt; writer reasoning `high`. | `runs/0.1.3/…T155646236Z` (none), `…T155815344Z` (high) |
| 0.1.5 | Answer her last message first; softer brand wording. | `runs/0.1.5/20261106T163051818Z` |
| 0.1.7 | Chinese-only prompts and keys; product and event details; 180 characters. | `runs/0.1.7/20261106T170439193Z` |
| 0.1.9 | Brand phrases and examples; revise back; optional length and reason. | `runs/0.1.9/20261106T175158630Z` |
| 0.1.10 | Colour of each purchase; discount reply may offer care or a gift. | `runs/0.1.10/20261106T183623165Z` |
| 0.1.11 | Tilde mentions removed. First run of the final 50. | `runs/0.1.11/20261106T184710617Z` |
| 0.1.12 | Birthday rule and purchase ages in code; free care bounded to one visit; lifetime and yearly promises forbidden; expectations on seven cases. | `runs/0.1.12/20261106T191408482Z` |
| 0.1.13 | Prompts frozen. New code checks: no English letters, no newness, discount replies state the price and a gesture. Tildes stripped in code. | `runs/0.1.13/20261106T194354973Z` |
| **0.1.14** | A strategy copied with its labels is cut back to the menu item; the judge asks up to three times. **The 50 submission cases come from this version.** | `runs/0.1.14/20261106T195636316Z` |

## Defects found and what changed

| # | Defect | How it showed up | Change | Before → after |
| --- | --- | --- | --- | --- |
| 1 | Writer reasoning was never off. Paratera ignores `thinking: disabled`; only `reasoning_effort` works. | 4,000–9,000 hidden tokens and 80–150 s per write. 20 tuning cases took 22.7 minutes and 6 timed out at 150 s. | Send `reasoning_effort`. | 22.7 min → 68 s for 20 cases (0.1.1 → 0.1.2) |
| 2 | A timeout was retried three times. | About 460 s lost per failed case. | A timeout is not retried. | Per-case worst case 460 s → 60 s |
| 3 | The length check read the label, `简短（1–50字）`, as a different label from `简短`. | All 3 messages failed on t01 and t15, and revise could not fix it. | Normalised the label, then dropped the per-label limit. Only 180 characters is checked. | 2 false failures → 0 |
| 4 | The offer check treated refusals as offers: 不打折, 没法, 给不了. | t20 and t19 flagged while refusing a discount. | Added those refusal words. | False flags on discount refusals → 0 |
| 5 | A product named in an event's own content was flagged as an unnamed product. | Event cases t13 and t14 failed the product check. | A product named in the event content is allowed. | 2 false failures → 0 |
| 6 | The old revise rewrote messages because of false checks and lost drafts when it timed out. | All six timeouts in round 2 came from revise. | Removed revise; later brought back for real failures only, with the drafts kept if it errors. | Cases lost to revise errors: 6 → 0 |
| 7 | A retry that returned fewer than three messages replaced a full first attempt. A missing 长度 field dropped a message. | t06 ended with empty messages. | Keep the first attempt; make length and reason optional. | t06 failed → done |
| 8 | Wrong dates in the text: 春节刚过 before the festival; 快一年半 for a purchase that was longer ago. | Judge 事实 failures on t01, t04, t10, t11, t12. | Today's date and season, days to birthday and since the last message, spans in words such as 一年多, and the nearest festivals before and after, in the prompt. | Cases with a date error, from different judge versions: 4 in 0.1.2 (t04, t09, t10, t11), 2 in 0.1.3 (t10, t12), 1 in 0.1.9 (t04). Still present in the final run (f36). |
| 9 | Invented product details and colours: 米白素缎, 大衣颜色沉静中性, 两层真丝. | Judge 事实 failures on t02, t07, t10, t13, t16. | Colour, cut, and wear for each product; what happens at each event; the colour of each purchase; a good-and-bad example on not guessing. | The colour of her own piece guessed on 2 cases in 0.1.9 (t07, t10), 0 in 0.1.10 |
| 10 | English words inside Chinese messages: "soon", "double", "Steam". | The Chinese-ratio check allows a stray word: one English word in a message passes. Judge 中文 and 品牌 failures on t03. | Chinese-only prompts and JSON keys. | 1 message in 60 in each of 0.1.2, 0.1.5, and 0.1.6; 1 of 150 in 0.1.11 (f22, "Steam"). Any English letter outside the brand name is now a failed check that goes to revise: 0 of 150 in 0.1.13 and 0.1.14. |
| 11 | Tildes (「～」) in messages. The brand voice at first allowed them, then a prompt line banned them. | 47 of 60 messages in 0.1.2 and 43 of 45 in 0.1.3. | The line 「不要用波浪号」 brought them to 0 of 60 in runs 0.1.4 to 0.1.9. At Ann's request the line was then removed from every prompt, with no code filter. | 31 of 150 final messages (21%) had a tilde in 0.1.11, and 24 of 150 (16%) in 0.1.12. Stripping them in code, with no prompt wording, gave 0 of 150 in 0.1.13 and 0.1.14. |
| 12 | The judge returned broken or incomplete rows. | 4 of 17 cases unscored in the first parallel run. | One retry; the prompt asks for all 24 rows; parallel judging. | 4 unscored → 0 on the 20 tuning cases. On the final run, 1 of 50 (0.1.11) and 6 of 50 (0.1.13) unscored, then 0 of 50 after the judge was allowed three attempts (0.1.14). |
| 13 | The free-care gesture conflicted with the brand rules and the cases, and over-promised. My edit to the brand voice had also been overwritten by the editor, so the 0.1.11 run still told the model 「不送优惠」. | 0.1.11: the discount-request cases pass 1 of 5. Replies offer 免费护理 or 终身免费干洗, and the judge calls it a gift. | Reapplied the voice. Free care is one visit for one piece she owns, only when she asks for a discount. Lifetime, yearly, and permanent promises are forbidden words. Expectations rewritten on seven cases. | Discount cases pass 1 of 5 → 3 of 5 (0.1.11 → 0.1.12). Lifetime or yearly offers: 2 cases (f37, f46) → 0. |
| 15 | Revise copied the whole prompt line into the strategy field, for example 「…；语气：…；长度：…」. | f49 and f50 failed the menu check in 0.1.13 although the strategy was right. | The strategy is cut at 「；」 back to the menu item. | f49 and f50: `failed_checks` → done (0.1.13 → 0.1.14). |
| 16 | The model called things new, or named a new colour, that the data does not say. | The judge's 事实 failures on f02, f11, f32 in 0.1.12. | Code check for 新款, 新品, 新到, 到货, 上新, 「新的…款」, and 「耳钉到了」. A new check was backtested on the saved 0.1.12 messages first: it caught those three cases. | 事实 pass rate 0.95 → 0.99 (0.1.12 → 0.1.14). Invented details remain, such as a guessed colour (f33). |
| 14 | The birthday and purchase ages were left to the model. | A greeting that says 中秋才过 on the day, 「戴了快半年」 for a longer purchase. | `ca/context.py` works out the birthday note (a week before, the day, two days after, otherwise do not mention) and the age of each purchase and visit, in words. | Date and age errors: f21 (中秋才过) remains in 0.1.12; f36's age error is gone. |

## Final run, generator 0.1.14, judge 0.1.8

**40 of 50 cases are good.** All 50 were judged. Statuses: 47 done and 3 `failed_checks` (f02, f47, f48). No message has a tilde or an English word. Revise ran on 7 cases. In Langfuse, a write costs about $0.0005 and a judge call about $0.0075.

| Scenario | 0.1.12 | 0.1.14 |
| --- | --- | --- |
| 1 Birthday and festive greetings | 6 / 7 | 4 / 7 |
| 2 Product recommendation | 6 / 7 | 7 / 7 |
| 3 Post-purchase care | 6 / 7 | 7 / 7 |
| 4 Reactivation | 6 / 7 | 6 / 7 |
| 5 Event invitation | 4 / 7 | 5 / 7 |
| 6 Price too high | 4 / 4 | 4 / 5 |
| 6 Comparison | 4 / 5 | 4 / 5 |
| 6 Discount request | 3 / 5 | 3 / 5 |
| **All** | **39 / 49** | **40 / 50** |

Scores: 事实 0.99, 期望 0.97, 场景 4.78, 称呼 4.83, 具体 4.42, 中文 4.73, 品牌 4.77, 不催 4.93. The two runs are within the noise of a single run, so the gain is in 事实 and in the checks, not the case count.

| Case | Defect |
| --- | --- |
| f07 | A reply to a complaint leaves out the birthday, in two of three messages. |
| f03 | 「差两天」 when the birthday and 中秋 are one day apart. |
| f02 | A generic message, and after revise one strategy is still off the menu. |
| f47, f48 | Revise leaves a repeated strategy, so the case stays `failed_checks`. |
| f27 | Offers something free to a client who did not ask for a discount. |
| f37 | Ties free care to a dress the client has not bought. |
| f33 | Guesses that some coats come in light colours. |
| f29 | A message of about 60 characters where the case asked for 简短. |
| f45 | A comparison reply does not explain how the shop's service differs. |

## The web page was removed

A local web page was built and its API tested against a running server: page load, chat extraction, one generated case in 10.7 s, three rejected bad inputs, trace read, version list, a batch with Stop, and Copy feedback. The page itself was never opened in a browser. On 2026-11-06 it was removed at Ann's request, with chat extraction, the client editor, and Edit and Copy feedback. The command line is the only front end.

| Impact | Result |
| --- | --- |
| Brief | None. The demo is optional, and the brief's input is a structured case. |
| Code | About 1,300 lines gone: the server, the page, chat extraction, `save_client`, the chat prompt, and their tests. |
| Defects removed with it | Copy rewrote `data/clients.json` and changed the test-set hash; chat extraction left the product empty for price cases; test runs mixed into the version folders. |
| Replaced by | `generate --case` for one case, the run folder for a trace, `batch` for progress, `report` and `export --before --after` for comparison, the JSON file for client edits. |
| Lost | Confirm-before-generate, typing a request in natural language, a visual trace and version view, and logging which message a CA copies. |
| Design | The spec, the architecture diagrams, and the Docker image now describe a command-line tool. The few-shot feedback loop in `docs/future-implementation.md` has no source of picks until a front end returns. |

## What remains to be tuned

1. **Invented details.** Newness is now a code check, but a guessed colour or a made-up weaving method still gets through (f33, f36). The prompt is frozen, so the next step is data: for each product, list what is known and say that nothing else is.
2. **A wrong span or date** (f03, f50 in 0.1.13). Candidates: a fact-check call per case, or a festival-day note computed in code like the birthday note.
3. **A reply that skips what was just said** (f07, and t06 to t08 in tuning).
4. **Revise leaves a repeated strategy** (f47, f48). Pick the replacement from the menu items not used, in code.
5. **Judge reliability.** No person has scored a sample against the judge. Each version was run once.
6. **Housekeeping.** 57 of 70 cases have empty expectations. Langfuse traces are ended in the code but this was not checked in the Langfuse screen. 13 work-log rows still need screenshots.

## Future implementation

From `docs/future-implementation.md` and the steps above:

- **An agent that reads client history through a WeChat MCP server**, in place of the removed chat layer. The plan, and why the feedback loop is not possible now, are in `docs/future-implementation.md`.
- **Feedback loop.** Use logged Copy and Edit events as few-shot examples by scenario and client. An edit counts more than a pick. Add whether the client replied, booked, or bought.
- **Per-client memory:** what tone worked, what to avoid, how often to write, with the CA able to see and correct it.
- **Real data:** a client list built from triggers such as a birthday or days since purchase, CRM and WeChat Work for records and history, product catalog search, and a morning list with three drafts per client.
- **Best of two.** Generate two sets in parallel and keep the one that passes the checks. Cost doubles, time stays the same.
- **Better evaluation.** A person scores a sample in Langfuse, and judge agreement is tracked across versions. Large reruns through the GLM Batch API at half the cost.
- **Detect the scenario** from the client's message instead of asking the CA.
- **Hardening.** Logins and one workspace per CA, deployment, audit logs, privacy review, and redaction in traces.
