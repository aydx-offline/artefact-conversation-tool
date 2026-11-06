import unittest
from pathlib import Path

from ca.brand import load_brand
from ca.clients import load_clients
from ca.context import Context, resolve_context

ROOT = Path(__file__).resolve().parent.parent / "data"


class ContextTest(unittest.TestCase):
    def setUp(self):
        self.festivals = load_brand(ROOT / "brand").festivals
        self.lin = load_clients(ROOT / "clients.json")["lin"]

    def resolve(self, timestamp, client=None, occasion="", greeting=False):
        return resolve_context(timestamp, client or self.lin, self.festivals, occasion, greeting=greeting)

    def test_festival_window(self):
        for day in ("25", "22"):
            ctx = self.resolve(f"2026-09-{day}T10:00:00+08:00")
            self.assertEqual((ctx.occasion, ctx.festival, ctx.birthday), ("中秋", "中秋", False))

    def test_outside_window(self):
        ctx = self.resolve("2026-09-21T10:00:00+08:00")
        self.assertEqual((ctx.occasion, ctx.festival, ctx.birthday), ("", None, False))

    def test_birthday(self):
        ctx = self.resolve("2026-03-15T10:00:00+08:00")
        self.assertEqual((ctx.occasion, ctx.festival, ctx.birthday), ("生日", None, True))

    def test_birthday_and_festival(self):
        client = {**self.lin, "birthday": "09-24"}
        ctx = self.resolve("2026-09-22T10:00:00+08:00", client)
        self.assertEqual((ctx.occasion, ctx.festival, ctx.birthday), ("生日和中秋", "中秋", True))

    def test_birthday_across_new_year(self):
        client = {**self.lin, "birthday": "01-01"}
        self.assertTrue(self.resolve("2026-12-30T10:00:00+08:00", client).birthday)

    def test_explicit_occasion_wins(self):
        client = {**self.lin, "birthday": "09-24"}
        ctx = self.resolve("2026-09-22T10:00:00+08:00", client, "新品上市")
        self.assertEqual(ctx.occasion, "新品上市")
        self.assertEqual((ctx.festival, ctx.birthday), ("中秋", True))

    def test_days_since_purchase(self):
        self.assertEqual(self.resolve("2026-03-12T10:00:00+08:00").days_since_purchase, 10)
        self.assertIsNone(self.resolve("2026-03-12T10:00:00+08:00", {**self.lin, "purchases": []}).days_since_purchase)

    def test_latest_purchase_used(self):
        client = {**self.lin, "purchases": [{"product_id": "a", "date": "2026-01-01"}, {"product_id": "b", "date": "2026-03-02"}]}
        self.assertEqual(self.resolve("2026-03-12T10:00:00+08:00", client).days_since_purchase, 10)

    def test_months_since_visit(self):
        self.assertEqual(self.resolve("2026-09-25T10:00:00+08:00").months_since_visit, 6)
        self.assertIsNone(self.resolve("2026-09-25T10:00:00+08:00", {**self.lin, "last_visit": None}).months_since_visit)

    def test_naive_timestamp_is_shanghai(self):
        ctx = self.resolve("2026-09-25T10:00:00")
        self.assertEqual(ctx.festival, "中秋")

    def test_offset_converted_to_shanghai(self):
        ctx = self.resolve("2026-09-24T20:00:00-05:00")
        self.assertEqual(ctx.festival, "中秋")
        self.assertEqual(self.resolve("2026-03-14T20:00:00-05:00").birthday, True)

    def test_today_and_last_message(self):
        ctx = resolve_context("2026-08-17T10:00:00+08:00", self.lin, self.festivals, "", "2026-08-17T09:00:00+08:00")
        self.assertEqual((ctx.today, ctx.days_since_message), ("2026-08-17", 0))
        self.assertIsNone(self.resolve("2026-03-15T10:00:00+08:00").days_since_message)

    def test_birthday_window_and_note(self):
        # Lin's birthday is 03-15: seven days ahead, the day itself, and two days after count.
        cases = {
            "2026-03-07": (False, "不要提生日"),
            "2026-03-08": (True, "还有7天，要提前送上生日祝福"),
            "2026-03-15": (True, "今天是她的生日，要写生日快乐"),
            "2026-03-16": (True, "刚过1天，要补一句生日快乐"),
            "2026-03-17": (True, "刚过2天，要补一句生日快乐"),
            "2026-03-18": (False, "不要提生日"),
        }
        for day, (inside, words) in cases.items():
            ctx = self.resolve(f"{day}T10:00:00+08:00", occasion="", greeting=True)
            self.assertEqual(ctx.birthday, inside, day)
            self.assertIn(words, ctx.birthday_note, day)
            self.assertEqual(ctx.occasion, "生日" if inside else "", day)

    def test_birthday_note_is_a_suggestion_outside_the_greeting_scenario(self):
        ctx = self.resolve("2026-03-10T10:00:00+08:00")
        self.assertIn("还有5天，可以顺带提前送上生日祝福", ctx.birthday_note)
        self.assertEqual(self.resolve("2026-03-15T10:00:00+08:00").birthday_note, "今天是她的生日，可以顺带写生日快乐")

    def test_a_leap_day_birthday_works_in_a_common_year(self):
        client = {**self.lin, "birthday": "02-29"}
        self.assertEqual(self.resolve("2026-02-28T10:00:00+08:00", client).birthday_note, "今天是她的生日，可以顺带写生日快乐")
        self.assertIn("刚过1天", self.resolve("2026-03-01T10:00:00+08:00", client).birthday_note)

    def test_no_birthday_no_note(self):
        self.assertIsNone(self.resolve("2026-03-15T10:00:00+08:00", {**self.lin, "birthday": ""}).birthday_note)

    def test_age_words(self):
        from ca.context import age_words

        cases = {"2026-11-01": "5天前", "2026-09-06": "2个月前", "2026-03-06": "8个月前", "2025-11-06": "一年前", "2025-05-12": "一年多前", "2024-08-01": "两年多前"}
        for start, words in cases.items():
            self.assertEqual(age_words(start, "2026-11-06"), words, start)

    def test_nearest_festivals(self):
        ctx = self.resolve("2026-02-12T10:00:00+08:00")
        self.assertEqual((ctx.next_festival, ctx.last_festival), (("春节", 5), ("元旦", 42)))

    def test_context_fields(self):
        self.assertEqual(
            list(Context.__dataclass_fields__),
            ["occasion", "festival", "birthday", "days_since_purchase", "months_since_visit", "today", "birthday_note", "days_since_message", "next_festival", "last_festival"],
        )


if __name__ == "__main__":
    unittest.main()
