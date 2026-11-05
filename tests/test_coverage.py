import json
import re
import unittest
from collections import Counter
from datetime import datetime
from pathlib import Path

from ca.schema import SCENARIOS

ROOT = Path(__file__).resolve().parent.parent
COVERAGE = ROOT / "docs" / "coverage.md"
COLUMNS = [
    "id",
    "scenario",
    "tier",
    "relationship",
    "history",
    "product",
    "event",
    "timestamp",
    "note",
]
FINAL_COUNTS = dict(zip(SCENARIOS, (7, 7, 7, 7, 7, 5, 5, 5)))


def read_table(section):
    text = COVERAGE.read_text(encoding="utf-8")
    match = re.search(
        rf"^## {section}\s*$\n(?P<table>(?:^\|.*\|\s*$\n?)+)",
        text,
        flags=re.MULTILINE,
    )
    if not match:
        raise AssertionError(f"missing {section} table")
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in match.group("table").splitlines()
        if line.strip().startswith("|")
    ]
    return rows[0], rows[2:]


class CoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.final_header, cls.final = read_table("final")
        cls.tuning_header, cls.tuning = read_table("tuning")
        cls.catalog_ids = {
            item["id"]
            for item in json.loads(
                (ROOT / "data" / "brand" / "catalog.json").read_text(encoding="utf-8")
            )
        }
        cls.event_ids = set(
            json.loads(
                (ROOT / "data" / "brand" / "events.json").read_text(encoding="utf-8")
            )
        )

    def test_columns_are_exact(self):
        self.assertEqual(self.final_header, COLUMNS)
        self.assertEqual(self.tuning_header, COLUMNS)
        self.assertTrue(all(len(row) == len(COLUMNS) for row in self.final + self.tuning))

    def test_ids_and_final_scenario_counts(self):
        final_ids = [row[0] for row in self.final]
        tuning_ids = [row[0] for row in self.tuning]
        self.assertEqual(set(final_ids), {f"f{i:02d}" for i in range(1, 51)})
        self.assertEqual(len(final_ids), len(set(final_ids)))
        self.assertEqual(set(tuning_ids), {f"t{i:02d}" for i in range(1, 21)})
        self.assertEqual(len(tuning_ids), len(set(tuning_ids)))
        self.assertFalse(set(final_ids) & set(tuning_ids))
        self.assertEqual(Counter(row[1] for row in self.final), FINAL_COUNTS)

    def test_final_price_rows_have_history_and_product(self):
        price_rows = [row for row in self.final if row[1].startswith("6 ")]
        self.assertTrue(price_rows)
        for row in price_rows:
            self.assertIn(row[4], {"short", "long"})
            self.assertIn(row[5], self.catalog_ids)

    def test_tuning_covers_each_scenario_twice(self):
        counts = Counter(row[1] for row in self.tuning)
        for scenario in SCENARIOS:
            self.assertGreaterEqual(counts[scenario], 2)

    def test_references_and_timestamps_are_valid(self):
        for row in self.final + self.tuning:
            scenario, product, event, timestamp = row[1], row[5], row[6], row[7]
            if product != "—":
                self.assertIn(product, self.catalog_ids)
            if scenario == "5 Event invitation":
                self.assertIn(event, self.event_ids)
            elif event != "—":
                self.fail(f"{row[0]} has an event outside scenario 5")
            parsed = datetime.fromisoformat(timestamp)
            self.assertIsNotNone(parsed.utcoffset())


if __name__ == "__main__":
    unittest.main()
