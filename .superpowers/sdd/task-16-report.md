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

## Fix round 1

`523bd64` — 修正客户时间线、商品归属与重复话术，并新增对应回归测试。保留 `t01` 的 `生日和春节` 覆盖，不改批准时间。

## Fix round 2

`da5f4f0` — 重写重复对话，修正客户复用与故事冲突，并加强话术归一化检查。

- 新测试先在旧数据上失败：10 个案例连续出现两条顾问消息，客户间隔不足，归一化话术重复超限。最终所有对话严格交替，无需例外；重复话术白名单已删除。
- 实质调整：`f02`、`f03`、`f10`、`f16`、`f20`、`f23`、`f24`、`f27`、`f30`、`f34`、`f36`–`f45`、`f47`、`f49`、`f50`、`t02`、`t07`、`t12`–`t20`。
- 使用 30 位虚构客户。服务 3 个案例的客户为：`bi`、`cao`、`du`、`fang`、`han`、`he`、`meng`、`niu`、`su`、`wei`、`yu`；任意两个案例至少相隔 14 天，档案、购买与对话相容。
- `f38`、`f40`、`f42`、`f48`、`f49`、`t15` 仍是在客户已拥有的同类商品上提出价格异议，作为合理复购语境保留。
- 批准的覆盖表各列未改；`f21` 备注继续保留控制人批准的“当天询问大衣使用情况”。冻结版本更新为 `1813aaaf4d3042a884449cd01d8ddd11aa0d482ff8e72debe599fac16e648952`。
- `tests.test_cases` 11 项通过；全套 183 项仅预期的截图测试失败，另有 1 项跳过；`git diff --check` 与代码检查通过。

## Fix round 3

`a806de7` — 消除剩余故事冲突与模板话术，并收紧生日、客户数量、轮次交替和归一化重复检查。

- 测试先在旧数据上失败：`f20`、`t14` 落入客户生日窗口，且 `f16`、`f20` 的归一化顾问话术重复。最终归一化话术每个案例只出现一次，无白名单。
- `f28` 明确承接七周前的 `t17` 沟通，同时保留交付等待造成的不愉快经历；`f14` 明确回顾 `f37` 的试穿与价格顾虑，并改写垂感说明。
- 调整 `niu` 与 `wei` 的生日，未改批准的时间与备注。`lin` 现服务 `t02`；按要求保留 `kong` 的 `f25`/`t11` 和 `bi` 的 `f27`/`t12` 两组重新联系案例。
- 管线会为所有场景计算 `occasion` 并放入 `resolved`。提示词的共用正文随后把它写成“日子：节日或生日：「…」”，进入计划、写作、改写和评审提示。因此 `f13`（端午）、`f14`（七夕）、`f21`（中秋）、`f25`（劳动节）、`t10`（七夕）可能把巧合节日带入消息；本轮按指示仅记录，不修改。
- 冻结版本更新为 `6f658bb976b9aa8673b1015cd050d4e3377b2bda6da3900bcb52c3c132bfc584`。`tests.test_cases` 12 项通过；全套 184 项仅预期的截图测试失败，另有 1 项跳过；`git diff --check` 与代码检查通过。
