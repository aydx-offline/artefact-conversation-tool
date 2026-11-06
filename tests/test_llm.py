import io
import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from ca.cli import _models
from ca.llm import (
    FakeModel,
    GlmModel,
    build_body,
    complete_with_retries,
    parse_reply,
    parse_usage,
    require_models,
)

KEY = "sk-secret-123"
ENV = {"GLM_API_KEY": KEY, "WRITER_MODEL": "w", "JUDGE_MODEL": "j"}


class FlakyModel:
    def __init__(self, replies):
        self.replies = list(replies)

    def complete(self, system, user):
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class FakeModelTests(unittest.TestCase):
    def test_returns_in_order_and_records_calls(self):
        model = FakeModel(["a", "b"])
        self.assertEqual(model.complete("s1", "u1"), "a")
        self.assertEqual(model.complete("s2", "u2"), "b")
        self.assertEqual(model.calls, [("s1", "u1"), ("s2", "u2")])

    def test_exception_items_are_raised(self):
        model = FakeModel([ValueError("boom"), "ok"])
        with self.assertRaises(ValueError):
            model.complete("s", "u")
        self.assertEqual(model.complete("s", "u"), "ok")

    def test_exhausted_script_raises_clear_error(self):
        with self.assertRaisesRegex(RuntimeError, "script"):
            FakeModel([]).complete("s", "u")


class RetryTests(unittest.TestCase):
    def test_two_failures_then_success(self):
        sleeps = []
        model = FlakyModel([OSError("1"), OSError("2"), "ok"])
        self.assertEqual(complete_with_retries(model, "s", "u", sleeps.append), "ok")
        self.assertEqual(sleeps, [2, 8])

    def test_three_failures_raise_last_error(self):
        sleeps = []
        model = FlakyModel([OSError("1"), OSError("2"), OSError("3")])
        with self.assertRaisesRegex(OSError, "3"):
            complete_with_retries(model, "s", "u", sleeps.append)
        self.assertEqual(sleeps, [2, 8])

    def test_first_success_does_not_sleep(self):
        sleeps = []
        self.assertEqual(complete_with_retries(FlakyModel(["ok"]), "s", "u", sleeps.append), "ok")
        self.assertEqual(sleeps, [])


class RequireModelsTests(unittest.TestCase):
    def test_returns_names(self):
        self.assertEqual(require_models(ENV), ("w", "j"))

    def test_missing_or_empty_values_exit(self):
        for name in ENV:
            for bad in ({k: v for k, v in ENV.items() if k != name}, {**ENV, name: ""}):
                with self.assertRaises(SystemExit, msg=name):
                    require_models(bad)

    def test_equal_names_exit(self):
        with self.assertRaises(SystemExit):
            require_models({**ENV, "JUDGE_MODEL": "w"})

    def test_exit_message_is_english_and_hides_key(self):
        for env in ({**ENV, "WRITER_MODEL": ""}, {**ENV, "JUDGE_MODEL": "w"}):
            with self.assertRaises(SystemExit) as ctx:
                require_models(env)
            message = str(ctx.exception)
            self.assertNotIn(KEY, message)
            self.assertTrue(message.isascii())


class GlmTests(unittest.TestCase):
    def test_body_shape(self):
        self.assertEqual(
            build_body("m", "sys", "usr"),
            {
                "model": "m",
                "messages": [
                    {"role": "system", "content": "sys"},
                    {"role": "user", "content": "usr"},
                ],
            },
        )

    def test_thinking_disabled_is_sent(self):
        body = build_body("m", "sys", "usr", thinking=False)
        self.assertEqual(body["thinking"], {"type": "disabled"})

    def test_complete_sends_disabled_thinking(self):
        model = GlmModel(KEY, "https://example.invalid/v1", "m", thinking=False)
        response = MagicMock()
        response.__enter__.return_value.read.return_value = (
            b'{"choices":[{"message":{"content":"ok"}}]}'
        )
        with patch("urllib.request.urlopen", return_value=response) as urlopen:
            model.complete("s", "u")
        sent = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(sent["thinking"], {"type": "disabled"})

    def test_writer_disables_thinking_and_judge_keeps_it(self):
        writer, judge = _models(ENV, None, None)
        self.assertIs(writer.thinking, False)
        self.assertIs(judge.thinking, True)
        self.assertEqual(build_body("m", "s", "u", thinking=True)["thinking"], {"type": "enabled"})

    def test_parse_reply(self):
        raw = '{"choices":[{"message":{"content":"你好"}}]}'
        self.assertEqual(parse_reply(raw), "你好")

    def test_parse_usage_reads_tokens_and_cost(self):
        payload = {
            "usage": {
                "prompt_tokens": 3,
                "completion_tokens": 5,
                "total_tokens": 8,
                "input_cost": 0.1,
                "output_cost": 0.2,
                "total_cost": 0.3,
            }
        }
        self.assertEqual(
            parse_usage(payload),
            {
                "input": 3,
                "output": 5,
                "total": 8,
                "input_cost": 0.1,
                "output_cost": 0.2,
                "total_cost": 0.3,
            },
        )

    def test_repr_and_str_hide_key(self):
        model = GlmModel(KEY, "https://example.invalid/v1", "m")
        self.assertNotIn(KEY, repr(model))
        self.assertNotIn(KEY, str(model))

    def test_timeout_is_configurable(self):
        model = GlmModel(KEY, "https://example.invalid/v1", "m", timeout=23)
        response = MagicMock()
        response.__enter__.return_value.read.return_value = (
            b'{"choices":[{"message":{"content":"ok"}}]}'
        )
        with patch("urllib.request.urlopen", return_value=response) as urlopen:
            self.assertEqual(model.complete("s", "u"), "ok")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 23)

    def test_complete_returns_usage_and_latency(self):
        model = GlmModel(KEY, "https://example.invalid/v1", "m")
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {
                "choices": [{"message": {"content": "你好"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3, "total_cost": 0.01},
            }
        ).encode()
        with patch("urllib.request.urlopen", return_value=response):
            reply = model.complete("s", "u")
        self.assertEqual(reply, "你好")
        self.assertEqual(reply.usage["input"], 2)
        self.assertEqual(reply.usage["total_cost"], 0.01)
        self.assertGreaterEqual(reply.latency_ms, 0)

    def test_http_error_includes_body_without_key(self):
        error = urllib.error.HTTPError(
            "https://example.invalid/v1",
            429,
            "limited",
            {},
            io.BytesIO("请求过多".encode()),
        )
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "GLM 429: 请求过多") as caught:
                GlmModel(KEY, "https://example.invalid/v1", "m").complete("s", "u")
        self.assertNotIn(KEY, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
