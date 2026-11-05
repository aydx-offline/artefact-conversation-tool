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

    def trace(self, *args, **kwargs):
        self.traces.append((args, kwargs))
        return "trace"

    def score(self, *args, **kwargs):
        self.scores.append((args, kwargs))

    def create_dataset(self, **kwargs):
        self.datasets.append(kwargs)

    def create_dataset_run(self, **kwargs):
        self.runs.append(kwargs)

    def flush(self):
        self.flushed += 1


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        telemetry._off_printed = False

    def test_disabled_telemetry_is_a_noop(self):
        item = Telemetry(None)
        self.assertIsNone(item.trace_case("c1", input={"客户": "林女士"}))
        item.score(name="事实", value=1)
        item.dataset_run("tuning", "r1")
        item.flush()

    def test_missing_keys_prints_once_and_disables_telemetry(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            first = open_telemetry({})
            second = open_telemetry({})
        self.assertIsNone(first.client)
        self.assertIsNone(second.client)
        self.assertEqual(output.getvalue(), "Langfuse off\n")

    def test_fake_client_receives_trace_score_dataset_run_and_flush(self):
        client = FakeClient()
        item = Telemetry(client)

        self.assertEqual(item.trace_case("c1", input={"客户": "林女士"}), "trace")
        item.score(name="事实", value=1)
        item.dataset_run("final", "r1")
        item.flush()

        self.assertEqual(len(client.traces), 1)
        self.assertEqual(len(client.scores), 1)
        self.assertEqual(client.datasets, [{"name": "final"}])
        self.assertEqual(client.runs, [{"dataset_name": "final", "name": f"{GENERATOR_VERSION}:r1"}])
        self.assertEqual(client.flushed, 1)

    def test_dataset_name_must_be_tuning_or_final(self):
        with self.assertRaises(ValueError):
            Telemetry(FakeClient()).dataset_run("other", "r1")

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
