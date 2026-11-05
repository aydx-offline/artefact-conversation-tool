import json
import re
import unittest
from collections import Counter
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
        cls.catalog = {
            item["id"]
            for item in json.loads((ROOT / "data/brand/catalog.json").read_text(encoding="utf-8"))
        }
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

    def test_owned_products_reactivation_age_and_safe_ca_messages(self):
        coverage = {
            row["id"]: row for rows in self.coverage.values() for row in rows
        }
        for rows in self.rows.values():
            for row in rows:
                client = self.clients[row["client_id"]]
                if row["scenario"] == "3 Post-purchase care":
                    self.assertIn(row["product_ids"][0], {purchase["product_id"] for purchase in client["purchases"]})
                if row["scenario"] == "4 Reactivation":
                    context = resolve_context(row["timestamp"], client, self.festivals, "")
                    self.assertGreaterEqual(context.months_since_visit, 4, coverage[row["case_id"]]["note"])
                for message in row["history"]:
                    if message["sender"] == "ca":
                        self.assertFalse(has_offer(message["text"], self.rules["offer_patterns"]))

    def test_frozen_version(self):
        used = sorted({row["client_id"] for rows in self.rows.values() for row in rows})
        actual = test_set_version(FILES["final"], FILES["tuning"], [self.clients[key] for key in used])
        text = (ROOT / "docs/coverage.md").read_text(encoding="utf-8")
        match = re.search(r"^## Frozen\s*\n\n`([0-9a-f]{64})`$", text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), actual)


if __name__ == "__main__":
    unittest.main()
