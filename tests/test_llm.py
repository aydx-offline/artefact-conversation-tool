import unittest

from ca.llm import (
    FakeModel,
    GlmModel,
    build_body,
    complete_with_retries,
    parse_reply,
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
        self.assertEqual(sleeps, [0.5, 1.0])

    def test_three_failures_raise_last_error(self):
        sleeps = []
        model = FlakyModel([OSError("1"), OSError("2"), OSError("3")])
        with self.assertRaisesRegex(OSError, "3"):
            complete_with_retries(model, "s", "u", sleeps.append)
        self.assertEqual(sleeps, [0.5, 1.0])

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

    def test_parse_reply(self):
        raw = '{"choices":[{"message":{"content":"你好"}}]}'
        self.assertEqual(parse_reply(raw), "你好")

    def test_repr_and_str_hide_key(self):
        model = GlmModel(KEY, "https://example.invalid/v1", "m")
        self.assertNotIn(KEY, repr(model))
        self.assertNotIn(KEY, str(model))


if __name__ == "__main__":
    unittest.main()
