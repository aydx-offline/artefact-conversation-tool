import contextlib
import io
import unittest
from unittest.mock import patch

import ca.telemetry as telemetry
from ca.brand import load_brand
from ca.telemetry import Telemetry, open_telemetry, publish_prompts
from ca.version import GENERATOR_VERSION


class FakeClient:
    def __init__(self):
        self.traces = []
        self.scores = []
        self.datasets = []
        self.runs = []
        self.flushed = 0

        self.items = []

    def start_observation(self, *, name, input=None):
        self.traces.append({"name": name, "input": input})
        return "trace"

    def create_score(self, *, name, value, trace_id=None):
        self.scores.append({"name": name, "value": value, "trace_id": trace_id})

    def create_dataset(self, *, name):
        self.datasets.append({"name": name})

    def create_dataset_item(self, *, dataset_name, input=None):
        item = {"dataset_name": dataset_name, "input": input}
        self.items.append(item)
        return item

    def run_experiment(self, *, name, run_name, data, task):
        call = {"name": name, "run_name": run_name, "data": data, "task": task}
        self.runs.append(call)
        return "run"

    def flush(self):
        self.flushed += 1


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        telemetry._off_printed = False

    def test_disabled_telemetry_is_a_noop(self):
        item = Telemetry(None)
        self.assertIsNone(item.trace_case("c1", input={"客户": "林女士"}))
        item.score(name="事实", value=1)
        item.dataset_run("tuning", "r1", {"case_id": "c1"}, lambda row: row)
        item.flush()

    def test_missing_keys_prints_once_and_disables_telemetry(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            first = open_telemetry({})
            second = open_telemetry({})
        self.assertIsNone(first.client)
        self.assertIsNone(second.client)
        self.assertEqual(output.getvalue(), "Langfuse off\n")

    def test_one_missing_key_disables_telemetry(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            item = open_telemetry({"LANGFUSE_PUBLIC_KEY": "public"})
        self.assertIsNone(item.client)
        self.assertEqual(output.getvalue(), "Langfuse off\n")

    def test_import_error_prints_once_and_disables_telemetry(self):
        env = {"LANGFUSE_PUBLIC_KEY": "public", "LANGFUSE_SECRET_KEY": "secret"}
        output = io.StringIO()
        real_import = __import__

        def fail_langfuse(name, *args, **kwargs):
            if name == "langfuse":
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fail_langfuse):
            with contextlib.redirect_stdout(output):
                first = open_telemetry(env)
                second = open_telemetry(env)
        self.assertIsNone(first.client)
        self.assertIsNone(second.client)
        self.assertEqual(output.getvalue(), "Langfuse off\n")

    def test_fake_client_receives_trace_score_dataset_run_and_flush(self):
        client = FakeClient()
        item = Telemetry(client)
        task = lambda row: row

        self.assertEqual(item.trace_case("c1", input={"客户": "林女士"}), "trace")
        item.score(name="事实", value=1, trace_id="trace-1")
        self.assertEqual(
            item.dataset_run("final", "r1", {"case_id": "c1"}, task),
            "run",
        )
        item.flush()

        self.assertEqual(client.traces, [{"name": "c1", "input": {"客户": "林女士"}}])
        self.assertEqual(client.scores, [{"name": "事实", "value": 1, "trace_id": "trace-1"}])
        self.assertEqual(client.datasets, [{"name": "final"}])
        self.assertEqual(client.items, [{"dataset_name": "final", "input": {"case_id": "c1"}}])
        self.assertEqual(client.runs, [{
            "name": "final",
            "run_name": f"{GENERATOR_VERSION}:r1",
            "data": [client.items[0]],
            "task": task,
        }])
        self.assertEqual(client.flushed, 1)

    def test_record_case_ends_the_observation_with_output(self):
        class Observation:
            def __init__(self):
                self.output = None
                self.ended = False

            def update(self, *, output):
                self.output = output

            def end(self):
                self.ended = True

        client = FakeClient()
        observation = Observation()
        client.start_observation = lambda *, name, input=None: observation
        item = Telemetry(client)
        self.assertIs(item.record_case("t04", {"case_id": "t04"}, {"status": "done"}), observation)
        self.assertEqual(observation.output, {"status": "done"})
        self.assertTrue(observation.ended)
        self.assertIsNone(Telemetry(None).record_case("t04", {}, {}))

    def test_record_case_file_sends_profile_prompt_plan_checks_scores_cost_and_latency(self):
        class Observation:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.trace_id = "trace-1"
                self.id = "span-1"
                self.ended = False

            def end(self):
                self.ended = True

        class Client:
            def __init__(self):
                self.observations = []
                self.scores = []

            def start_observation(self, **kwargs):
                observation = Observation(**kwargs)
                self.observations.append(observation)
                return observation

            def create_score(self, **kwargs):
                self.scores.append(kwargs)

        client = Client()
        case_file = {
            "case": {"case_id": "t04", "scenario": "2 Product recommendation"},
            "resolved": {
                "client": {"name": "林女士"},
                "occasion": None,
                "tone": "亲切温暖",
                "length": "简短",
                "products": [{"id": "scarf"}],
                "event": None,
                "history": [{"role": "顾客", "text": "你好"}],
                "expectations": [],
            },
            "status": "done",
            "candidates": [
                {"strategy": "从她已经有的一件东西说起", "reason": "她买过围巾", "tone": "亲切温暖", "length": "简短", "text": "林女士，围巾还合用吗？"}
            ],
            "steps": [
                {
                    "name": "plan",
                    "prompt": "请选三个策略",
                    "raw": '{"picks":[]}',
                    "usage": {"input": 10, "output": 4, "total": 14, "total_cost": 0.2},
                    "latency_ms": 1200,
                },
                {"name": "write", "prompt": "请写三条", "raw": "三条", "usage": {"input": 8, "output": 6, "total": 14}, "latency_ms": 800},
            ],
            "checks": [{"name": "count", "passed": True, "reason": ""}],
        }
        scores = [{"candidate": 0, "item": "中文", "value": 5, "reason": "自然", "judge_model": "GLM-5.3"}]
        judge_call = {"prompt": "请评分", "raw": '{"scores":[]}', "usage": {"input": 3, "output": 2, "total": 5}, "latency_ms": 400}
        Telemetry(client).record_case_file(case_file, "run-1", scores=scores, writer_model="glm-5.3-flash", judge_call=judge_call)

        root = client.observations[0]
        self.assertEqual(root.kwargs["input"]["client"]["name"], "林女士")
        self.assertEqual(root.kwargs["output"]["plan"][0]["strategy"], "从她已经有的一件东西说起")
        self.assertEqual(root.kwargs["output"]["texts"], ["林女士，围巾还合用吗？"])
        self.assertEqual(root.kwargs["metadata"]["latency_ms"], 2400)
        names = [item.kwargs["name"] for item in client.observations]
        self.assertEqual(names, ["t04", "plan", "write", "judge"])
        plan = client.observations[1].kwargs
        self.assertEqual(plan["input"], "请选三个策略")
        self.assertEqual(plan["output"], '{"picks":[]}')
        self.assertEqual(plan["usage_details"], {"input": 10, "output": 4, "total": 14})
        self.assertEqual(plan["cost_details"], {"total": 0.2})
        self.assertEqual(plan["metadata"]["latency_ms"], 1200)
        self.assertEqual(client.scores[0]["name"], "check:count")
        self.assertEqual(client.scores[1]["name"], "中文")
        self.assertEqual(client.scores[1]["metadata"]["candidate"], 0)
        self.assertEqual(client.scores[1]["value"], 5.0)
        self.assertEqual(client.scores[1]["trace_id"], "trace-1")
        self.assertTrue(root.ended)
        self.assertIsNone(Telemetry(None).record_case_file({}, "run-1"))

    def test_publish_prompts_creates_a_version_only_when_the_text_changes(self):
        class Stored:
            def __init__(self, prompt):
                self.prompt = prompt

        class Client:
            def __init__(self):
                self.created = []
                self.stored = {}

            def get_prompt(self, name, label="production"):
                if name not in self.stored:
                    raise KeyError(name)
                return self.stored[name]

            def create_prompt(self, **kwargs):
                self.created.append(kwargs["name"])
                self.stored[kwargs["name"]] = Stored(kwargs["prompt"])

        brand = load_brand(__import__("pathlib").Path(__file__).resolve().parent.parent / "data" / "brand")
        client = Client()
        first = publish_prompts(client, brand)
        second = publish_prompts(client, brand)
        self.assertEqual(first, ["ca/draft", "ca/revise", "ca/judge", "ca/chat"])
        self.assertEqual(second, [])
        self.assertEqual(client.created, first)
        self.assertEqual(publish_prompts(None, brand), [])

    def test_noop_dataset_name_must_be_tuning_or_final(self):
        with self.assertRaises(ValueError):
            Telemetry().dataset_run("other", "r1", {}, lambda row: row)

    def test_open_telemetry_constructs_client_only_with_both_keys(self):
        made = object()
        env = {
            "LANGFUSE_PUBLIC_KEY": "public",
            "LANGFUSE_SECRET_KEY": "secret",
            "LANGFUSE_HOST": "https://langfuse.example",
        }
        with patch.object(telemetry, "_langfuse_client", return_value=made) as factory:
            item = open_telemetry(env)
        self.assertIs(item.client, made)
        factory.assert_called_once_with(env)


if __name__ == "__main__":
    unittest.main()
