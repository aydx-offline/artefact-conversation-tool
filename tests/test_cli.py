import csv
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ca.brand import load_brand
from ca.clients import load_clients
from ca.llm import FakeModel
from ca.store import RunStore, test_set_version
from ca.version import GENERATOR_VERSION

ROOT = Path(__file__).resolve().parent.parent
SCENARIO = "1 Birthday and festive greetings"
BRAND = load_brand(ROOT / "data" / "brand")
MENU = BRAND.menus[SCENARIO]
TEXTS = ["林女士，生日快乐，祝您今天一切顺心。", "上次的围巾还合用吗？有空来店里喝杯茶。", "最近天气转凉，记得添件衣裳。"]


def plan():
    return json.dumps({"picks": [{"strategy": item, "reason": "合她的情况"} for item in MENU[:3]]}, ensure_ascii=False)


def write(texts=TEXTS):
    candidates = [
        {"strategy": MENU[index], "reason": "合她的情况", "tone": "亲切温暖", "length": "简短", "text": text}
        for index, text in enumerate(texts)
    ]
    return json.dumps({"candidates": candidates}, ensure_ascii=False)


def judge_reply():
    rows = []
    for candidate in range(3):
        for item in ("事实", "期望"):
            rows.append({"candidate": candidate, "item": item, "value": "pass", "reason": "符合"})
        for item in ("场景", "称呼", "具体", "中文", "品牌", "不催"):
            rows.append({"candidate": candidate, "item": item, "value": 3, "reason": "符合"})
    return json.dumps({"scores": rows}, ensure_ascii=False)


class SelectiveModel:
    model_name = "测试写作模型"

    def complete(self, system, user):
        if "生日乙" in user:
            raise RuntimeError("断线")
        return plan() if '"picks"' in system + user else write()


class CliTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "data", self.root / "data")
        (self.root / "cases").mkdir()
        self.case = {
            "case_id": "c1",
            "client_id": "lin",
            "scenario": SCENARIO,
            "timestamp": "2026-11-04T10:00:00+08:00",
            "history": [{"sender": "client", "text": "祝您中秋快乐", "time": "2026-09-25T09:00:00+08:00"}],
            "occasion": "生日",
            "split": "final",
        }
        self.case_path = self.root / "case.json"
        self.case_path.write_text(json.dumps(self.case, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def run_id(self):
        return next((self.root / "runs" / GENERATOR_VERSION).iterdir()).name

    def test_generate_evaluate_and_export(self):
        from ca.cli import main

        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["generate", "--case", str(self.case_path)], model=FakeModel([plan(), write()]), root=self.root), 0)
        self.assertTrue(all(text in output.getvalue() for text in TEXTS))
        self.assertIn(str(self.root / "runs"), output.getvalue())

        run_id = self.run_id()
        self.assertEqual(main(["evaluate", "--run", run_id], model=FakeModel([judge_reply()]), root=self.root), 0)
        scores = self.root / "runs" / GENERATOR_VERSION / run_id / "scores.jsonl"
        self.assertTrue(scores.read_text(encoding="utf-8").strip())

        self.assertEqual(main(["export", "--run", run_id], root=self.root), 0)
        export = self.root / "cases" / "cases.csv"
        self.assertTrue(export.read_bytes().startswith(b"\xef\xbb\xbf"))
        with export.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 1)
        self.assertIn("林女士", rows[0]["Client information"])
        self.assertIn("顾客：祝您中秋快乐", rows[0]["Conversation history"])
        self.assertNotIn("client", rows[0]["Conversation history"])
        self.assertEqual(rows[0]["Generator version"], GENERATOR_VERSION)
        self.assertEqual(
            list(rows[0]),
            ["Case ID", "Scenario", "Client information", "Conversation history", "Product information", "Output 1", "Output 2", "Output 3", "Generator version"],
        )

    def test_evaluate_records_judge_error_instead_of_crashing(self):
        from ca.cli import main

        main(["generate", "--case", str(self.case_path)], model=FakeModel([plan(), write()]), root=self.root)
        run_id = self.run_id()
        raw = "不是有效评分"
        self.assertEqual(main(["evaluate", "--run", run_id], judge_model=FakeModel([raw]), root=self.root), 0)
        rows = [
            json.loads(line)
            for line in (self.root / "runs" / GENERATOR_VERSION / run_id / "scores.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(rows[0]["status"], "failed")
        self.assertEqual(rows[0]["raw"], raw)

    def test_evaluate_appends_to_the_run_version_it_reads(self):
        from ca.cli import main

        main(["generate", "--case", str(self.case_path)], model=FakeModel([plan(), write()]), root=self.root)
        run_id = self.run_id()
        current = self.root / "runs" / GENERATOR_VERSION
        previous = self.root / "runs" / "0.0.9"
        current.rename(previous)
        self.assertEqual(main(["evaluate", "--run", run_id], judge_model=FakeModel([judge_reply()]), root=self.root), 0)
        self.assertTrue((previous / run_id / "scores.jsonl").exists())
        self.assertFalse((current / run_id / "scores.jsonl").exists())

    def test_export_refuses_tuning_and_incomplete_runs(self):
        from ca.cli import main

        self.case["split"] = "tuning"
        self.case_path.write_text(json.dumps(self.case, ensure_ascii=False), encoding="utf-8")
        main(["generate", "--case", str(self.case_path)], model=FakeModel([plan(), write()]), root=self.root)
        with self.assertRaises(SystemExit):
            main(["export", "--run", self.run_id()], root=self.root)

        other = self.root / "other"
        shutil.copytree(self.root / "data", other / "data")
        (other / "cases").mkdir(parents=True)
        store = RunStore(other / "runs")
        run_id = store.begin({"writer_model": "测试", "brand_hash": "", "client_store_hash": "", "test_set_version": "", "split": "final", "case_ids": ["missing"]})
        store.finish_manifest(run_id, {"end": "现在", "case_statuses": {"missing": "failed"}})
        with self.assertRaises(SystemExit):
            main(["export", "--run", run_id], root=other)

    def test_batch_continues_after_a_failed_case(self):
        from ca.cli import main

        rows = [
            {**self.case, "case_id": "c1", "occasion": "生日甲", "split": "tuning"},
            {**self.case, "case_id": "c2", "occasion": "生日乙", "split": "tuning"},
        ]
        cases = self.root / "cases" / "tuning.jsonl"
        cases.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
        inputs = self.root / "cases" / "inputs.jsonl"
        inputs.write_text(json.dumps({**self.case, "case_id": "f1"}, ensure_ascii=False) + "\n", encoding="utf-8")
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["batch", "--cases", str(cases)], model=SelectiveModel(), root=self.root), 0)
        self.assertIn("c1 done", output.getvalue())
        self.assertIn("c2 failed", output.getvalue())
        run_dir = self.root / "runs" / GENERATOR_VERSION / self.run_id()
        manifest = {
            **json.loads((run_dir / "manifest.json").read_text(encoding="utf-8")),
            **json.loads((run_dir / "manifest.end.json").read_text(encoding="utf-8")),
        }
        self.assertEqual(manifest["case_statuses"], {"c1": "done", "c2": "failed"})
        self.assertEqual(
            manifest["test_set_version"],
            test_set_version(inputs, cases, [load_clients(self.root / "data" / "clients.json")["lin"]]),
        )

    def test_before_after_exports_only_changed_cases(self):
        from ca.cli import main

        before = self._stored_run(TEXTS, "版本甲")
        after = self._stored_run([*TEXTS[:2], "林女士，愿您每天都有好心情。"], "版本乙")
        self.assertEqual(main(["export", "--before", before, "--after", after], root=self.root), 0)
        with (self.root / "cases" / "before-after.csv").open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 1)
        self.assertEqual(list(rows[0]), ["Case ID", "Scenario", "Before 1", "Before 2", "Before 3", "After 1", "After 2", "After 3", "Before version", "After version"])
        self.assertEqual(rows[0]["Before version"], GENERATOR_VERSION)
        self.assertEqual(rows[0]["After version"], GENERATOR_VERSION)

    def _stored_run(self, texts, version):
        store = RunStore(self.root / "runs")
        run_id = store.begin(
            {"writer_model": "测试", "brand_hash": "", "client_store_hash": "", "test_set_version": version, "split": "final", "case_ids": ["c1", "c2"]}
        )
        for case_id, candidate_texts in (("c1", texts), ("c2", TEXTS)):
            store.write_case(
                run_id,
                case_id,
                {
                    "case": {**self.case, "case_id": case_id},
                    "resolved": {"client": {"name": "林女士"}, "history": [], "products": []},
                    "candidates": [{"text": text} for text in candidate_texts],
                    "status": "done",
                },
            )
        store.finish_manifest(run_id, {"end": "现在", "case_statuses": {"c1": "done", "c2": "done"}, "test_set_version": version})
        return run_id

    def test_missing_key_exits_before_begin(self):
        from ca.cli import main

        with patch.dict(os.environ, {}, clear=True), patch("ca.cli.RunStore.begin") as begin:
            with self.assertRaises(SystemExit):
                main(["generate", "--case", str(self.case_path)], root=self.root)
        begin.assert_not_called()


if __name__ == "__main__":
    unittest.main()
