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

    def resolve(self, timestamp, client=None, occasion=""):
        return resolve_context(timestamp, client or self.lin, self.festivals, occasion)

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

    def test_today_birthday_and_last_message(self):
        ctx = resolve_context("2026-08-17T10:00:00+08:00", self.lin, self.festivals, "", "2026-08-17T09:00:00+08:00")
        self.assertEqual((ctx.today, ctx.days_to_birthday, ctx.days_since_message), ("2026-08-17", 210, 0))
        ctx = self.resolve("2026-03-15T10:00:00+08:00")
        self.assertEqual((ctx.days_to_birthday, ctx.days_since_message), (0, None))
        self.assertEqual(self.resolve("2026-03-16T10:00:00+08:00").days_to_birthday, 364)

    def test_nearest_festivals(self):
        ctx = self.resolve("2026-02-12T10:00:00+08:00")
        self.assertEqual((ctx.next_festival, ctx.last_festival), (("春节", 5), ("元旦", 42)))

    def test_context_fields(self):
        self.assertEqual(
            list(Context.__dataclass_fields__),
            ["occasion", "festival", "birthday", "days_since_purchase", "months_since_visit", "today", "days_to_birthday", "days_since_message", "next_festival", "last_festival"],
        )


if __name__ == "__main__":
    unittest.main()
