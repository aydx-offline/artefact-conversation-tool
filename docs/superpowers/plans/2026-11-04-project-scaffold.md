# Project Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the challenge's record-keeping and contracts in the repo before any message generator exists.

**Architecture:** `AGENT.md` is the operating manual for every coding agent in this repo. `log/LOG.md` is submission element A, with one row per step and a real screenshot per row. `cases/cases.csv` and `docs/rubric.md` lock the case columns and the draft quality bar so later generation has something to be judged against. The generator, the brand, and the fifty filled cases are a later plan.

**Tech Stack:** Markdown, one CSV, one Cursor rule, and a stdlib `unittest` file. No application dependencies.

**Spec:** `Written_Challenge_Brief.pdf` (local only; do not commit it) and the decisions in this plan. The brief's required work-log columns are: Step, What you did, Input, Output, Tool or agent used, Screenshots. The brief's required case columns are: Case ID, Scenario, Client information, Conversation history, Product information, Output 1, Output 2, Output 3. This plan adds one case column, `Generator version`, because the brief requires each result to name the tool version that produced it.

## Global Constraints

- Fictional people and brands only. No real personal data.
- Do not publish the brief. Do not commit `Written_Challenge_Brief.pdf`.
- Messages the future tool produces are three Chinese WeChat candidates covering all six scenarios. This plan does not produce those messages.
- Do not invent a screenshot. A log row stays `PENDING` until a real PNG of the chat exists.
- Do not overwrite an earlier run. No generation runs exist yet.
- Do not create a git commit unless Ann explicitly asks.
- Deadline for the whole submission is the end of 2026-11-09. This plan does not submit anything.
- Write a failing test before the change it covers.
- Edit an existing file before creating a new one. The files this plan creates are the starting set. After they exist, extend them instead of adding files.
- Keep code and docs concise.
- If a requirement is unclear, stop and ask Ann. Do not guess.
- Before finishing a document, read `.cursor/skills/deslop/SKILL.md` and apply it. The file is the Cursor team-kit skill, copied verbatim. Do not rewrite it.

## Decisions locked here

- `AGENT.md` is the manual for agents working on this repo. It is not the spec of the Client Advisor message agent. That spec comes after the brand exists.
- `AGENTS.md` is a short pointer to `AGENT.md`, so a harness that auto-reads `AGENTS.md` still reaches the manual.
- `.cursor/rules/project.mdc` repeats only the hard rules, under 50 lines, with `alwaysApply: true`.
- Scenario 6 is stored as three scenario labels: price too high, comparison, and discount request.
- `docs/rubric.md` is a draft. No generation happens until Ann accepts or edits it.
- Screenshots for the two steps that already happened are captured during Task 6 from the real Cursor chat.
- The message agent's tooling pool is undecided. This plan does not choose models, frameworks, or tools.
- Deslop is installed at `.cursor/skills/deslop/SKILL.md` from `cursor/plugins` `cursor-team-kit/skills/deslop/SKILL.md`.

## Review Focus

- The brief PDF is committed or copied into a file that will be shared. Expected: `git check-ignore` matches `Written_Challenge_Brief.pdf`, and no other file contains the brief's body. Test in Task 1.
- A work-log row is closed with a missing or fake screenshot. Expected: the cell is `PENDING: screenshots/<file>.png` or a markdown link to a file whose first bytes are a PNG. Test in Tasks 3 and 6.
- The case file drifts from the brief's column names. Expected: the header row matches the brief, plus `Generator version` at the end. Test in Task 4.
- A later run cannot be told from an earlier run. Expected: `Generator version` is in the header before any output is written. Test in Task 4.
- Scaffold work starts the generator, the brand essay, or the fifty cases. Expected: `AGENT.md` lists those as out of scope, and this plan creates none of those files. Test in Task 2.

---

### Task 1: Keep the brief out of git

**Files:**
- Create: `.gitignore`
- Create: `tests/test_scaffold.py`
- Modify: none
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Consumes: the untracked file `Written_Challenge_Brief.pdf` at the repo root
- Produces: `tests.test_scaffold.ROOT`, a `pathlib.Path` to the repo root, imported by later tests in the same module

- [ ] **Step 1: Write the failing test**

```python
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ScaffoldTest(unittest.TestCase):
    def test_brief_is_gitignored(self):
        result = subprocess.run(
            ["git", "check-ignore", "-q", "Written_Challenge_Brief.pdf"],
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 0)

    def test_gitignore_covers_local_secrets_and_caches(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for line in [".DS_Store", ".venv/", ".env", "__pycache__/"]:
            self.assertIn(line, text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 tests/test_scaffold.py -v`

Expected: FAIL because `.gitignore` does not exist.

- [ ] **Step 3: Add `.gitignore`**

Exact entries, one per line:

```
Written_Challenge_Brief.pdf
.DS_Store
.venv/
.env
__pycache__/
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 tests/test_scaffold.py -v`

Expected: PASS for the two tests in this task.

---

### Task 2: Write the project manual and load it into Cursor

**Files:**
- Create: `AGENT.md`
- Create: `AGENTS.md`
- Create: `.cursor/rules/project.mdc`
- Modify: `tests/test_scaffold.py`
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Consumes: `ROOT` from Task 1
- Produces: the headings and hard-rule sentences below. Later tasks and later sessions follow them.

- [ ] **Step 1: Write the failing test**

Add these methods to `ScaffoldTest`:

```python
    def test_agent_manual_has_required_sections_and_rules(self):
        text = (ROOT / "AGENT.md").read_text(encoding="utf-8")
        for heading in [
            "## What this project is",
            "## Hard rules",
            "## Coding practice",
            "## Work log",
            "## In scope for the scaffold",
            "## Out of scope until a later plan",
            "## File map",
        ]:
            self.assertIn(heading, text)
        for rule in [
            "Fictional people and brands only.",
            "Do not commit Written_Challenge_Brief.pdf.",
            "Do not publish the brief.",
            "Do not invent a screenshot.",
            "Do not overwrite an earlier run.",
            "If a requirement is unclear, stop and ask Ann. Do not guess.",
            "Write a failing test before the change it covers.",
            "Edit an existing file before creating a new one.",
            "Keep code and docs concise.",
            "Before finishing a document, read `.cursor/skills/deslop/SKILL.md` and apply it.",
            "1 Birthday and festive greetings",
            "2 Product recommendation",
            "3 Post-purchase care",
            "4 Reactivation",
            "5 Event invitation",
            "6 Price objection — price too high",
            "6 Price objection — comparison",
            "6 Price objection — discount request",
        ]:
            self.assertIn(rule, text)
        out_of_scope = text.split("## Out of scope until a later plan", 1)[1]
        for item in ["brand document", "message generator", "filled test cases"]:
            self.assertIn(item, out_of_scope)

    def test_agents_pointer_and_cursor_rule(self):
        self.assertIn("AGENT.md", (ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        rule = (ROOT / ".cursor/rules/project.mdc").read_text(encoding="utf-8")
        self.assertIn("alwaysApply: true", rule)
        self.assertLess(len(rule.splitlines()), 50)
        self.assertIn("AGENT.md", rule)
        self.assertIn("If a requirement is unclear, stop and ask Ann. Do not guess.", rule)
        self.assertIn("Edit an existing file before creating a new one.", rule)
        self.assertIn("Before finishing a document, read `.cursor/skills/deslop/SKILL.md` and apply it.", rule)
        skill = (ROOT / ".cursor" / "skills" / "deslop" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: deslop", skill)
        self.assertIn("# Remove AI code slop", skill)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 tests/test_scaffold.py ScaffoldTest.test_agent_manual_has_required_sections_and_rules ScaffoldTest.test_agents_pointer_and_cursor_rule -v`

Expected: FAIL because `AGENT.md` does not exist.

- [ ] **Step 3: Write the three files**

`AGENT.md` uses the seven headings in the test, in that order. Under Hard rules, include each hard-rule sentence from the test as its own bullet, plus: the future tool returns three Chinese WeChat candidates, and a log row is not closed while its screenshot cell starts with `PENDING`. Under Coding practice, include the coding sentences from the test as their own bullets, including the deslop sentence. `.cursor/skills/deslop/SKILL.md` is already installed. Do not rewrite it. Under Work log, say the file on disk is `log/screenshots/step-NN-short-name.png` and the cell in `log/LOG.md` uses the path relative to `log/`, either `PENDING: screenshots/step-NN-short-name.png` or `[step-NN-short-name.png](screenshots/step-NN-short-name.png)`. Under File map, list the scenario labels from the test as the only allowed values for the Scenario column. In scope for the scaffold is this plan's files. Out of scope names the brand document, the message generator, and the filled test cases.

`AGENTS.md` is only:

```markdown
# Agents

Read [AGENT.md](AGENT.md) before changing this repo.
```

`.cursor/rules/project.mdc` has `alwaysApply: true`, points at `AGENT.md`, and repeats the hard rules in under 50 lines. It must include these three sentences: "If a requirement is unclear, stop and ask Ann. Do not guess." "Edit an existing file before creating a new one." "Before finishing a document, read `.cursor/skills/deslop/SKILL.md` and apply it." One concern: how an agent must behave in this repo.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 tests/test_scaffold.py -v`

Expected: PASS

---

### Task 3: Open the work log and the screenshot folder

**Files:**
- Create: `log/LOG.md`
- Create: `log/screenshots/README.md`
- Modify: `tests/test_scaffold.py`
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Consumes: the work-log columns from the brief
- Produces: two seeded rows. Task 6 replaces each `PENDING` cell with a markdown link. Do not add step 3 in this task.

- [ ] **Step 1: Write the failing test**

```python
    def test_work_log_matches_the_brief_and_seeds_two_rows(self):
        text = (ROOT / "log" / "LOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "| Step | What you did | Input | Output | Tool or agent used | Screenshots |",
            text,
        )
        self.assertIn("PENDING: screenshots/step-01-review-brief.png", text)
        self.assertIn("PENDING: screenshots/step-02-scaffold-plan.png", text)
        self.assertIn("Reviewed the written challenge brief", text)
        self.assertIn("docs/superpowers/plans/2026-11-04-project-scaffold.md", text)
        shots = (ROOT / "log" / "screenshots" / "README.md").read_text(encoding="utf-8")
        self.assertIn("step-NN-short-name.png", shots)
        self.assertIn("Do not generate or draw a substitute image.", shots)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 tests/test_scaffold.py ScaffoldTest.test_work_log_matches_the_brief_and_seeds_two_rows -v`

Expected: FAIL because `log/LOG.md` does not exist.

- [ ] **Step 3: Write the log and the screenshot note**

`log/LOG.md` title is `# Work log`. One sentence says this file is submission element A. Then this table, with the two data rows filled:

| Step | What you did | Input | Output | Tool or agent used | Screenshots |
| --- | --- | --- | --- | --- | --- |
| 1 | Reviewed the written challenge brief and restated the task, the six scenarios, the submission elements, and the five-day scope. | `Written_Challenge_Brief.pdf` | Review in the Cursor chat on 2026-11-04. | Cursor agent (Grok 4.7) | PENDING: screenshots/step-01-review-brief.png |
| 2 | Planned the repo scaffold: the project manual, the work log, the case contract, and the draft rubric, before any message generator. | The brief review and the request to set up supporting files first. | `docs/superpowers/plans/2026-11-04-project-scaffold.md` | Cursor agent (Grok 4.7), writing-plans skill | PENDING: screenshots/step-02-scaffold-plan.png |

`log/screenshots/README.md` states: PNG only; name `step-NN-short-name.png`; paths in `LOG.md` are relative to `log/`; a row may close only after the file exists; `Do not generate or draw a substitute image.`

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 tests/test_scaffold.py -v`

Expected: PASS

---

### Task 4: Lock the case contract and the draft rubric

**Files:**
- Create: `cases/cases.csv`
- Create: `docs/rubric.md`
- Modify: `tests/test_scaffold.py`
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Consumes: the brief's case columns and the scenario labels in `AGENT.md`
- Produces: the CSV header later generation must append to, and the draft bar later evaluation must use. No data rows.

- [ ] **Step 1: Write the failing test**

```python
    def test_case_header_and_draft_rubric(self):
        header = (ROOT / "cases" / "cases.csv").read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(
            header,
            "Case ID,Scenario,Client information,Conversation history,Product information,Output 1,Output 2,Output 3,Generator version",
        )
        self.assertEqual(
            len((ROOT / "cases" / "cases.csv").read_text(encoding="utf-8").splitlines()),
            1,
        )
        rubric = (ROOT / "docs" / "rubric.md").read_text(encoding="utf-8")
        for heading in ["# Draft rubric", "## Good", "## Not acceptable", "## Unscored until the brand exists"]:
            self.assertIn(heading, rubric)
        self.assertIn("Draft. Do not generate messages until Ann accepts or edits this file.", rubric)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 tests/test_scaffold.py ScaffoldTest.test_case_header_and_draft_rubric -v`

Expected: FAIL because `cases/cases.csv` does not exist.

- [ ] **Step 3: Write the CSV and the draft rubric**

The CSV file contains only the header line from the test. UTF-8, no BOM, trailing newline, no data rows.

`docs/rubric.md` starts with `# Draft rubric` and the sentence `Draft. Do not generate messages until Ann accepts or edits this file.`

## Good

A candidate is good when it uses only facts present in that case, fits the named scenario, matches the relationship the client record supports, reads as Chinese a person would send on WeChat, and the three candidates are three different strategies.

## Not acceptable

- A template opener that would fit any client
- Urgency or false scarcity
- A fact, discount, or product attribute that was not in the input
- A greeting or care message that turns into a hard sell
- Three candidates that are the same strategy
- English or translationese

## Unscored until the brand exists

Brand fit is unscored until a brand document names the house, the voice, and what an advisor may not say. A discount the brand has not allowed is already not acceptable under the rule above.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 tests/test_scaffold.py -v`

Expected: PASS

---

### Task 5: Add the repo map

**Files:**
- Create: `README.md`
- Modify: `tests/test_scaffold.py`
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Consumes: the paths created in Tasks 1–4
- Produces: the entry point a later reader uses to find the work log, the cases, and the rubric

- [ ] **Step 1: Write the failing test**

```python
    def test_readme_points_at_the_scaffold(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for item in [
            "log/LOG.md",
            "cases/cases.csv",
            "docs/rubric.md",
            "AGENT.md",
            "2026-11-09",
            "Do not publish the brief.",
        ]:
            self.assertIn(item, text)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 tests/test_scaffold.py ScaffoldTest.test_readme_points_at_the_scaffold -v`

Expected: FAIL because `README.md` does not exist.

- [ ] **Step 3: Write `README.md`**

Short. What the repo is: a fictional luxury-house tool that will draft three Chinese WeChat messages for Client Advisors. Where things are: `AGENT.md`, `log/LOG.md`, `cases/cases.csv`, `docs/rubric.md`, and this plan. State `Do not publish the brief.` and the submission deadline, the end of `2026-11-09`. Say the generator is not in this repo yet.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 tests/test_scaffold.py -v`

Expected: PASS

---

### Task 6: Capture the two screenshots that already have chats

**Files:**
- Create: `log/screenshots/step-01-review-brief.png`
- Create: `log/screenshots/step-02-scaffold-plan.png`
- Modify: `log/LOG.md`
- Modify: `tests/test_scaffold.py`
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Consumes: the `PENDING` cells from Task 3
- Produces: two real PNGs and closed log cells. Later steps append a new row; they do not reuse these filenames.

- [ ] **Step 1: Write the failing test**

```python
    def test_step_screenshots_are_real_pngs_and_the_log_links_them(self):
        log = (ROOT / "log" / "LOG.md").read_text(encoding="utf-8")
        self.assertNotIn("PENDING:", log)
        for name in ["step-01-review-brief.png", "step-02-scaffold-plan.png"]:
            path = ROOT / "log" / "screenshots" / name
            data = path.read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertGreater(len(data), 10_000)
            self.assertIn(f"](screenshots/{name})", log)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 tests/test_scaffold.py ScaffoldTest.test_step_screenshots_are_real_pngs_and_the_log_links_them -v`

Expected: FAIL because the PNGs do not exist and the cells still say `PENDING`.

- [ ] **Step 3: Capture the chats and close the rows**

Open the Cursor chat that reviewed the brief and save it as `log/screenshots/step-01-review-brief.png`. Open the chat that produced this plan and save it as `log/screenshots/step-02-scaffold-plan.png`. Replace each `PENDING: screenshots/<file>.png` cell with `[<file>.png](screenshots/<file>.png)`.

Capture the real chat. Do not generate, draw, or download a substitute image. If a chat is not on screen, ask Ann to open it and stop that capture.

- [ ] **Step 4: Run the full test file**

Run: `python3 tests/test_scaffold.py -v`

Expected: PASS for every test in `tests/test_scaffold.py`.

---

## Self-review

- Spec coverage: element A is Tasks 3 and 6. The case columns for element C are the header in Task 4, with rows left empty. The "good" and "not acceptable" language required by element B is the draft rubric in Task 4, marked draft. Elements D and E, the architecture bonus, the brand, and the generator have no tasks, on purpose.
- The brief's body is not copied into the repo. The PDF stays local and gitignored.
- Screenshot cells cannot pass Task 6 on an empty or non-PNG file.
- No commit step. The global constraint forbids a commit unless Ann asks.
