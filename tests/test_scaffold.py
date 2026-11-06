import subprocess
import re
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
        for line in [".DS_Store", ".venv/", ".env", "__pycache__/", "runs/"]:
            self.assertIn(line, text)

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
            "If a requirement is unclear, stop and ask the author. Do not guess.",
            "Write a failing test before the change it covers.",
            "Edit an existing file before creating a new one.",
            "Keep code and docs concise.",
            "The default languages are Python and Markdown.",
            "Before finishing a document, read `.cursor/skills/deslop/SKILL.md` and apply it.",
            "After a substantial step, append a row to `log/LOG.md`.",
            "Capture that row's screenshot with `python3 log/capture_step.py` before closing it.",
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
        in_scope = text.split("## In scope for the scaffold", 1)[1].split(
            "## Out of scope until a later plan", 1
        )[0]
        for item in ["brand document", "message generator", "filled test cases"]:
            self.assertIn(item, in_scope)
        out_of_scope = text.split("## Out of scope until a later plan", 1)[1].split(
            "## File map", 1
        )[0]
        self.assertEqual(out_of_scope.strip(), "None.")

    def test_agents_pointer_and_cursor_rule(self):
        self.assertIn("AGENT.md", (ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        rule = (ROOT / ".cursor/rules/project.mdc").read_text(encoding="utf-8")
        self.assertIn("alwaysApply: true", rule)
        self.assertLess(len(rule.splitlines()), 50)
        self.assertIn("AGENT.md", rule)
        self.assertIn("If a requirement is unclear, stop and ask the author. Do not guess.", rule)
        self.assertIn("Edit an existing file before creating a new one.", rule)
        self.assertIn("The default languages are Python and Markdown.", rule)
        self.assertIn("Before finishing a document, read `.cursor/skills/deslop/SKILL.md` and apply it.", rule)
        self.assertIn("After a substantial step, append a row to `log/LOG.md`.", rule)
        self.assertIn("Capture that row's screenshot with `python3 log/capture_step.py` before closing it.", rule)
        skill = (ROOT / ".cursor" / "skills" / "deslop" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: deslop", skill)
        self.assertIn("# Remove AI code slop", skill)

    def test_work_log_matches_the_brief_and_seeds_two_rows(self):
        text = (ROOT / "log" / "LOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "| Step | What you did | Input | Output | Tool or agent used | Screenshots |",
            text,
        )
        self.assertRegex(text, r"\| 1 \|[^\n]*screenshots/step-01-[a-z0-9-]+\.png")
        self.assertIn("Reviewed the brief", text)
        self.assertIn("docs/superpowers/plans/2026-11-04-project-scaffold.md", text)
        shots = (ROOT / "log" / "screenshots" / "README.md").read_text(encoding="utf-8")
        self.assertIn("step-NN-short-name.png", shots)
        self.assertIn("Do not generate or draw a substitute image.", shots)

    def test_case_header_and_draft_rubric(self):
        header = (ROOT / "cases" / "cases.csv").read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(
            header,
            "Case ID,Scenario,Client information,Conversation history,Product information,Output 1,Output 2,Output 3,Generator version",
        )
        rubric = (ROOT / "docs" / "rubric.md").read_text(encoding="utf-8")
        for heading in ["# Rubric", "## Good", "## Not acceptable"]:
            self.assertIn(heading, rubric)
        self.assertNotIn("## Unscored until the brand exists", rubric)
        self.assertNotIn("hard sell", rubric)
        self.assertNotIn("Draft", rubric)
        for line in [
            "## Scoring",
            "A candidate is acceptable",
            "no 1–5 item is below 3",
            "Facts, dates, and details come from the input",
            "English names that the brand allows are not a failure",
            "Brand fit is a 1–5 judge item.",
            "a 1–5 item passes at 3 or above",
        ]:
            self.assertIn(line, rubric)

    def test_readme_points_at_the_scaffold(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for item in [
            "log/LOG.md",
            "cases/cases.csv",
            "docs/rubric.md",
            "AGENT.md",
            "must not be published",
        ]:
            self.assertIn(item, text)

    def test_step_screenshots_are_real_pngs_and_the_log_links_them(self):
        log = (ROOT / "log" / "LOG.md").read_text(encoding="utf-8")
        self.assertNotIn("PENDING:", log)
        names = re.findall(r"\]\(screenshots/(step-\d{2}-[a-z0-9-]+\.png)\)", log)
        self.assertTrue(names)
        for name in names:
            data = (ROOT / "log" / "screenshots" / name).read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertGreater(len(data), 10_000)

class CaptureStepTest(unittest.TestCase):
    def test_screenshot_name_and_refuses_to_overwrite(self):
        import importlib.util

        path = ROOT / "log" / "capture_step.py"
        spec = importlib.util.spec_from_file_location("capture_step", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        dest = module.destination("step-05-spec-revision")
        self.assertEqual(dest, ROOT / "log" / "screenshots" / "step-05-spec-revision.png")
        with self.assertRaises(SystemExit):
            module.destination("notes")
        real = ROOT / "log" / "screenshots" / "step-01-review-brief.png"
        before = real.read_bytes() if real.exists() else None
        existing = ROOT / "log" / "screenshots" / "step-99-test-only.png"
        existing.write_bytes(b"x")
        try:
            with self.assertRaises(SystemExit):
                module.refuse_overwrite(existing)
        finally:
            existing.unlink()
        self.assertEqual(real.read_bytes() if real.exists() else None, before)


if __name__ == "__main__":
    unittest.main()
