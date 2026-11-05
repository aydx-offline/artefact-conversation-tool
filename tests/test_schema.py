import json
import tempfile
import unittest
from pathlib import Path

from ca.schema import Case, CaseError, Message, load_case, validate_case

ALLOWED = ["Chengbai"]

def case(**kwargs):
    base = dict(
        case_id="c1",
        client_id="lin",
        scenario="1 Birthday and festive greetings",
        timestamp="2026-09-25T10:00:00+08:00",
        history=[],
    )
    base.update(kwargs)
    return Case(**base)

class SchemaTest(unittest.TestCase):
    def test_load_case_accepts_json_and_jsonl_rows(self):
        row = {
            "case_id": "c1",
            "client_id": "lin",
            "scenario": "1 Birthday and festive greetings",
            "timestamp": "2026-09-25T10:00:00+08:00",
            "history": [{"sender": "client", "text": "中秋快乐", "time": "2026-09-25T09:00:00+08:00"}],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "case.json"
            path.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
            loaded = load_case(path)
        self.assertEqual(loaded.case_id, "c1")
        self.assertEqual(loaded.history, [Message("client", "中秋快乐", "2026-09-25T09:00:00+08:00")])

    def test_scenario_6_needs_a_client_message(self):
        item = case(scenario="6 Price objection — price too high", history=[])
        with self.assertRaises(CaseError) as caught:
            validate_case(item, allowed_names=ALLOWED)
        self.assertEqual(caught.exception.field, "history")

    def test_scenario_6_price_message_passes(self):
        item = case(
            scenario="6 Price objection — price too high",
            history=[Message("client", "六万八太贵了", "2026-09-25T09:00:00+08:00")],
            product_ids=["yunwen"],
        )
        validate_case(item, allowed_names=ALLOWED)

    def test_english_client_text_is_rejected(self):
        item = case(history=[Message("client", "too expensive", "2026-09-25T09:00:00+08:00")])
        with self.assertRaises(CaseError) as caught:
            validate_case(item, allowed_names=ALLOWED)
        self.assertEqual(caught.exception.field, "history")

    def test_allowed_english_name_passes(self):
        item = case(history=[Message("ca", "Chengbai 的围巾到了", "2026-09-25T09:00:00+08:00")])
        validate_case(item, allowed_names=ALLOWED)

    def test_empty_history_is_valid_for_scenario_1(self):
        validate_case(case(), allowed_names=ALLOWED)

    def test_none_history_is_valid_for_scenario_1(self):
        validate_case(case(history=None), allowed_names=ALLOWED)

    def test_unknown_scenario_names_the_field(self):
        with self.assertRaises(CaseError) as caught:
            validate_case(case(scenario="nope"), allowed_names=ALLOWED)
        self.assertEqual(caught.exception.field, "scenario")

    def test_scenario_6_subtypes_need_their_own_marker(self):
        for scenario, text in [
            ("6 Price objection — comparison", "别家便宜"),
            ("6 Price objection — discount request", "能打折吗"),
        ]:
            msg = [Message("client", text, "2026-09-25T09:00:00+08:00")]
            validate_case(case(scenario=scenario, history=msg), allowed_names=ALLOWED)
        wrong = [Message("client", "太贵了", "2026-09-25T09:00:00+08:00")]
        with self.assertRaises(CaseError):
            validate_case(case(scenario="6 Price objection — discount request", history=wrong), allowed_names=ALLOWED)

    def test_bad_timestamp_sender_and_ids(self):
        bad = [
            ("timestamp", case(timestamp="yesterday")),
            ("history", case(history=[Message("bot", "你好", "2026-09-25T09:00:00+08:00")])),
            ("case_id", case(case_id="")),
            ("client_id", case(client_id="")),
        ]
        for field, item in bad:
            with self.assertRaises(CaseError) as caught:
                validate_case(item, allowed_names=ALLOWED)
            self.assertEqual(caught.exception.field, field)
