# Project manual

## What this project is

A fictional luxury house will use this repo to draft three Chinese WeChat messages for Client Advisors. This file is the manual for agents working here.

## Hard rules

- Fictional people and brands only.
- Do not commit Written_Challenge_Brief.pdf.
- Do not publish the brief.
- Do not invent a screenshot.
- Do not overwrite an earlier run.
- If a requirement is unclear, stop and ask the author. Do not guess.
- The future tool returns three Chinese WeChat candidates.
- A log row is not closed while its screenshot cell starts with `PENDING`.
- After a substantial step, append a row to `log/LOG.md`.
- Capture that row's screenshot with `python3 log/capture_step.py` before closing it.

## Coding practice

- Write a failing test before the change it covers.
- Edit an existing file before creating a new one.
- Keep code and docs concise.
- The default languages are Python and Markdown.
- Before finishing a document, read `.cursor/skills/deslop/SKILL.md` and apply it.

## Work log

The file on disk is `log/screenshots/step-NN-short-name.png`. A cell in `log/LOG.md` uses a path relative to `log/`: `PENDING: screenshots/step-NN-short-name.png` or `[step-NN-short-name.png](screenshots/step-NN-short-name.png)`.

A substantial step is a new plan, a design change the author accepted, or a working slice of the tool. Append the row in that same session. Run `python3 log/capture_step.py step-NN-short-name` and link the PNG it writes. The script captures the Cursor window. It does not draw an image, and it refuses to replace an existing file.

## In scope for the scaffold

`.gitignore`, `tests/test_scaffold.py`, `AGENT.md`, `AGENTS.md`, `.cursor/rules/project.mdc`, `log/LOG.md`, `log/screenshots/README.md`, `cases/cases.csv`, `docs/rubric.md`, `README.md`, and the installed `.cursor/skills/deslop/SKILL.md`.

- brand document
- message generator
- filled test cases

## Out of scope until a later plan

None.

## File map

The Scenario column allows only:

- 1 Birthday and festive greetings
- 2 Product recommendation
- 3 Post-purchase care
- 4 Reactivation
- 5 Event invitation
- 6 Price objection — price too high
- 6 Price objection — comparison
- 6 Price objection — discount request
