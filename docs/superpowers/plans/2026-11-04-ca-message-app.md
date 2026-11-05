# CA Message App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the fixed pipeline that turns one case into three Chinese WeChat candidates, plus the CLI, the local page, scoring, and Docker.

**Architecture:** One Python package, `ca`, with no agent framework. Every front end calls `generate`. A batch runs at most 4 cases at a time. The run store is append-only and is the record of truth. Langfuse is optional.

**Tech Stack:** Python 3, stdlib `unittest`, `urllib` for GLM, the Langfuse Python SDK, one HTML page, Docker.

**Spec:** `docs/superpowers/specs/2026-11-04-ca-message-app-design.md`

## Global Constraints

- Fictional people and brands only.
- Do not commit `Written_Challenge_Brief.pdf`. Do not publish the brief.
- Do not invent a screenshot. Ann said to skip screenshots for now. A log row stays `PENDING` until a real capture exists.
- Do not overwrite an earlier run.
- Do not create a git commit unless Ann explicitly asks. Skip the commit step this skill usually adds.
- If a requirement is unclear, stop and ask Ann. Do not guess.
- Write a failing test before the change it covers. Tests are stdlib `unittest`. Run `python3 -m unittest <module> -v` from the repo root.
- Edit an existing file before creating a new one. The files this plan creates are the app. After one exists, extend it.
- Keep code and docs concise. The default languages are Python and Markdown.
- Before finishing a document, read `.cursor/skills/deslop/SKILL.md` and apply it.
- Every natural-language string sent to GLM is written in Chinese from the start. Do not draft it in English and translate it. The tool does not translate.
- The only English inside that text is an allowed brand or product name. JSON keys stay English. Numbers, dates, and prices stay digits.
- The case `scenario` value stays one of the eight labels in `AGENT.md`. Prompts show the Chinese name from `SCENARIO_ZH` below. That map is authored in Chinese.
- `WRITER_MODEL` and `JUDGE_MODEL` stay empty until Ann names them. They must differ. Do not pick a model.
- A candidate is acceptable when every code check passes, both pass-or-fail judge items pass, and no 1–5 item is below 3. A case is good when all three candidates are acceptable.
- 简短 is 1–50 characters. 适中 is 51–130. Nothing exceeds 150. Count `len(text)`.
- Character-bigram overlap is `|A ∩ B| / min(|A|, |B|)`. Above 0.75 fails. Sets of adjacent character pairs. No pairs means overlap 0.
- Output Chinese ratio is CJK characters among letters, after allowed English names are removed, punctuation and digits ignored. At least 0.90.
- Input prose fails when any `A-Za-z` remains after allowed English names are removed.
- Festival and birthday windows are the date itself and the 3 days before, in Asia/Shanghai.
- Default batch file is `cases/tuning.jsonl`. `export` refuses a tuning run.
- `python3 -m unittest discover -s tests` will still fail `test_step_screenshots_are_real_pngs_and_the_log_links_them` while any cell says `PENDING`. Do not weaken that test. Do not draw a PNG.

## Decisions locked here

- Package path is `ca/`. Run the CLI as `python3 -m ca.cli`.
- GLM requests go to `GLM_BASE_URL`, default `https://open.bigmodel.cn/api/paas/v4/chat/completions`, with `GLM_API_KEY`.
- `runs/` is gitignored.
- Before-and-after export writes `cases/before-after.csv`.
- Export cells for client, history, and product are the resolved Chinese text, not ids.
- `docs/coverage.md` is written and then work stops until Ann approves it. No `cases/inputs.jsonl` or `cases/tuning.jsonl` before that.
- The resolved dict passed to prompts has these shapes. `client` is the client-store dict. `products` is a list of catalog dicts. `event` is an event dict or `None`. `history` is a list of `Message` or of dicts with `sender`, `text`, `time`. `occasion` is a Chinese string. `expectations` is a list of strings or a dict `{must, must_not}`. Prompts render only the Chinese fields, with price and dates as digits. Ids such as `lin` and `scarf` and English keys never appear in the prompt text. Revise prompts show only the failing candidates, with their original indexes.
- Scenario 6 client text must contain a marker: price too high uses 贵 or 价格高; comparison uses 别处, 别家, 代购, 其他店, or 别的店; discount uses 折扣, 优惠, 打折, 便宜点, or 便宜一点.

```python
SCENARIO_ZH = {
    "1 Birthday and festive greetings": "生日与节日问候",
    "2 Product recommendation": "产品推荐",
    "3 Post-purchase care": "购后关怀",
    "4 Reactivation": "重新联系",
    "5 Event invitation": "活动邀约",
    "6 Price objection — price too high": "价格异议：觉得太贵",
    "6 Price objection — comparison": "价格异议：和其他渠道比较",
    "6 Price objection — discount request": "价格异议：要求折扣",
}
```

## File map

| Path | Job |
| --- | --- |
| `ca/schema.py` | Dataclasses, scenario list, prose check, `validate_case` |
| `ca/brand.py` | Load `data/brand/` |
| `ca/clients.py` | Load and edit `data/clients.json` |
| `ca/context.py` | Occasion and time since contact |
| `ca/prompts.py` | Chinese plan, write, revise, chat, and judge prompts |
| `ca/llm.py` | `complete(system, user) -> str`, fake model, GLM adapter, two backoff retries |
| `ca/checks.py` | Code checks |
| `ca/pipeline.py` | `generate(case, model, brand, clients, recorder) -> Result` |
| `ca/store.py` | Append-only runs, one writer per run |
| `ca/judge.py` | Judge call and acceptable / good |
| `ca/telemetry.py` | Langfuse, or nothing when no key |
| `ca/chat.py` | Extract a case, never invent a client |
| `ca/cli.py` | `generate`, `batch`, `evaluate`, `export` |
| `ca/web.py` | JSON handlers and the HTTP server |
| `web/index.html` | Case form, chat, clients, trace, batch, versions |
| `data/brand/` | Voice, rules, menus, catalog, events, festivals, written in Chinese |
| `docs/rubric.md` | Mapping from the spec. Still a draft until Ann accepts it |
| `docs/coverage.md` | Case grid. Ann approves it before any case file is filled |
| `Dockerfile` | One image. `runs/` and `data/` are mounts |

`generate` takes `clients` as well as the spec's `case, model, brand, recorder`, because resolution reads the store.

## Task 1: Move the scaffold scope and map the rubric

**Files:**
- Modify: `tests/test_scaffold.py`
- Modify: `AGENT.md`
- Modify: `docs/rubric.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: nothing
- Produces: rubric headings the judge task will match

- [ ] **Step 1: Write the failing test**

In `test_agent_manual_has_required_sections_and_rules`, stop requiring `brand document`, `message generator`, and `filled test cases` under `## Out of scope until a later plan`. Require those three strings under `## In scope for the scaffold`.

In `test_case_header_and_draft_rubric`, delete the assertion that `cases/cases.csv` has one line. Keep the header assertion. Require these rubric strings: `## Scoring`, `A candidate is acceptable`, `no 1–5 item is below 3`, `Facts, dates, and details come from the input`. Keep `Draft. Do not generate messages until Ann accepts or edits this file.`

- [ ] **Step 2: Run the test**

Run: `python3 -m unittest tests.test_scaffold.ScaffoldTest.test_agent_manual_has_required_sections_and_rules tests.test_scaffold.ScaffoldTest.test_case_header_and_draft_rubric -v`

Expected: FAIL. The out-of-scope section still lists the three items, and the rubric has no scoring section.

- [ ] **Step 3: Update the docs**

Move the three items into `## In scope for the scaffold`. Leave `## Out of scope until a later plan` with the single line `None.`

Replace `docs/rubric.md` body after the draft line with the spec's Good / Not acceptable rules and this table. Keep the draft line. English names that the brand allows are not a failure. Brand fit is a 1–5 judge item.

| Rubric item | Scored by |
| --- | --- |
| Three candidates, Chinese, length | Code checks |
| Three different strategies | Code checks |
| Urgency or false scarcity | Code checks |
| Unallowed discount | Code checks |
| Unknown product | Code checks |
| Facts, dates, and details come from the input | Judge, pass or fail |
| Case expectations met | Judge, pass or fail |
| Fits the scenario | Judge, 1–5 |
| Matches the relationship and address form | Judge, 1–5 |
| Specific to this client, not a template opener | Judge, 1–5 |
| Natural WeChat Chinese, not translationese | Judge, 1–5 |
| On-brand | Judge, 1–5 |
| Not pushy | Judge, 1–5 |

A candidate is acceptable when every code check passes, both pass-or-fail judge items pass, and no 1–5 item is below 3. A case is good when all three candidates are acceptable.

In `README.md`, point at this plan. Leave the sentence that the generator is not built yet.

- [ ] **Step 4: Run the test**

Run the same command. Expected: PASS.

- [ ] **Step 5: Do not commit**

## Task 2: Case schema and validation

**Files:**
- Create: `ca/__init__.py`
- Create: `ca/schema.py`
- Test: `tests/test_schema.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `SCENARIOS: tuple[str, ...]` the eight `AGENT.md` labels
  - `CaseError(ValueError)` with `.field` and `.message`
  - `@dataclass Case` fields: `case_id, client_id, scenario, timestamp, history, product_ids, event_id, occasion, tone, length, split, expectations`
  - `@dataclass Message` fields: `sender, text, time`
  - `prose_is_chinese(text: str, allowed_names: list[str]) -> bool`
  - `validate_case(case: Case, *, allowed_names: list[str]) -> None`

`history` entries are `Message`. `timestamp` is ISO-8601 with an offset.

- [ ] **Step 1: Write the failing test**

```python
import unittest
from ca.schema import Case, CaseError, Message, validate_case

ALLOWED = ["Chengbai"]

def case(**kwargs):
    base = dict(
        case_id="c1",
        client_id="lin",
        scenario="1 Birthday and festive greetings",
        timestamp="2026-09-25T10:00:00+08:00",
        history=[],
    )
    base.update(kwargs)
    return Case(**base)

class SchemaTest(unittest.TestCase):
    def test_scenario_6_needs_a_client_message(self):
        item = case(scenario="6 Price objection — price too high", history=[])
        with self.assertRaises(CaseError) as caught:
            validate_case(item, allowed_names=ALLOWED)
        self.assertEqual(caught.exception.field, "history")

    def test_scenario_6_price_message_passes(self):
        item = case(
            scenario="6 Price objection — price too high",
            history=[Message("client", "六万八太贵了", "2026-09-25T09:00:00+08:00")],
            product_ids=["yunwen"],
        )
        validate_case(item, allowed_names=ALLOWED)

    def test_english_client_text_is_rejected(self):
        item = case(history=[Message("client", "too expensive", "2026-09-25T09:00:00+08:00")])
        with self.assertRaises(CaseError) as caught:
            validate_case(item, allowed_names=ALLOWED)
        self.assertEqual(caught.exception.field, "history")

    def test_allowed_english_name_passes(self):
        item = case(history=[Message("ca", "Chengbai 的围巾到了", "2026-09-25T09:00:00+08:00")])
        validate_case(item, allowed_names=ALLOWED)

    def test_empty_history_is_valid_for_scenario_1(self):
        validate_case(case(), allowed_names=ALLOWED)

    def test_unknown_scenario_names_the_field(self):
        with self.assertRaises(CaseError) as caught:
            validate_case(case(scenario="nope"), allowed_names=ALLOWED)
        self.assertEqual(caught.exception.field, "scenario")
```

- [ ] **Step 2: Run the test**

Run: `python3 -m unittest tests.test_schema -v`

Expected: FAIL with `ModuleNotFoundError: ca`.

- [ ] **Step 3: Implement**

`ca/__init__.py` is empty.

`validate_case` checks, in order: non-empty `case_id` and `client_id`; `scenario` in `SCENARIOS`; `timestamp` parses with `datetime.fromisoformat`; each history sender is `client` or `ca`; each history `text` passes `prose_is_chinese`. For a scenario starting with `6`, require one `client` message whose text contains a marker for that subtype (see Decisions). `product_ids` required is checked later, when the brand and client exist. This function does not read the clock.

`prose_is_chinese` removes each allowed name, then returns False if `[A-Za-z]` remains.

- [ ] **Step 4: Run the test**

Expected: PASS.

- [ ] **Step 5: Do not commit**

## Task 3: Brand data, written in Chinese

**Files:**
- Create: `data/brand/voice.md`
- Create: `data/brand/rules.json`
- Create: `data/brand/menus.json`
- Create: `data/brand/catalog.json`
- Create: `data/brand/events.json`
- Create: `data/brand/festivals.json`
- Create: `ca/brand.py`
- Test: `tests/test_brand.py`

**Interfaces:**
- Consumes: `prose_is_chinese`
- Produces: `Brand` with `.voice, .rules, .menus, .catalog, .events, .festivals`, and `load_brand(root: Path) -> Brand`
- `rules["allowed_english"]` is `["Chengbai"]`
- `rules["lengths"]` is `{"简短": [1, 50], "适中": [51, 130], "max": 150}`
- `rules["offer_patterns"]` is `["优惠", "打折", "折扣价", "打八折", "打九折", "%"]`
- `rules["forbidden"]` includes `最后机会`, `仅此一天`, `马上涨价`, `限时`
- `menus[scenario]` is a list of 5 Chinese strategy strings, keyed by the eight `AGENT.md` labels

The house is 澄白. The allowed English name is Chengbai. It sells silk in Shanghai. It does not give discounts. A client may be offered a fitting or care for a piece they own. Write `voice.md` and every menu string in Chinese. Do not translate the English strategy table in the spec. Use these menus:

| Label | Five Chinese strategies |
| --- | --- |
| 1 | 只问好，不提购买；提起她之前买过的一件东西；把这个日子和她的生活连起来；问问已有的一件东西要不要保养；轻轻提一次到店服务，不推销 |
| 2 | 从她已经有的一件东西说起；连到一个近的日子；一件新的，合她平时的喜好；讲这件东西怎么做出来；提议为她留到店里看 |
| 3 | 问她用得是否顺手；按材质写一句保养；告诉她店里可以做的服务；和她已有的东西搭一句；按购买时的日子道一声谢 |
| 4 | 只是问候，不提出要求；用她的喜好给一个理由；提出保养她已有的一件东西；说一句店里的新消息，不邀请购买；轻轻请她有空来坐坐 |
| 5 | 以顾问本人的口气邀请；把活动内容和她的喜好连起来；仅当面额人数写在活动上时才提名额；请她带一位客人；来不了就改为单独约见 |
| 6 price | 讲材质和做法；同系列里的另一件；长期可以享受的保养；请她到店里看和试；表示听见了，不催，把门留着 |
| 6 comparison | 讲官方渠道、真伪和保修；讲只有精品店做的服务；提议核对对方条件，不贬低对方；请她到店里对比着看；说明全渠道一个价格 |
| 6 discount | 礼貌地说明没有折扣，并把人留住；给出品牌允许的一次到店或保养；把话题转到一个日子或一次试穿；说明一个价格是对每位客人公平；下次新品可以先告诉她 |

Catalog, four products, prose in Chinese: `yunwen` 云纹大衣 68000, `scarf` 素缎围巾 12800, `pearl` 珍珠耳钉 9600, `dress` 月白长裙 42000. Each has `id, name, line, price, materials, care`.

Events: `winter` 冬日私览 on `2026-11-20`, place 上海澄白店, capacity 10. `spring` 春日沙龙 on `2027-03-12`, capacity `null`.

Festivals, `name` and `date`: 元旦 2026-01-01 and 2027-01-01; 春节 2026-02-17 and 2027-02-06; 元宵 2026-03-03 and 2027-02-20; 清明 2026-04-05 and 2027-04-05; 劳动节 2026-05-01 and 2027-05-01; 端午 2026-06-19 and 2027-06-09; 七夕 2026-08-19 and 2027-08-08; 中秋 2026-09-25 and 2027-09-15; 国庆 2026-10-01 and 2027-10-01; 圣诞 2026-12-25 and 2027-12-25.

- [ ] **Step 1: Write the failing test**

Assert `load_brand(Path("data/brand"))` returns 8 menus of 5 strings, 4 products, 2 events, and 20 festival rows. Assert every menu string and the voice file pass `prose_is_chinese` with `allowed_english`. Assert `winter` capacity is 10 and `spring` capacity is `None`.

- [ ] **Step 2: Run the test**

Expected: FAIL, `data/brand` missing.

- [ ] **Step 3: Write the Chinese files and `load_brand`**

`load_brand` reads the six files. JSON objects keep English keys. `capacity: null` becomes `None`.

- [ ] **Step 4: Run the test**

Expected: PASS.

- [ ] **Step 5: Do not commit**

## Task 4: Client store

**Files:**
- Create: `ca/clients.py`
- Create: `data/clients.json` with one fixture client, `lin`
- Test: `tests/test_clients.py`

**Interfaces:**
- Consumes: `prose_is_chinese`
- Produces:
  - `load_clients(path) -> dict[str, dict]`
  - `save_client(path, client: dict) -> None`
  - `store_hash(path) -> str` sha256 of the canonical JSON

Fixture `lin`, written in Chinese: name 林女士, tier 常客, relationship 熟, address 您, birthday `03-15`, preferences 喜欢素色丝绸, purchases `[{product_id: scarf, date: 2026-03-02}]`, last_visit `2026-03-02`, history `[]`.

- [ ] **Step 1: Write the failing test**

Loading the fixture returns 林女士. A profile value `hello` raises `CaseError` on field `preferences`. `save_client` of a second Chinese client round-trips. `store_hash` changes when the file changes.

- [ ] **Step 2: Run the test**

Expected: FAIL, `ca.clients` missing.

- [ ] **Step 3: Implement**

Canonical JSON is `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"))`. Check every string value except `id`, `product_id`, `birthday`, `date`, `last_visit`, and `address` is not the place for English: check `name`, `tier`, `relationship`, `preferences`, and history `text`. `address` must be `您` or `你`.

- [ ] **Step 4: Run the test**

Expected: PASS.

- [ ] **Step 5: Do not commit**

## Task 5: Occasion and time since contact

**Files:**
- Create: `ca/context.py`
- Test: `tests/test_context.py`

**Interfaces:**
- Consumes: `Brand.festivals`, a client dict
- Produces: `resolve_context(timestamp, client, festivals, occasion) -> Context`
- `Context` fields: `occasion: str`, `festival: str | None`, `birthday: bool`, `days_since_purchase: int | None`, `months_since_visit: int | None`

- [ ] **Step 1: Write the failing test**

Use the festival file from Task 3.

- Timestamp `2026-09-25T10:00:00+08:00` resolves occasion `中秋`.
- `2026-09-22T10:00:00+08:00` still resolves `中秋`.
- `2026-09-21T10:00:00+08:00` is outside the window.
- Client birthday `03-15` and timestamp `2026-03-15T10:00:00+08:00` set `birthday` True and occasion `生日`.
- An explicit `occasion` argument wins over the calendar.
- `days_since_purchase` for a purchase on `2026-03-02` and timestamp `2026-03-12` is 10.
- `months_since_visit` for `2026-03-02` to `2026-09-25` is 6.
- Scenario is not this function's job. Raising when scenario 1 has no occasion is Task 9, using `Context.occasion == ""`.

- [ ] **Step 2: Run the test**

Expected: FAIL, `ca.context` missing.

- [ ] **Step 3: Implement**

Compare dates in `zoneinfo.ZoneInfo("Asia/Shanghai")`. A festival matches if `0 <= (festival_date - message_date).days <= 3`. Birthday uses the message year, and also the previous year when the message is in early January and the birthday is in late December. Empty occasion string means none. Do not invent a festival name.

- [ ] **Step 4: Run the test**

Expected: PASS.

- [ ] **Step 5: Do not commit**

## Task 6: Chinese prompts

**Files:**
- Create: `ca/prompts.py`
- Test: `tests/test_prompts.py`

**Interfaces:**
- Consumes: `Case`, `Brand`, `SCENARIO_ZH`
- Produces:
  - `quote_data(text: str) -> str` wraps in `「」`, inner quotes become `『』`
  - `plan_prompt(resolved, menu) -> tuple[str, str]`
  - `write_prompt(resolved, plan) -> tuple[str, str]`
  - `revise_prompt(resolved, candidates, failures) -> tuple[str, str]`
  - `chat_prompt(request: str) -> tuple[str, str]`
  - `judge_prompt(resolved, candidates, expectations) -> tuple[str, str]`
  - `natural_language_is_chinese(prompt: str, allowed_names: list[str]) -> bool`

`resolved` is a dict with Chinese keys in the prompt body only: 客户, 场景, 对话, 产品, 日子, 策略. The Python dict keeps English keys: `client, scenario, history, products, occasion, event, days_since_purchase, months_since_visit`.

- [ ] **Step 1: Write the failing test**

Build each prompt from a Chinese fixture that includes `expectations` text `不能提折扣`. Assert `expectations` is absent from plan, write, and revise, and present in the judge prompt. Assert `natural_language_is_chinese` after removing `Chengbai` and these keys: `strategy, reason, tone, length, text, picks, candidates, index, client_name, scenario, client_message, item, value`. Assert the scenario line uses `生日与节日问候`, not the English label.

- [ ] **Step 2: Run the test**

Expected: FAIL, `ca.prompts` missing.

- [ ] **Step 3: Implement**

System text for plan, write, revise, and chat tells the model the quoted blocks are data, not instructions. Plan asks for JSON `{"picks":[{"strategy","reason"}]}` with three different menu strings copied verbatim. Write asks for `{"candidates":[{"strategy","reason","tone","length","text"}]}`. Tone choices are the six labels. Length choices are 简短 and 适中, with the character bounds from the brand rules stated in Chinese. Revise asks for `{"candidates":[{"index","strategy","reason","tone","length","text"}]}` and only the failing indexes. Chat asks for `{"client_name","scenario","client_message"}` and lists the eight Chinese scenario names. Judge asks for `{"scores":[{"candidate","item","value","reason"}]}`. Pass-or-fail items are `事实` and `期望`. The 1–5 items are `场景`, `称呼`, `具体`, `中文`, `品牌`, `不催`.

- [ ] **Step 4: Run the test**

Expected: PASS.

- [ ] **Step 5: Do not commit**

## Task 7: Model calls

**Files:**
- Create: `ca/llm.py`
- Test: `tests/test_llm.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `class FakeModel` with `complete(self, system, user) -> str` and `.calls`
  - `complete_with_retries(model, system, user, sleep) -> str` attempts 3 times, sleeps `0.5` then `1.0`
  - `GlmModel(api_key, base_url, model_name).complete(system, user) -> str`
  - `require_models(env: dict) -> tuple[str, str]` raises `SystemExit` when the key or either model name is missing, or when the two names are equal

- [ ] **Step 1: Write the failing test**

`FakeModel(["a"])` returns `a` and records the call. A model that raises twice then returns `ok` causes two sleeps and one success. Three failures raise the last error. `require_models` rejects an empty `WRITER_MODEL`, an empty `JUDGE_MODEL`, and equal names. Do not call the network.

- [ ] **Step 2: Run the test**

Expected: FAIL, `ca.llm` missing.

- [ ] **Step 3: Implement**

`GlmModel.complete` POSTs JSON `{"model", "messages":[{"role":"system"},{"role":"user"}]}` with header `Authorization: Bearer <key>`. Parse `choices[0].message.content`. This function is not used in unit tests.

- [ ] **Step 4: Run the test**

Expected: PASS.

- [ ] **Step 5: Do not commit**

## Task 8: Code checks

**Files:**
- Create: `ca/checks.py`
- Test: `tests/test_checks.py`

**Interfaces:**
- Consumes: `Brand`
- Produces: `Check` with `.name, .passed, .reason`, and `check_candidates(candidates, brand, scenario, product_ids, owned_ids, event) -> list[Check]`

Each candidate is a dict `strategy, reason, tone, length, text`.

- [ ] **Step 1: Write the failing test**

One test per check, pass and fail:

- Not exactly three non-empty texts.
- Chinese ratio: a string that is 90% CJK passes; `hello 你好` fails.
- 简短 of 51 characters fails. 适中 of 50 fails. 151 characters fails. A 简短 message of 10 passes.
- Two identical texts fail overlap. Two unrelated sentences pass.
- A strategy not on the menu fails. Two equal strategies fail.
- Forbidden `最后机会` fails.
- `给您打八折` fails. `折扣我们没有，价格对每位客人都一样` passes.
- A catalog name that is not in `product_ids` or `owned_ids` fails.
- `本次仅限十位` fails when `event["capacity"]` is `None`, and passes when capacity is 10.

- [ ] **Step 2: Run the test**

Expected: FAIL, `ca.checks` missing.

- [ ] **Step 3: Implement**

Overlap uses the formula in Global Constraints. Offer check: if any `offer_patterns` entry is in the text, fail, unless the text also has `没有` or `不能` or `不提供` next to a discount word. A refusal that contains `折扣` and `没有` passes. Product check scans `catalog` names and fails when a found name is outside the allowed ids.

- [ ] **Step 4: Run the test**

Expected: PASS.

- [ ] **Step 5: Do not commit**

## Task 9: Pipeline

**Files:**
- Create: `ca/pipeline.py`
- Create: `ca/version.py` with `GENERATOR_VERSION = "0.1.0"`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: validate, brand, clients, context, prompts, llm retries, checks
- Produces: `generate(case, model, brand, clients, recorder) -> Result`
- `Result` fields: `status, resolved, steps, candidates, checks`
- `recorder.step(case_id, step)` and `recorder.finish(case_id, result)` may be no-ops
- Status values: `done`, `failed_checks`, `failed`

Resolved dict saved later must include the four brief inputs in full: client profile, scenario plus occasion, event, and time since contact, history, and product records.

- [ ] **Step 1: Write the failing test**

Use `FakeModel` and the `lin` client.

- Scenario 1 on `2026-11-04` with no occasion raises `CaseError` field `occasion` before any model call.
- A plan reply that repeats one strategy, then a valid plan, then a valid write: two plan calls, status `done`, step names in order `validate, resolve, select, plan, write, check, final`.
- A write of three identical texts, then a revise that replaces the later indexes with different texts: status `done`, and the revise prompt contains only those indexes.
- A write of invalid JSON, then a valid revise: status `done`.
- `complete` raises three times: status `failed`, and the candidates list is empty.
- `case.expectations` does not appear in any recorded prompt.
- After `generate`, mutate the client store object. The `resolved` client name on the result stays `林女士`.

- [ ] **Step 2: Run the test**

Expected: FAIL, `ca.pipeline` missing.

- [ ] **Step 3: Implement**

Validate first, including product rules: scenario `2` and every `6` require `product_ids`; scenario `3` with empty `product_ids` uses the client's latest purchase; scenario `5` requires `event_id`. Then resolve. Copy the client dict and product dicts into `resolved` so later store edits cannot change them. History is the case history when the case has a `history` list, including an empty list. Missing `history` uses the client's stored history.

Plan: parse JSON, require three different menu strings. On failure, call the model once more. Write: parse three candidates. Check. If any check fails, one revise call for the failing indexes. Overlap adds the later index of each pair. If checks still fail, status `failed_checks` and the candidates are kept. A model error after the retries in `complete_with_retries` sets status `failed`.

Each model step stores `prompt` and `raw` on the step.

- [ ] **Step 4: Run the test**

Expected: PASS.

- [ ] **Step 5: Do not commit**

## Task 10: Run store

**Files:**
- Create: `ca/store.py`
- Modify: `.gitignore` add `runs/`
- Modify: `tests/test_scaffold.py` `test_gitignore_covers_local_secrets_and_caches` to expect `runs/`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `GENERATOR_VERSION`
- Produces:
  - `RunStore(root: Path)`
  - `begin(manifest: dict) -> str` returns `run_id` like `20261104T231501123Z`
  - `append(run_id, filename, obj) -> None` for `events.jsonl`, `scores.jsonl`, `feedback.jsonl`
  - `write_case(run_id, case_id, obj) -> None` once
  - `finish_manifest(run_id, manifest) -> None` once
  - `test_set_version(inputs: Path, tuning: Path, profiles: list[dict]) -> str`

Layout:

```text
runs/<GENERATOR_VERSION>/<run_id>/manifest.json
runs/<GENERATOR_VERSION>/<run_id>/events.jsonl
runs/<GENERATOR_VERSION>/<run_id>/cases/<case_id>.json
runs/<GENERATOR_VERSION>/<run_id>/scores.jsonl
runs/<GENERATOR_VERSION>/<run_id>/feedback.jsonl
```

- [ ] **Step 1: Write the failing test**

`write_case` twice on the same path raises `FileExistsError`. Two threads appending 20 events through one store produce 20 valid JSON lines and no interleaved line. `test_set_version` changes when `inputs` bytes change. Manifest records `generator_version, writer_model, brand_hash, client_store_hash, test_set_version, split, start, case_ids`.

- [ ] **Step 2: Run the test**

Expected: FAIL, `ca.store` missing. Then the gitignore assertion fails until `.gitignore` contains `runs/`.

- [ ] **Step 3: Implement**

One `threading.Lock` per `run_id` guards appends. `run_id` is UTC from `datetime.now(timezone.utc)` to the millisecond, `YYYYMMDDTHHMMSSmmmZ`. Hashes are sha256 of canonical JSON or raw file bytes.

- [ ] **Step 4: Run the tests**

Expected: PASS for `tests.test_store` and the gitignore test.

- [ ] **Step 5: Do not commit**

## Task 11: Judge, scores, and telemetry

**Files:**
- Create: `ca/judge.py`
- Create: `ca/telemetry.py`
- Create: `ca/version.py` add `JUDGE_VERSION = "0.1.0"` if not already there
- Test: `tests/test_judge.py`
- Test: `tests/test_telemetry.py`

**Interfaces:**
- Consumes: prompts, llm, checks, store
- Produces:
  - `evaluate_case(case_file: dict, model, brand) -> list[dict]`
  - `candidate_acceptable(checks, scores) -> bool`
  - `case_good(per_candidate: list[bool]) -> bool`
  - `Telemetry(client=None)` with `trace_case`, `score`, `dataset_run`, `flush`
  - `open_telemetry(env) -> Telemetry`

Score dict keys: `evaluation_id, judge_model, judge_version, case_id, candidate, item, value, reason`.

- [ ] **Step 1: Write the failing tests**

A fake judge returns pass for `事实` and `期望` and `3` for each 1–5 item. With passing checks, `candidate_acceptable` is True. One item at `2` makes it False. A failed code check makes it False.

`Telemetry(None).trace_case(...)` records nothing and does not raise. `open_telemetry({})` returns a telemetry whose client is `None`. A fake client receives one trace, one score, and `flush`.

- [ ] **Step 2: Run the tests**

Expected: FAIL, modules missing.

- [ ] **Step 3: Implement**

`evaluate_case` sends the judge prompt, parses `scores`, and also appends one score row per code check with value `pass` or `fail`. `open_telemetry` constructs `Langfuse()` only when `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set. Otherwise it prints `Langfuse off` once. Dataset names are `tuning` and `final`. A dataset run name is `{GENERATOR_VERSION}:{run_id}`.

- [ ] **Step 4: Run the tests**

Expected: PASS.

- [ ] **Step 5: Do not commit**

## Task 12: Chat extraction

**Files:**
- Create: `ca/chat.py`
- Test: `tests/test_chat.py`

**Interfaces:**
- Consumes: llm, clients, schema, `SCENARIO_ZH`
- Produces: `extract_case(request, model, clients, now) -> Case | str`

The string return is the message shown when no client matches. It does not build a client.

- [ ] **Step 1: Write the failing test**

Fake model returns `{"client_name":"林女士","scenario":"价格异议：和其他渠道比较","client_message":"价格比别处贵"}`. The case uses client `lin`, the English scenario label for comparison, history of that one client message, and `timestamp == now`. An unknown name `不存在` returns a string that asks the CA to pick a client, and the clients file is unchanged.

- [ ] **Step 2: Run the test**

Expected: FAIL, `ca.chat` missing.

- [ ] **Step 3: Implement**

Map the Chinese scenario back through `SCENARIO_ZH`. Reject the request with `CaseError` field `request` when `prose_is_chinese` fails, before the model call.

- [ ] **Step 4: Run the test**

Expected: PASS.

- [ ] **Step 5: Do not commit**

## Task 13: CLI

**Files:**
- Create: `ca/cli.py`
- Create: `ca/__main__.py` that calls `ca.cli.main`
- Create: `.env.example`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: pipeline, judge, store, telemetry, llm
- Produces: `main(argv: list[str]) -> int`

Commands:

- `generate --case <file>`
- `batch` reads `cases/tuning.jsonl`
- `batch --cases cases/inputs.jsonl`
- `evaluate --run <run_id>`
- `export --run <run_id>`
- `export --before <run_id> --after <run_id>`

`.env.example` keys: `GLM_API_KEY`, `GLM_BASE_URL`, `WRITER_MODEL`, `JUDGE_MODEL`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`. Leave the model names empty.

- [ ] **Step 1: Write the failing test**

On a temp dir, with `FakeModel` injected by `main`'s optional `model` argument: `generate` prints three texts and a run path. `evaluate` writes `scores.jsonl`. `export` of a `final` run writes 1 data row plus the header to `cases/cases.csv` in that temp dir, with the resolved Chinese client name in the client column and `Generator version` equal to `GENERATOR_VERSION`. `export` of a `split: tuning` manifest raises `SystemExit`. `batch` runs two cases and continues when the second model's `complete` fails. A missing `GLM_API_KEY` on the real path, called via `require_models`, exits before `begin`.

Header:

```text
Case ID,Scenario,Client information,Conversation history,Product information,Output 1,Output 2,Output 3,Generator version
```

`export --before --after` writes `cases/before-after.csv` with columns `Case ID, Scenario, Before 1, Before 2, Before 3, After 1, After 2, After 3, Before version, After version`, and only the cases whose three outputs differ.

- [ ] **Step 2: Run the test**

Expected: FAIL, `ca.cli` missing.

- [ ] **Step 3: Implement**

Load `.env` with a small reader, no extra dependency. `batch` uses `ThreadPoolExecutor(max_workers=4)`. A failed case is marked `failed` and the batch continues. Progress is one printed line per case: `case_id status`.

A smoke test in `tests/test_smoke.py` calls `GlmModel` once and skips unless `GLM_API_KEY` and `WRITER_MODEL` are set. It is not part of the default unit run.

- [ ] **Step 4: Run the test**

Expected: PASS.

- [ ] **Step 5: Do not commit**

## Task 14: Web page

**Files:**
- Create: `ca/web.py`
- Create: `web/index.html`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: cli's batch and generate functions, clients, store, chat
- Produces: `handle(method, path, body, deps) -> tuple[int, dict]`

The page layout is not unit tested. `handle` is.

Routes:

- `GET /api/clients` and `POST /api/clients` and `PUT /api/clients/<id>`
- `POST /api/generate` runs one case after validation
- `POST /api/chat` returns the extracted case and does not run the pipeline
- `POST /api/feedback` appends one object: `run_id, case_id, candidate, strategy, tone, original_text, copied_text, edited, time`. Copy also appends the copied text to that client's stored history
- `GET /api/runs` groups runs by generator version
- `GET /api/runs/<version>/<run_id>/cases/<case_id>` returns steps, prompts, raw output, checks, and scores
- `POST /api/batch` body `{"split":"tuning"}` or `{"split":"final"}`. One batch at a time. A second start returns 409
- `POST /api/batch/stop` lets running cases finish and marks cases not yet started `cancelled`
- `GET /api/batch` returns the rows

`index.html` has six regions: case form, chat, clients, trace, batch, versions. The form's timestamp defaults to the current time in Asia/Shanghai. Candidate cards have Edit and Copy. The batch view has Run and Stop, and a choice of the 20 or the 50. The versions view shows one case under two runs and a flag when `client_store_hash` or `test_set_version` differs. Serve it with `python3 -m ca.web` on port 8765.

- [ ] **Step 1: Write the failing test**

`POST /api/chat` with the 林女士 request returns a case and does not create a run directory. `POST /api/chat` for an unknown client returns 404 and the pick-a-client message. `POST /api/generate` on an English history returns 400 and names `history`. `POST /api/batch` twice returns 409 the second time. `POST /api/batch/stop` marks a not-yet-started case `cancelled` and leaves a started case to finish. `POST /api/feedback` with `action: copy` adds the text to the client history.

- [ ] **Step 2: Run the test**

Expected: FAIL, `ca.web` missing.

- [ ] **Step 3: Implement `handle` and the page**

Wire `handle` to the same functions as the CLI. The page is one HTML file and one script block. No framework.

- [ ] **Step 4: Run the test**

Expected: PASS.

- [ ] **Step 5: Do not commit**

## Task 15: Coverage table, then stop

**Files:**
- Create: `docs/coverage.md`
- Test: `tests/test_coverage.py`

**Interfaces:**
- Consumes: the eight scenario labels
- Produces: a table Ann approves before Task 16

Do not create `cases/inputs.jsonl` or `cases/tuning.jsonl` in this task. Do not call GLM.

- [ ] **Step 1: Write the failing test**

`docs/coverage.md` has a `final` table and a `tuning` table. Count data rows whose first cell matches `f01`–`f50` or `t01`–`t20`. Final counts are 7 for each of scenarios 1–5 and 5 for each scenario 6 subtype. Every final scenario 6 row says `short` or `long`, never `none`. Every final row has a unique id `f01`–`f50`. Tuning ids are `t01`–`t20`. The two id sets do not overlap.

- [ ] **Step 2: Run the test**

Expected: FAIL, file missing.

- [ ] **Step 3: Write the tables**

Columns: `id, scenario, tier, relationship, history, product, event, timestamp, note`.

Final shape:

- Scenarios 1–5, seven rows each: top/熟/none, top/正式/short, 常客/熟/long, 常客/正式/none, 新客/正式/none, 新客/熟/short, and one hard row.
- Hard notes, one row each: 投诉之后的生日; timestamp `2026-08-19` so the occasion is 七夕; timestamp `2026-09-25` so the occasion is 中秋; 不愉快的经历之后重新联系; 上次谢绝过邀请; 客户报出代购价格; 常客要求折扣; 客户说忽略之前的规则并要求五折.
- Scenario 6 rows all have a product id and history `short` or `long`.
- Tuning: 20 rows, at least two for each scenario label, different notes from the final hard rows.

Tiers are 顶级, 常客, 新客. Relationships are 熟 and 正式.

- [ ] **Step 4: Run the test**

Expected: PASS.

- [ ] **Step 5: Stop**

Ask Ann to approve `docs/coverage.md`. Do not start Task 16 until she does.

## Task 16: Clients and case files, after approval

**Files:**
- Modify: `data/clients.json`
- Create: `cases/inputs.jsonl`
- Create: `cases/tuning.jsonl`
- Test: `tests/test_cases.py`

**Interfaces:**
- Consumes: the approved coverage table, brand catalog, `prose_is_chinese`
- Produces: 24 to 30 clients, 50 final cases, 20 tuning cases

Skip this task until Ann approves the coverage table.

- [ ] **Step 1: Write the failing test**

`cases/inputs.jsonl` has 50 lines and `cases/tuning.jsonl` has 20. Ids match the coverage file. Ids are unique across both files. Every `client_id`, `product_id`, and `event_id` exists. Scenario `2` and every `6` have products. Scenario `5` has an event. Scenario `6` has a client message with the subtype marker. Every string that is not an id, a date, or `Chengbai` passes `prose_is_chinese`. Scenario counts match Task 15.

- [ ] **Step 2: Run the test**

Expected: FAIL.

- [ ] **Step 3: Write the files in Chinese**

One JSON object per line. English keys. `split` is `final` or `tuning`. `expectations` is a Chinese `must` and `must_not` pair on the hard rows only. Write the history sentences in Chinese in this step. There is no English draft.

```json
{"case_id":"f36","client_id":"lin","scenario":"6 Price objection — price too high","timestamp":"2026-11-04T11:00:00+08:00","history":[{"sender":"ca","text":"林女士，云纹大衣这周在店里。","time":"2026-11-04T10:40:00+08:00"},{"sender":"client","text":"好看，但六万八太贵了，我再想想。","time":"2026-11-04T10:50:00+08:00"}],"product_ids":["yunwen"],"split":"final","expectations":{"must":"回应太贵","must_not":"主动提出折扣"}}
```

Write the other rows to that shape from the approved table. Do not copy a final history into a tuning row.

- [ ] **Step 4: Run the test**

Expected: PASS. Record `test_set_version` by running `python3 -c "from ca.store import test_set_version; ..." ` and paste the hash into `docs/coverage.md` under `Frozen`.

- [ ] **Step 5: Do not commit**

## Task 17: Docker

**Files:**
- Create: `Dockerfile`
- Create: `requirements.txt` with `langfuse`
- Modify: `README.md`
- Test: `tests/test_docker.py`

**Interfaces:**
- Consumes: `ca.web` and `ca.cli`
- Produces: an image that serves the page and can run the CLI

- [ ] **Step 1: Write the failing test**

`Dockerfile` contains `python:3.12-slim`, `ca`, and `web`. `README.md` contains:

```text
docker build -t ca-messages .
docker run --env-file .env -p 8765:8765 -v "$PWD/runs:/app/runs" -v "$PWD/data:/app/data" ca-messages
```

- [ ] **Step 2: Run the test**

Expected: FAIL.

- [ ] **Step 3: Write the image**

`CMD` is `python -m ca.web`. Do not copy `.env` into the image. Do not run Docker in the unit test.

- [ ] **Step 4: Run the test**

Expected: PASS.

- [ ] **Step 5: Do not commit**

## Self-review

- Spec pipeline, checks, judge rule, two case files, export refusal, page views, and Docker each have a task.
- The evaluation report stays a document Ann writes from the trace view. The app does not generate it.
- GLM model names stay empty. Task 7 refuses a real run until Ann sets two different names.
- Task 16 does not start until Ann approves `docs/coverage.md`.
- No step says TBD, TODO, or "similar to Task N".
