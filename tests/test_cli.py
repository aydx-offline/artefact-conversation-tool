import csv
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from ca.brand import load_brand
from ca.clients import load_clients
from ca.llm import FakeModel
from ca.schema import load_case
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
        self.assertFalse(export.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertEqual(
            export.read_text(encoding="utf-8").splitlines()[0],
            "Case ID,Scenario,Client information,Conversation history,Product information,Output 1,Output 2,Output 3,Generator version",
        )
        with export.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 1)
        self.assertIn("姓名：林女士", rows[0]["Client information"])
        self.assertIn("等级：常客", rows[0]["Client information"])
        self.assertIn("购买记录：素缎围巾（2026-03-02，米白，", rows[0]["Client information"])
        self.assertNotIn("「", rows[0]["Client information"])
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
        self.assertEqual(main(["evaluate", "--run", run_id], judge_model=FakeModel([raw, raw, raw]), root=self.root), 0)
        rows = [
            json.loads(line)
            for line in (self.root / "runs" / GENERATOR_VERSION / run_id / "scores.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(rows[0]["status"], "failed")
        self.assertEqual(rows[0]["raw"], raw)

    def test_evaluate_skips_failed_and_incomplete_cases(self):
        from ca.cli import main

        run_id = self._stored_status_run(
            [
                ("short", "failed_checks", TEXTS[:2]),
                ("failed", "failed", []),
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["evaluate", "--run", run_id], judge_model=FakeModel([]), root=self.root), 0)
        self.assertEqual(output.getvalue().splitlines(), ["short skipped", "failed skipped"])
        self.assertFalse((self.root / "runs" / GENERATOR_VERSION / run_id / "scores.jsonl").exists())

    def test_evaluate_records_unexpected_error_and_continues(self):
        from ca.cli import main
        from ca.judge import evaluation_id

        run_id = self._stored_status_run(
            [
                ("broken", "done", TEXTS),
                ("good", "done", TEXTS),
            ]
        )
        error = RuntimeError("judge unavailable")
        error.raw = "upstream reply"
        def judged(case_file, *_):
            if case_file["case"]["case_id"] == "broken":
                raise error
            return [{"case_id": "good", "status": "ok"}]

        with patch("ca.cli.evaluate_case", side_effect=judged):
            self.assertEqual(main(["evaluate", "--run", run_id], judge_model=FakeModel([]), root=self.root), 0)
        rows = [
            json.loads(line)
            for line in (self.root / "runs" / GENERATOR_VERSION / run_id / "scores.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertRegex(rows[0]["evaluation_id"], r"^\d{4}-\d{2}-\d{2}T.*:[0-9a-f]{32}$")
        self.assertRegex(evaluation_id(), r"^\d{4}-\d{2}-\d{2}T.*:[0-9a-f]{32}$")
        self.assertEqual(rows[0]["reason"], "judge unavailable")
        self.assertEqual(rows[0]["raw"], "upstream reply")
        self.assertEqual(rows[1]["case_id"], "good")

    def test_evaluate_judges_cases_in_parallel(self):
        import threading

        from ca.cli import main

        run_id = self._stored_status_run([("a", "done", TEXTS), ("b", "done", TEXTS)])
        barrier = threading.Barrier(2, timeout=5)

        def judged(case_file, *_):
            barrier.wait()
            return [{"case_id": case_file["case"]["case_id"], "status": "ok"}]

        with patch("ca.cli.evaluate_case", side_effect=judged):
            self.assertEqual(main(["evaluate", "--run", run_id], judge_model=FakeModel([]), root=self.root), 0)
        rows = (self.root / "runs" / GENERATOR_VERSION / run_id / "scores.jsonl").read_text(encoding="utf-8")
        self.assertEqual([(json.loads(line)["case_id"], json.loads(line)["status"]) for line in rows.splitlines()], [("a", "ok"), ("b", "ok")])

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

    def test_export_labels_client_and_product_cells(self):
        from ca.cli import main

        run_id = self._stored_status_run([("a", "done", TEXTS)])
        path = self.root / "runs" / GENERATOR_VERSION / run_id / "cases" / "a.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        scarf = next(p for p in BRAND.catalog if p["id"] == "scarf")
        data["resolved"] = {"client": load_clients(ROOT / "data" / "clients.json")["lin"], "history": [], "products": [scarf], "today": "2026-11-06"}
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        main(["export", "--run", run_id], root=self.root)
        with (self.root / "cases" / "cases.csv").open(encoding="utf-8", newline="") as file:
            row = next(csv.DictReader(file))
        self.assertIn("姓名：林女士；等级：常客；关系：熟", row["Client information"])
        self.assertIn("上次到店：2026-03-02（8个月前）", row["Client information"])
        self.assertIn("产品：素缎围巾；系列：素缎系列；价格：12800元", row["Product information"])
        self.assertIn("颜色：", row["Product information"])
        self.assertNotIn("scarf", row["Client information"] + row["Product information"])

    def test_report_summarises_good_cases_items_and_problems(self):
        from ca.cli import main

        run_id = self._stored_status_run([("a", "done", TEXTS), ("b", "done", TEXTS), ("c", "failed", [])])
        store = RunStore(self.root / "runs")
        for case_id, bad in (("a", False), ("b", True)):
            for row in json.loads(judge_reply())["scores"]:
                if bad and row["candidate"] == 1 and row["item"] == "事实":
                    row = {**row, "value": "fail", "reason": "编造新品"}
                store.append(run_id, "scores.jsonl", {"case_id": case_id, "evaluation_id": "e1", "judge_version": "j", **row})
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["report", "--run", run_id], root=self.root), 0)
        text = output.getvalue()
        self.assertIn("good: 1 of 2 judged cases", text)
        self.assertIn("not judged: c", text)
        self.assertIn(f"{SCENARIO}: 1 / 2", text)
        self.assertIn("事实 0.83", text)
        self.assertIn("场景 3.00", text)
        self.assertIn("b 1 事实 fail: 编造新品", text)
        self.assertNotIn("a 1 事实", text)

    def test_export_refuses_tuning_but_exports_incomplete_run(self):
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
        store.write_case(
            run_id,
            "missing",
            {"case": {**self.case, "case_id": "missing"}, "resolved": {}, "candidates": [], "status": "failed"},
        )
        store.finish_manifest(run_id, {"end": "现在", "case_statuses": {"missing": "failed"}})
        self.assertEqual(main(["export", "--run", run_id], root=other), 0)
        with (other / "cases" / "cases.csv").open(encoding="utf-8", newline="") as file:
            row = next(csv.DictReader(file))
        self.assertEqual([row[f"Output {number}"] for number in range(1, 4)], ["", "", ""])

    def test_export_includes_done_failed_checks_and_failed_cases(self):
        from ca.cli import main

        run_id = self._stored_status_run(
            [
                ("done", "done", TEXTS),
                ("checks", "failed_checks", TEXTS),
                ("failed", "failed", []),
            ]
        )
        self.assertEqual(main(["export", "--run", run_id], root=self.root), 0)
        with (self.root / "cases" / "cases.csv").open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual([row["Case ID"] for row in rows], ["done", "checks", "failed"])
        self.assertEqual(rows[1]["Output 1"], TEXTS[0])
        self.assertEqual([rows[2][f"Output {number}"] for number in range(1, 4)], ["", "", ""])

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
            self.assertEqual(main(["batch", "--cases", str(cases)], model=SelectiveModel(), root=self.root), 1)
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

    def test_timeout_and_worker_settings_parse_with_defaults(self):
        from ca.cli import _models, _workers

        env = {"GLM_API_KEY": "key", "WRITER_MODEL": "writer", "JUDGE_MODEL": "judge"}
        writer, judge = _models(env, None, None)
        self.assertEqual((writer.timeout, judge.timeout, _workers(env)), (60, 300, 2))

        configured = {**env, "GLM_TIMEOUT": "45", "JUDGE_TIMEOUT": "200", "CA_WORKERS": "3"}
        writer, judge = _models(configured, None, None)
        self.assertEqual((writer.timeout, judge.timeout, _workers(configured)), (45, 200, 3))

    def test_batch_rejects_duplicate_ids_before_begin(self):
        from ca.cli import main

        cases = self.root / "cases" / "duplicates.jsonl"
        cases.write_text(
            "\n".join(json.dumps({**self.case, "case_id": "same"}, ensure_ascii=False) for _ in range(2)),
            encoding="utf-8",
        )
        with patch("ca.cli.RunStore.begin") as begin:
            with self.assertRaisesRegex(SystemExit, "Duplicate case_id: same"):
                main(["batch", "--cases", str(cases)], model=FakeModel([]), root=self.root)
        begin.assert_not_called()

    def test_batch_rejects_mixed_splits(self):
        from ca.cli import main

        cases = self.root / "cases" / "mixed.jsonl"
        rows = [
            {**self.case, "case_id": "final", "split": "final"},
            {**self.case, "case_id": "tuning", "split": "tuning"},
        ]
        cases.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
        with patch("ca.cli.RunStore.begin") as begin:
            with self.assertRaisesRegex(SystemExit, "mixes splits"):
                main(["batch", "--cases", str(cases)], model=FakeModel([]), root=self.root)
        begin.assert_not_called()

    def test_generate_returns_one_when_case_fails(self):
        from ca.cli import main

        self.assertEqual(main(["generate", "--case", str(self.case_path)], model=FakeModel([RuntimeError("断线")] * 3), root=self.root), 1)

    def test_worker_does_not_rewrite_after_successful_case_write(self):
        from ca.cli import _generate_one

        class LateFailure:
            resolved = {}
            steps = []
            candidates = []
            checks = []

            def __init__(self):
                self.reads = 0

            @property
            def status(self):
                self.reads += 1
                if self.reads == 2:
                    raise RuntimeError("late failure")
                return "done"

        case = load_case(self.case_path)
        store = Mock()
        result = LateFailure()
        with patch("ca.cli.generate", return_value=result):
            self.assertEqual(_generate_one(case, FakeModel([]), BRAND, {}, store, "run"), "done")
        store.write_case.assert_called_once()

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
                    "resolved": {"client": load_clients(ROOT / "data" / "clients.json")["lin"], "history": [], "products": []},
                    "candidates": [{"text": text} for text in candidate_texts],
                    "status": "done",
                },
            )
        store.finish_manifest(run_id, {"end": "现在", "case_statuses": {"c1": "done", "c2": "done"}, "test_set_version": version})
        return run_id

    def _stored_status_run(self, cases):
        store = RunStore(self.root / "runs")
        run_id = store.begin(
            {
                "writer_model": "测试",
                "brand_hash": "",
                "client_store_hash": "",
                "test_set_version": "",
                "split": "final",
                "case_ids": [case_id for case_id, _, _ in cases],
            }
        )
        for case_id, status, texts in cases:
            store.write_case(
                run_id,
                case_id,
                {
                    "case": {**self.case, "case_id": case_id},
                    "resolved": {"client": load_clients(ROOT / "data" / "clients.json")["lin"], "history": [], "products": []},
                    "candidates": [{"text": text} for text in texts],
                    "checks": [],
                    "status": status,
                },
            )
        store.finish_manifest(run_id, {"end": "现在", "case_statuses": {case_id: status for case_id, status, _ in cases}})
        return run_id

    def test_missing_key_exits_before_begin(self):
        from ca.cli import main

        with patch.dict(os.environ, {}, clear=True), patch("ca.cli.RunStore.begin") as begin:
            with self.assertRaises(SystemExit):
                main(["generate", "--case", str(self.case_path)], root=self.root)
        begin.assert_not_called()


if __name__ == "__main__":
    unittest.main()
