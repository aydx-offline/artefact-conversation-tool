# Evaluation report

This file is submission element D. How the tool was designed and what "good" means are in `docs/methodology.md`. The defects and the changes made are in `docs/defects-and-next-steps.md`.

**What was evaluated.** The 50 final cases, written by generator version 0.1.14 and scored by judge version 0.1.8 (run `20261106T195636316Z`). `cases/cases.csv` holds the inputs and the three outputs for each case. At 0.1.14 the team stopped fixing: the defects below are in the submitted version and are not hidden.

## Summary

| Measure | Result |
| --- | --- |
| Good cases | **40 of 50** |
| Not good | 10 cases: f02, f03, f07, f27, f29, f33, f37, f45, f47, f48 |
| Case status | 47 done, 3 `failed_checks` (f02, f47, f48), 0 failed |
| Messages passing all 12 code checks | 147 of 150 |
| Revise | ran on 7 cases; fixed 4, left 3 failing |
| Tildes and English letters in messages | 0 of 150 |
| 事实 pass rate (facts come from the input) | 0.99 |

A case is good when all three messages are acceptable: every code check passes, both pass-or-fail items pass, and no 1–5 item is below 3.

## By scenario

| Scenario | Good | Cases not good |
| --- | --- | --- |
| 1 Birthday and festive greetings | 4 / 7 | f02, f03, f07 |
| 2 Product recommendation | 7 / 7 | |
| 3 Post-purchase care | 7 / 7 | |
| 4 Reactivation | 6 / 7 | f27 |
| 5 Event invitation | 5 / 7 | f29, f33 |
| 6 Price objection: price too high | 4 / 5 | f37 |
| 6 Price objection: comparison | 4 / 5 | f45 |
| 6 Price objection: discount request | 3 / 5 | f47, f48 |

Product recommendation and post-purchase care were the most reliable. Birthday greetings were the weakest. Their three failures are a missing birthday (f07), a date slip (f03), and a generic message (f02).

## By judge item

| Item | Scale | Mean over 150 messages |
| --- | --- | --- |
| 事实: facts, dates, and details come from the input | pass rate | 0.99 |
| 期望: the case's must and must-not notes are met | pass rate | 0.97 |
| 场景: fits the scenario | 1–5 | 4.78 |
| 称呼: the address fits the relationship | 1–5 | 4.83 |
| 具体: specific to this client | 1–5 | 4.42 |
| 中文: reads like native WeChat Chinese | 1–5 | 4.73 |
| 品牌: on-brand | 1–5 | 4.77 |
| 不催: not pushy | 1–5 | 4.93 |

The lowest item is 具体, how specific a message is to the client, and the only 1–5 item with a mean under 4.5.

## Code checks

The 12 checks are: three messages, Chinese only, length, overlap, strategy on the menu, three different strategies, urgency words, discounts, unnamed products, places, newness, and the discount reply. In the final output 147 of 150 messages pass all of them. The three that do not:

| Case | Check | Why |
| --- | --- | --- |
| f02 | strategy on the menu | After revise one strategy is still not a menu item. |
| f47 | different strategies | After revise two messages share a strategy. |
| f48 | different strategies | The same. |

These three cases are marked `failed_checks` and kept in `cases/cases.csv` as the tool produced them.

## All 50 cases

| Case | Scenario | Status | Verdict | First problem the judge or a check found |
| --- | --- | --- | --- | --- |
| f01 | 1 Birthday | done | Good | — |
| f02 | 1 Birthday | failed_checks | Not good | check menu |
| f03 | 1 Birthday | done | Not good | 3号 事实：生日是09-24，中秋是09-25，两日只差一天，消息里说差两天，与资料不符。 |
| f04 | 1 Birthday | done | Good | — |
| f05 | 1 Birthday | done | Good | — |
| f06 | 1 Birthday | done | Good | — |
| f07 | 1 Birthday | done | Not good | 1号 期望：必须项是真诚送上生日祝福，但整条消息完全没提生日，漏掉了核心任务。 |
| f08 | 2 Recommendation | done | Good | — |
| f09 | 2 Recommendation | done | Good | — |
| f10 | 2 Recommendation | done | Good | — |
| f11 | 2 Recommendation | done | Good | — |
| f12 | 2 Recommendation | done | Good | — |
| f13 | 2 Recommendation | done | Good | — |
| f14 | 2 Recommendation | done | Good | — |
| f15 | 3 Post-purchase | done | Good | — |
| f16 | 3 Post-purchase | done | Good | — |
| f17 | 3 Post-purchase | done | Good | — |
| f18 | 3 Post-purchase | done | Good | — |
| f19 | 3 Post-purchase | done | Good | — |
| f20 | 3 Post-purchase | done | Good | — |
| f21 | 3 Post-purchase | done | Good | — |
| f22 | 4 Reactivation | done | Good | — |
| f23 | 4 Reactivation | done | Good | — |
| f24 | 4 Reactivation | done | Good | — |
| f25 | 4 Reactivation | done | Good | — |
| f26 | 4 Reactivation | done | Good | — |
| f27 | 4 Reactivation | done | Not good | 2号 品牌：服务本身合规，但客人没提折扣就明说「免费」，违反了不在折扣场景外说免费、送心意的规矩。 |
| f28 | 4 Reactivation | done | Good | — |
| f29 | 5 Event | done | Not good | 3号 期望：要求简短（1–50字），实际约60字，超出篇幅上限。 |
| f30 | 5 Event | done | Good | — |
| f31 | 5 Event | done | Good | — |
| f32 | 5 Event | done | Good | — |
| f33 | 5 Event | done | Not good | 2号 事实：大衣里有几件浅色调的是资料里没有的，按品牌规矩不知道就不说，不应猜颜色。 |
| f34 | 5 Event | done | Good | — |
| f35 | 5 Event | done | Good | — |
| f36 | 6 Price too high | done | Good | — |
| f37 | 6 Price too high | done | Not good | 2号 期望：'一直保持好的状态'带长期承诺意味，且免费护理只限客人已有的东西，这条裙子她还没买，不该把护理服务挂在这件上。 |
| f38 | 6 Price too high | done | Good | — |
| f39 | 6 Price too high | done | Good | — |
| f40 | 6 Price too high | done | Good | — |
| f41 | 6 Comparison | done | Good | — |
| f42 | 6 Comparison | done | Good | — |
| f43 | 6 Comparison | done | Good | — |
| f44 | 6 Comparison | done | Good | — |
| f45 | 6 Comparison | done | Not good | 3号 期望：必须说明官方渠道与服务的差异，这条只转到料子上手感受和到店试穿，没有回应渠道与服务差别这一核心。 |
| f46 | 6 Discount | done | Good | — |
| f47 | 6 Discount | failed_checks | Not good | check distinct_strategies |
| f48 | 6 Discount | failed_checks | Not good | check distinct_strategies |
| f49 | 6 Discount | done | Good | — |
| f50 | 6 Discount | done | Good | — |

## Examples

Good. f36, a client says a 68,000 coat is too expensive. The first message:

> 明白的，六万多确实不是小数目，换我也会好好掂量掂量。您别有压力，喜欢这件事不用急在今天就定下来。哪天想通了，或者只是想再摸摸那块料子，随时来找我就行，它一直都在的😊

It names the price the way the client did, does not push, and leaves the door open. The three messages use different strategies.

Good. f17, a client says her scarf creases when folded. The second message:

> 好嘞桑蚕丝的料子娇气些，垫张无酸薄纸平放着最稳妥，比挂着还不容易变形。有事随时找我哈。

It picks up her last line, that she will store the scarf again, and adds one storage tip without turning into a sales message.

Not good. f07, a client had a complaint about a loose tassel and her birthday is in two days. The judge's note: two of the three messages never mention the birthday. The second message:

> 明白的，流苏散了，谁戴着心里都会膈应。这条围巾到店我们可以当场做一次护理，散的流苏帮您理顺，再整烫检查一遍，您来一趟就行。…

It deals with the complaint well, but the case's expectation was to do both.

Not good. f33, an invitation to the winter preview. The second message says 「这次的大衣里有几件浅色调的」. The data says nothing about which coats are light, so this is a guessed detail.

Not good. f03, a birthday one day before 中秋. The third message says the two are 「就差两天」. They are one day apart, a date slip.

## Across versions

The same 50 cases were run four times with fixes in between. The judge changed once, so the first row is not strictly comparable.

| Generator | Judge | Good / judged | What the run showed |
| --- | --- | --- | --- |
| 0.1.11 | 0.1.7 | 40 / 49 | Discount requests passed 1 of 5. The brand voice still said no gifts while the menu offered one. |
| 0.1.12 | 0.1.8 | 39 / 49 | Discount requests 3 of 5. 24 of 150 messages had a tilde. |
| 0.1.13 | 0.1.8 | 32 / 44 | Six cases were not judged. No tildes or English. Revise copied its prompt labels into the strategy field in two cases. |
| **0.1.14** | 0.1.8 | **40 / 50** | All judged. The submitted version. |

The case count barely moves. What improved is what the checks now guarantee: no tildes, no English, no lifetime promises, and a higher 事实 rate (0.95 to 0.99). The tuning set (20 cases) went from 12 clean cases and 6 timeouts in 22.7 minutes to 20 finished cases in about a minute; that is in the defects document.

## Cost and speed

| Measure | Result |
| --- | --- |
| Batch of 50, four cases at a time | 3 min 11 s |
| One write call | mean 12.5 s, longest 26.3 s |
| One revise call | mean 13.1 s, 7 calls |
| Tokens per write | about 1,900 in and 560 out |
| Writer cost for the whole run | about $0.033 |
| One judge call | mean 26.7 s, about 3,600 tokens, about $0.010 |
| Judge cost for 50 cases | about $0.50 |
| Whole run, write and judge | about $0.53 |

Costs use the Z.AI list prices in `data/prices.json`. Paratera may bill differently. Langfuse holds the tokens, latency, and cost of every call.

## How far to trust these scores

- **The judge is a model, and no person has scored a sample against it.** The scores compare versions. They are not an absolute measure of quality.
- **The judge is not always consistent.** In run 0.1.13 it marked 「提花」 weaving as an invented detail (f41). In this run it passed the same phrase in f36's second message, where the data does not mention it either. So some invented details in the 40 good cases are probably missed.
- **One run per version.** A difference of one or two cases is within the noise of a single run.
- **The final set is not fully held out.** It was run four times, and a policy conflict found in the first run was fixed before the last. The score is a little optimistic.
- **The writer and the judge are from the same provider.** They are different models, but they may share blind spots.
- **The 10 cases that are not good are real defects** in the submitted version, not a judging artefact. Each is listed above and in `docs/defects-and-next-steps.md`.
