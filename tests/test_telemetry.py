import contextlib
import io
import unittest
from unittest.mock import patch

import ca.telemetry as telemetry
from ca.telemetry import Telemetry, open_telemetry
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
