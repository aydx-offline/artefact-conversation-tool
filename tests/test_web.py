import io
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ca.brand import load_brand
from ca.clients import load_clients
from ca.llm import FakeModel
from ca.store import RunStore

ROOT = Path(__file__).resolve().parent.parent
SCENARIO = "1 Birthday and festive greetings"


def chat_reply(name="林女士", scenario="价格异议：和其他渠道比较", message="价格比别处贵"):
    return json.dumps(
        {"client_name": name, "scenario": scenario, "client_message": message},
        ensure_ascii=False,
    )


def plan_reply(brand, scenario=SCENARIO):
    return json.dumps(
        {"picks": [{"strategy": value, "reason": "合适"} for value in brand.menus[scenario][:3]]},
        ensure_ascii=False,
    )


def write_reply(brand, scenario=SCENARIO):
    texts = ["林女士，生日快乐，愿您顺心。", "生日将至，愿您日日从容。", "想起您，祝您生日愉快。"]
    return json.dumps(
        {
            "candidates": [
                {
                    "strategy": strategy,
                    "reason": "合适",
                    "tone": "亲切温暖",
                    "length": "简短",
                    "text": text,
                }
                for strategy, text in zip(brand.menus[scenario][:3], texts)
            ]
        },
        ensure_ascii=False,
    )


class WebTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "data", self.root / "data")
        (self.root / "cases").mkdir()
        (self.root / "web").mkdir()
        shutil.copy(ROOT / "web" / "index.html", self.root / "web" / "index.html")
        self.brand = load_brand(self.root / "data" / "brand")
        self.model = FakeModel([])
        self.deps = SimpleNamespace(
            root=self.root,
            clients_path=self.root / "data" / "clients.json",
            brand=self.brand,
            model=self.model,
            telemetry=None,
            batch_state=None,
        )

    def tearDown(self):
        self.temp.cleanup()

    def call(self, method, path, body=None, headers=None):
        from ca.web import handle

        return handle(method, path, body, self.deps, headers=headers)

    def test_server_host_uses_argument_then_environment_then_loopback(self):
        from ca.web import _server_args

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_server_args([]).host, "127.0.0.1")
        with patch.dict(os.environ, {"CA_WEB_HOST": "0.0.0.0"}, clear=True):
            self.assertEqual(_server_args([]).host, "0.0.0.0")
            self.assertEqual(_server_args(["--host", "127.0.0.1"]).host, "127.0.0.1")

    def case(self, **changes):
        value = {
            "case_id": "web-1",
            "client_id": "lin",
            "scenario": SCENARIO,
            "timestamp": "2026-11-04T10:00:00+08:00",
            "occasion": "生日",
        }
        value.update(changes)
        return value

    def test_chat_returns_confirmable_case_without_run_and_combines_history(self):
        clients = load_clients(self.deps.clients_path)
        clients["lin"]["history"] = [
            {"sender": "ca", "text": "前次问候", "time": "2026-11-03T10:00:00+08:00"}
        ]
        self.deps.clients_path.write_text(json.dumps(clients, ensure_ascii=False), encoding="utf-8")
        self.deps.model = FakeModel([chat_reply()])

        status, payload = self.call("POST", "/api/chat", {"request": "林女士说价格比别处贵，帮我回一下。"})

        self.assertEqual(status, 200)
        self.assertEqual([row["text"] for row in payload["case"]["history"]], ["前次问候", "价格比别处贵"])
        self.assertFalse((self.root / "runs").exists())

    def test_chat_unknown_client_returns_404_pick_message(self):
        self.deps.model = FakeModel([chat_reply(name="不存在", scenario="重新联系", message="")])
        status, payload = self.call("POST", "/api/chat", {"request": "请帮不存在的客户重新联系。"})
        self.assertEqual(status, 404)
        self.assertIn("请选择客户", payload["error"])

    def test_generate_rejects_required_fields_before_model_call(self):
        cases = (
            (self.case(scenario="2 Product recommendation", product_ids=[]), "product_ids"),
            (self.case(scenario="5 Event invitation", event_id=""), "event_id"),
            (self.case(occasion="", timestamp="2026-11-04T10:00:00+08:00"), "occasion"),
            (
                self.case(
                    scenario="4 Reactivation",
                    history=[{"sender": "client", "text": "Price too high", "time": "2026-11-04T10:00:00+08:00"}],
                ),
                "history",
            ),
        )
        with patch("ca.web.generate") as run:
            for case, field in cases:
                with self.subTest(field=field):
                    status, payload = self.call("POST", "/api/generate", case)
                    self.assertEqual(status, 400)
                    self.assertIn(field, payload["error"])
            run.assert_not_called()
        self.assertEqual(self.deps.model.calls, [])
        self.assertFalse((self.root / "runs").exists())

    def test_generate_rejects_non_string_product_id(self):
        status, payload = self.call(
            "POST",
            "/api/generate",
            self.case(scenario="2 Product recommendation", product_ids=[{"id": "scarf"}]),
        )
        self.assertEqual(status, 400)
        self.assertIn("product_ids", payload["error"])

    def test_generate_returns_three_candidates_and_writes_run(self):
        self.deps.model = FakeModel([plan_reply(self.brand), write_reply(self.brand)])
        status, payload = self.call("POST", "/api/generate", self.case())
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "done")
        self.assertEqual(len(payload["candidates"]), 3)
        self.assertTrue(next((self.root / "runs").glob("*/*/manifest.end.json")).is_file())

    def test_chat_case_with_empty_products_can_generate_reactivation(self):
        scenario = "4 Reactivation"
        self.deps.model = FakeModel(
            [
                chat_reply(scenario="重新联系", message=""),
                plan_reply(self.brand, scenario),
                write_reply(self.brand, scenario),
            ]
        )
        status, chat = self.call("POST", "/api/chat", {"request": "请帮林女士重新联系。"})
        self.assertEqual(status, 200)
        self.assertEqual(chat["case"]["product_ids"], [])
        status, generated = self.call("POST", "/api/generate", chat["case"])
        self.assertEqual(status, 200)
        self.assertEqual(generated["status"], "done")

    def test_generate_hides_unexpected_exception(self):
        class SecretFailure(Exception):
            pass

        with patch("ca.web.generate", side_effect=SecretFailure("api-key-secret")):
            status, payload = self.call("POST", "/api/generate", self.case())
        self.assertEqual(status, 500)
        self.assertNotIn("api-key-secret", payload["error"])
        self.assertNotIn("Traceback", payload["error"])

    def test_model_lookup_runtime_error_returns_503_for_chat_and_generate(self):
        class RaisingDeps(dict):
            def get(self, name, default=None):
                if name == "model":
                    raise RuntimeError("缺少 GLM 配置: api-key-secret")
                return super().get(name, default)

        deps = RaisingDeps(vars(self.deps))
        for path, body in (
            ("/api/chat", {"request": "请帮林女士重新联系。"}),
            ("/api/generate", self.case()),
        ):
            with self.subTest(path=path):
                from ca.web import handle

                status, payload = handle("POST", path, body, deps)
                self.assertEqual(status, 503)
                self.assertIn("缺少 GLM 配置", payload["error"])
                self.assertNotIn("key", payload["error"].lower())

    def test_missing_setting_name_is_preserved(self):
        self.deps.model = None
        self.deps.model_error = "Missing required setting: GLM_API_KEY"

        status, payload = self.call("POST", "/api/chat", {"request": "请帮林女士重新联系。"})

        self.assertEqual(status, 503)
        self.assertEqual(payload["error"], "Missing required setting: GLM_API_KEY")

    def test_client_routes_include_put(self):
        status, payload = self.call("GET", "/api/clients")
        self.assertEqual(status, 200)
        self.assertIn("lin", payload["clients"])
        updated = {**payload["clients"]["lin"], "preferences": "喜欢淡色真丝"}
        status, _ = self.call("PUT", "/api/clients/lin", updated)
        self.assertEqual(status, 200)
        self.assertEqual(load_clients(self.deps.clients_path)["lin"]["preferences"], "喜欢淡色真丝")

    def test_client_post_is_create_only(self):
        client = load_clients(self.deps.clients_path)["lin"]
        status, _ = self.call("POST", "/api/clients", client)
        self.assertEqual(status, 409)

    def test_runs_merge_end_manifest_group_versions_and_flag_differences(self):
        first = self.stored_run("0.1.0", "客户甲", "测试甲")
        second = self.stored_run("0.2.0", "客户乙", "测试甲")
        status, payload = self.call("GET", "/api/runs")
        self.assertEqual(status, 200)
        self.assertEqual({item["version"] for item in payload["versions"]}, {"0.1.0", "0.2.0"})
        self.assertEqual(payload["versions"][0]["runs"][0]["case_statuses"], {"c1": "done"})
        comparison = next(item for item in payload["comparisons"] if {item["left"], item["right"]} == {first, second})
        self.assertEqual(comparison["flags"], ["client_store_hash"])

    def test_trace_returns_steps_prompts_raw_checks_and_scores(self):
        run_id = self.stored_run("0.1.0", "客户甲", "测试甲")
        status, payload = self.call("GET", f"/api/runs/0.1.0/{run_id}/cases/c1")
        self.assertEqual(status, 200)
        for key in ("steps", "prompts", "raw", "checks", "scores"):
            self.assertIn(key, payload)

    def test_feedback_copy_appends_feedback_and_client_history(self):
        run_id = self.stored_run("0.1.0", "客户甲", "测试甲")
        body = {
            "run_id": run_id,
            "case_id": "c1",
            "client_id": "lin",
            "candidate": 0,
            "strategy": "问候",
            "tone": "亲切温暖",
            "original_text": "原文",
            "copied_text": "修改后",
            "edited": True,
            "action": "copy",
            "time": "2026-11-04T10:00:00+08:00",
        }
        status, _ = self.call("POST", "/api/feedback", body)
        self.assertEqual(status, 200)
        self.assertEqual(load_clients(self.deps.clients_path)["lin"]["history"][-1]["text"], "修改后")
        feedback = self.root / "runs" / "0.1.0" / run_id / "feedback.jsonl"
        self.assertEqual(json.loads(feedback.read_text(encoding="utf-8"))["edited"], True)

    def test_concurrent_feedback_copies_keep_both_messages(self):
        run_id = self.stored_run("0.1.0", "客户甲", "测试甲")
        barrier = threading.Barrier(2)

        def copy(text):
            body = {
                "run_id": run_id,
                "case_id": "c1",
                "client_id": "lin",
                "candidate": 0,
                "strategy": "问候",
                "tone": "亲切温暖",
                "original_text": "原文",
                "copied_text": text,
                "edited": True,
                "action": "copy",
                "time": "2026-11-04T10:00:00+08:00",
            }
            barrier.wait()
            self.assertEqual(self.call("POST", "/api/feedback", body)[0], 200)

        threads = [threading.Thread(target=copy, args=(text,)) for text in ("消息甲", "消息乙")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        history = load_clients(self.deps.clients_path)["lin"]["history"]
        self.assertEqual({row["text"] for row in history[-2:]}, {"消息甲", "消息乙"})

    def test_bad_body_unknown_routes_and_unknown_runs(self):
        self.assertEqual(self.call("POST", "/api/chat", "{bad")[0], 400)
        self.assertEqual(self.call("POST", "/api/chat", [])[0], 400)
        self.assertEqual(self.call("GET", "/api/nope")[0], 404)
        self.assertEqual(self.call("GET", "/api/runs/0.1.0/nope/cases/c1")[0], 404)
        self.assertEqual(self.call("GET", "/api/runs/../x/cases/c1")[0], 400)
        self.assertEqual(self.call("PUT", "/api/clients/..", {})[0], 400)
        self.assertEqual(self.call("GET", "/api/runs/0.1.0/run*/cases/c1")[0], 400)

    def test_write_request_security_headers(self):
        body = {"request": "请帮林女士重新联系。"}
        trusted = {
            "Content-Type": "application/json",
            "Host": "127.0.0.1:8765",
            "Origin": "http://localhost:8765",
        }
        self.assertEqual(self.call("POST", "/api/chat", body, {**trusted, "Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.call("POST", "/api/chat", body, {**trusted, "Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.call("POST", "/api/chat", body, {**trusted, "Host": "evil.example"})[0], 403)

    def test_get_requires_local_host_through_guard_and_handle(self):
        from ca.web import _request_guard

        self.assertEqual(_request_guard("GET", {"Host": "evil.example"}, 8765)[0], 403)
        self.assertIsNone(_request_guard("GET", {"Host": "localhost:8765"}, 8765))
        self.assertEqual(self.call("GET", "/", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.call("GET", "/", headers={"Host": "127.0.0.1:8765"})[0], 200)

    def test_request_body_is_capped_at_one_mib(self):
        from ca.web import _request_guard

        status, payload = _request_guard(
            "POST",
            {"Content-Type": "application/json", "Host": "localhost:8765"},
            8765,
            1024 * 1024 + 1,
        )
        self.assertEqual(status, 413)
        self.assertIn("过大", payload["error"])

    def test_live_handler_rejects_invalid_lengths_and_closes_oversize_connection(self):
        from ca.web import Handler, MAX_BODY_SIZE

        def serve(length):
            handler = Handler.__new__(Handler)
            handler.command = "POST"
            handler.path = "/api/chat"
            handler.headers = {
                "Content-Length": length,
                "Content-Type": "application/json",
                "Host": "localhost:8765",
            }
            handler.server = SimpleNamespace(server_port=8765)
            handler.rfile = io.BytesIO(b'{"request":"x"}')
            handler.wfile = io.BytesIO()
            handler.deps = self.deps
            handler.send_response = lambda status: setattr(handler, "status", status)
            handler.send_header = lambda *args: None
            handler.end_headers = lambda: None
            handler._serve()
            return handler

        self.assertEqual(serve("nope").status, 400)
        self.assertEqual(serve("-1").status, 400)
        oversized = serve(str(MAX_BODY_SIZE + 1))
        self.assertEqual(oversized.status, 413)
        self.assertTrue(oversized.close_connection)

    def test_html_has_six_regions(self):
        status, payload = self.call("GET", "/")
        self.assertEqual(status, 200)
        for region in ("case-form", "chat", "clients", "trace", "batch", "versions"):
            self.assertIn(f'id="{region}"', payload["body"])

    def test_html_builds_dynamic_content_without_inner_html(self):
        html = (self.root / "web" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn(".innerHTML", html)
        self.assertIn("createElement", html)
        self.assertIn("replaceChildren", html)
        self.assertIn("textContent", html)
        self.assertIn(".value", html)

    def test_html_fill_form_normalizes_arrays_and_null(self):
        html = (self.root / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('Array.isArray(value)?value.join(",")', html)
        self.assertIn('value==null?"":value', html)

    def test_html_batch_view_displays_server_error_with_text_content(self):
        html = (self.root / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('$("#batch .error").textContent=data.error||""', html)

    def test_batch_conflict_stop_and_cancelled_case_file(self):
        rows = [self.case(case_id=f"c{i}", split="tuning") for i in range(5)]
        (self.root / "cases" / "tuning.jsonl").write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows),
            encoding="utf-8",
        )
        (self.root / "cases" / "inputs.jsonl").write_text(
            json.dumps(self.case(case_id="final", split="final"), ensure_ascii=False),
            encoding="utf-8",
        )
        started, release = threading.Event(), threading.Event()
        self.deps.model = GateModel(self.brand, started, release)

        status, _ = self.call("POST", "/api/batch", {"split": "tuning"})
        self.assertEqual(status, 202)
        self.assertTrue(started.wait(1))
        self.assertEqual(self.call("POST", "/api/batch", {"split": "tuning"})[0], 409)
        self.assertEqual(self.call("POST", "/api/batch/stop", {})[0], 200)
        release.set()

        state = self.deps.batch_state
        self.assertTrue(state.finished.wait(2))
        status, payload = self.call("GET", "/api/batch")
        self.assertEqual(status, 200)
        by_id = {row["case_id"]: row["status"] for row in payload["rows"]}
        self.assertEqual(by_id["c4"], "cancelled")
        self.assertIn(by_id["c0"], ("done", "failed_checks"))
        run_dir = next((self.root / "runs").glob("*/*"))
        cancelled = json.loads((run_dir / "cases" / "c4.json").read_text(encoding="utf-8"))
        self.assertEqual(cancelled["status"], "cancelled")

    def test_batch_reports_thread_failure_and_marks_unfinished_rows(self):
        row = self.case(case_id="c1", split="tuning")
        (self.root / "cases" / "tuning.jsonl").write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")

        def fail(*args):
            raise OSError("manifest broke")

        self.deps.run_cases = fail
        status, _ = self.call("POST", "/api/batch", {"split": "tuning"})
        self.assertEqual(status, 202)
        self.assertTrue(self.deps.batch_state.finished.wait(2))
        status, payload = self.call("GET", "/api/batch")
        self.assertEqual(status, 200)
        self.assertEqual(payload["error"], "manifest broke")
        self.assertEqual(payload["rows"], [{"case_id": "c1", "status": "failed"}])
        manifest = next((self.root / "runs").glob("*/*/manifest.end.json"))
        self.assertEqual(json.loads(manifest.read_text(encoding="utf-8"))["case_statuses"], {"c1": "failed"})

    def stored_run(self, version, client_hash, test_version):
        store = RunStore(self.root / "runs", version)
        run_id = store.begin(
            {
                "writer_model": "测试",
                "client_store_hash": client_hash,
                "test_set_version": test_version,
                "case_ids": ["c1"],
                "split": "final",
            }
        )
        store.write_case(
            run_id,
            "c1",
            {
                "case": self.case(case_id="c1"),
                "resolved": {},
                "steps": [{"name": "write", "prompt": "提示", "raw": "原始"}],
                "candidates": [],
                "checks": [{"name": "count", "passed": True, "reason": "", "indexes": []}],
                "status": "done",
            },
        )
        store.append(run_id, "scores.jsonl", {"case_id": "c1", "item": "事实", "value": "pass"})
        store.finish_manifest(run_id, {"case_statuses": {"c1": "done"}, "end": "现在"})
        return run_id


class GateModel:
    model_name = "闸门模型"

    def __init__(self, brand, started, release):
        self.brand = brand
        self.started = started
        self.release = release
        self.lock = threading.Lock()
        self.count = 0

    def complete(self, system, user):
        if '"picks"' in system:
            with self.lock:
                self.count += 1
                if self.count == 2:
                    self.started.set()
            self.release.wait(2)
            return plan_reply(self.brand)
        return write_reply(self.brand)


if __name__ == "__main__":
    unittest.main()
