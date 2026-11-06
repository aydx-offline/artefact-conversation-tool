import json
import re
import unittest
from collections import Counter
from datetime import date
from pathlib import Path

from ca.checks import has_offer
from ca.context import resolve_context
from ca.schema import PRICE_MARKERS, SCENARIOS, load_case, prose_is_chinese, validate_case
from ca.store import test_set_version
from tests.test_coverage import COLUMNS, FINAL_COUNTS, read_table

ROOT = Path(__file__).resolve().parents[1]
FILES = {"final": ROOT / "cases/inputs.jsonl", "tuning": ROOT / "cases/tuning.jsonl"}


def load_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class CaseFilesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {split: load_rows(path) for split, path in FILES.items()}
        cls.coverage = {
            split: [dict(zip(COLUMNS, row)) for row in read_table(split)[1]]
            for split in FILES
        }
        cls.clients = json.loads((ROOT / "data/clients.json").read_text(encoding="utf-8"))
        catalog = json.loads((ROOT / "data/brand/catalog.json").read_text(encoding="utf-8"))
        cls.catalog = {item["id"] for item in catalog}
        cls.product_terms = {
            term
            for item in catalog
            for term in (item["name"], item["line"])
        } | {"大衣", "围巾", "耳钉", "长裙"}
        cls.events = set(json.loads((ROOT / "data/brand/events.json").read_text(encoding="utf-8")))
        cls.festivals = json.loads((ROOT / "data/brand/festivals.json").read_text(encoding="utf-8"))
        cls.rules = json.loads((ROOT / "data/brand/rules.json").read_text(encoding="utf-8"))
        cls.allowed = tuple(cls.rules["allowed_english"])

    def test_rows_match_coverage(self):
        self.assertEqual({split: len(rows) for split, rows in self.rows.items()}, {"final": 50, "tuning": 20})
        all_ids = []
        for split, rows in self.rows.items():
            expected = {row["id"]: row for row in self.coverage[split]}
            self.assertEqual([row["case_id"] for row in rows], list(expected))
            for row in rows:
                coverage = expected[row["case_id"]]
                self.assertEqual(row["split"], split)
                self.assertEqual(row["scenario"], coverage["scenario"])
                self.assertEqual(row["timestamp"], coverage["timestamp"])
                self.assertEqual(row["product_ids"], [] if coverage["product"] == "—" else [coverage["product"]])
                self.assertEqual(row.get("event_id", ""), "" if coverage["event"] == "—" else coverage["event"])
                size = len(row["history"])
                self.assertTrue(
                    size == 0 if coverage["history"] == "none"
                    else 2 <= size <= 4 if coverage["history"] == "short"
                    else 8 <= size <= 12
                )
                client = self.clients[row["client_id"]]
                self.assertEqual((client["tier"], client["relationship"]), (coverage["tier"], coverage["relationship"]))
                all_ids.append(row["case_id"])
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_references_schema_and_required_fields(self):
        for rows in self.rows.values():
            for row in rows:
                self.assertIn(row["client_id"], self.clients)
                self.assertTrue(set(row["product_ids"]) <= self.catalog)
                self.assertFalse(row.get("event_id") and row["event_id"] not in self.events)
                if row["scenario"] == "2 Product recommendation" or row["scenario"].startswith("6"):
                    self.assertTrue(row["product_ids"])
                if row["scenario"] == "5 Event invitation":
                    self.assertIn(row.get("event_id"), self.events)
                if row["scenario"].startswith("6"):
                    markers = PRICE_MARKERS[row["scenario"]]
                    self.assertTrue(any(
                        message["sender"] == "client" and any(marker in message["text"] for marker in markers)
                        for message in row["history"]
                    ))
                validate_case(load_case(row), allowed_names=self.allowed)

    def test_chinese_prose_and_no_reused_history(self):
        final_text = {message["text"] for row in self.rows["final"] for message in row["history"]}
        tuning_text = {message["text"] for row in self.rows["tuning"] for message in row["history"]}
        self.assertFalse(final_text & tuning_text)
        for rows in self.rows.values():
            for row in rows:
                for message in row["history"]:
                    self.assertTrue(prose_is_chinese(message["text"], self.allowed))
                for value in row.get("expectations", {}).values():
                    self.assertTrue(prose_is_chinese(value, self.allowed))
        for client in self.clients.values():
            for field in ("name", "tier", "relationship", "preferences", "notes"):
                self.assertTrue(prose_is_chinese(client.get(field, ""), self.allowed))
            for message in client.get("history", []):
                self.assertTrue(prose_is_chinese(message["text"], self.allowed))

    def test_counts_and_scenario_one_context(self):
        self.assertEqual(Counter(row["scenario"] for row in self.rows["final"]), FINAL_COUNTS)
        tuning = Counter(row["scenario"] for row in self.rows["tuning"])
        self.assertTrue(all(tuning[scenario] >= 2 for scenario in SCENARIOS))
        for split, rows in self.rows.items():
            notes = {row["id"]: row["note"] for row in self.coverage[split]}
            for row in rows:
                if row["scenario"] != "1 Birthday and festive greetings":
                    continue
                context = resolve_context(row["timestamp"], self.clients[row["client_id"]], self.festivals, row.get("occasion", ""))
                note = notes[row["case_id"]]
                if note.startswith("both"):
                    expected = "生日和" + note.rsplit("与", 1)[1]
                else:
                    expected = "生日" if note.startswith("birthday") else note.split("；")[0]
                self.assertEqual(context.occasion, expected, row["case_id"])
        final = {row["case_id"]: row for row in self.rows["final"]}
        self.assertEqual(final["f14"]["occasion"], "七夕")
        self.assertEqual(final["f21"]["occasion"], "中秋")

    def test_gesture_cases_state_the_one_off_rule(self):
        final = {row["case_id"]: row for row in self.rows["final"]}
        for case_id in ("f18", "f37", "f46", "f47", "f48", "f49", "f50"):
            must_not = final[case_id]["expectations"]["must_not"]
            self.assertIn("终身", must_not, case_id)
        for case_id in ("f46", "f47", "f48", "f49", "f50"):
            self.assertIn("降价", final[case_id]["expectations"]["must_not"], case_id)
            self.assertIn("一次", final[case_id]["expectations"]["must"], case_id)

    def test_only_f21_is_inside_a_birthday_window_outside_scenario_1(self):
        for rows in self.rows.values():
            for row in rows:
                if row["scenario"] == "1 Birthday and festive greetings":
                    continue
                context = resolve_context(
                    row["timestamp"],
                    self.clients[row["client_id"]],
                    self.festivals,
                    "",
                )
                self.assertEqual(context.birthday, row["case_id"] == "f21", row["case_id"])

    def test_owned_products_reactivation_age_and_safe_ca_messages(self):
        coverage = {
            row["id"]: row for rows in self.coverage.values() for row in rows
        }
        for rows in self.rows.values():
            for row in rows:
                client = self.clients[row["client_id"]]
                owned = {purchase["product_id"] for purchase in client["purchases"]}
                if row["scenario"] == "2 Product recommendation":
                    self.assertNotIn(row["product_ids"][0], owned, row["case_id"])
                if row["scenario"] == "3 Post-purchase care":
                    self.assertIn(row["product_ids"][0], owned, row["case_id"])
                if row["scenario"] == "4 Reactivation":
                    context = resolve_context(row["timestamp"], client, self.festivals, "")
                    self.assertGreaterEqual(context.months_since_visit, 4, coverage[row["case_id"]]["note"])
                for message in row["history"]:
                    if message["sender"] == "ca":
                        self.assertFalse(has_offer(message["text"], self.rules["offer_patterns"]))

    def test_client_purchase_timeline_is_consistent(self):
        for client_id, client in self.clients.items():
            last_visit = date.fromisoformat(client["last_visit"])
            for purchase in client["purchases"]:
                self.assertGreaterEqual(last_visit, date.fromisoformat(purchase["date"]), client_id)

    def test_used_clients_have_no_purchase_after_case_timestamp(self):
        earliest_case = {}
        for rows in self.rows.values():
            for row in rows:
                day = date.fromisoformat(row["timestamp"][:10])
                earliest_case[row["client_id"]] = min(day, earliest_case.get(row["client_id"], day))
        for client_id, case_day in earliest_case.items():
            for purchase in self.clients[client_id]["purchases"]:
                self.assertLessEqual(date.fromisoformat(purchase["date"]), case_day, client_id)

    def test_histories_alternate_senders(self):
        for rows in self.rows.values():
            for row in rows:
                self.assertFalse(any(
                    left["sender"] == right["sender"]
                    for left, right in zip(row["history"], row["history"][1:])
                ), row["case_id"])

    def test_client_reuse_is_bounded_and_spaced(self):
        self.assertLessEqual(24, len(self.clients))
        self.assertLessEqual(len(self.clients), 30)
        uses = {}
        for rows in self.rows.values():
            for row in rows:
                uses.setdefault(row["client_id"], []).append(
                    (row["case_id"], date.fromisoformat(row["timestamp"][:10]))
                )
        for client_id, cases in uses.items():
            self.assertLessEqual(len(cases), 3, (client_id, cases))
            days = sorted(day for _, day in cases)
            for previous, current in zip(days, days[1:]):
                self.assertGreaterEqual((current - previous).days, 14, (client_id, cases))

    def test_history_repetition_is_bounded(self):
        rows = [row for split in self.rows.values() for row in split]
        exact = {
            row["case_id"]: {message["text"] for message in row["history"]}
            for row in rows
        }
        exact_counts = Counter(text for lines in exact.values() for text in lines)
        self.assertFalse({text: count for text, count in exact_counts.items() if count > 3})

        def normalise(row, text):
            client = self.clients[row["client_id"]]
            for term in sorted(
                self.product_terms | {client["name"], client["address"]},
                key=len,
                reverse=True,
            ):
                text = text.replace(term, "")
            return re.sub(r"[\W\d_]+", "", text, flags=re.UNICODE).lower()

        cases = {
            row["case_id"]: {
                normalise(row, message["text"]) for message in row["history"]
            }
            for row in rows
        }
        counts = Counter(text for lines in cases.values() for text in lines)
        self.assertFalse({text: count for text, count in counts.items() if count > 1})
        ids = list(cases)
        for index, left in enumerate(ids):
            for right in ids[index + 1:]:
                self.assertLessEqual(len(cases[left] & cases[right]), 1, f"{left}, {right}")

    def test_frozen_version(self):
        used = sorted({row["client_id"] for rows in self.rows.values() for row in rows})
        actual = test_set_version(FILES["final"], FILES["tuning"], [self.clients[key] for key in used])
        text = (ROOT / "docs/coverage.md").read_text(encoding="utf-8")
        match = re.search(r"^## Frozen\s*\n\n`([0-9a-f]{64})`$", text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), actual)


if __name__ == "__main__":
    unittest.main()
