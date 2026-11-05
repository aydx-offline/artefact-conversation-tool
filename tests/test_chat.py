import copy
import json
import unittest
from pathlib import Path

from ca.chat import extract_case
from ca.clients import load_clients
from ca.llm import FakeModel
from ca.schema import CaseError, Message

ROOT = Path(__file__).resolve().parent.parent
NOW = "2026-11-04T20:25:00+08:00"


def reply(**fields):
    return json.dumps(fields, ensure_ascii=False)


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.clients = load_clients(ROOT / "data" / "clients.json")

    def test_extracts_case_for_existing_client(self):
        model = FakeModel([
            "回复如下：\n```json\n" + reply(
                client_name="林女士",
                scenario="价格异议：和其他渠道比较",
                client_message="价格比别处贵",
            ) + "\n```"
        ])

        case = extract_case("林女士说价格比别处贵，帮我回一下。", model, self.clients, NOW)

        self.assertEqual(case.client_id, "lin")
        self.assertEqual(case.scenario, "6 Price objection — comparison")
        self.assertEqual(case.timestamp, NOW)
        self.assertEqual(case.history, [Message("client", "价格比别处贵", NOW)])
        self.assertTrue(case.case_id.startswith("chat-"))
        self.assertEqual((case.product_ids, case.event_id, case.tone, case.length), ([], "", "", ""))

    def test_unknown_client_asks_ca_to_pick_without_changing_store(self):
        before = copy.deepcopy(self.clients)
        store_path = ROOT / "data" / "clients.json"
        file_before = store_path.read_bytes()
        model = FakeModel([
            reply(client_name="不存在", scenario="重新联系", client_message="")
        ])

        result = extract_case("请帮不存在的客户重新联系。", model, self.clients, NOW)

        self.assertIn("请选择客户", result)
        self.assertEqual(self.clients, before)
        self.assertEqual(store_path.read_bytes(), file_before)

    def test_non_chinese_request_is_rejected_before_model_call(self):
        model = FakeModel([])

        with self.assertRaises(CaseError) as caught:
            extract_case("Please help 林女士", model, self.clients, NOW)

        self.assertEqual(caught.exception.field, "request")
        self.assertEqual(model.calls, [])

    def test_invalid_model_reply_is_a_plain_request_error(self):
        replies = (
            "无法解析",
            reply(client_name="林女士", scenario="未知场景", client_message="您好"),
            reply(client_name="林女士", scenario="重新联系"),
        )
        for raw in replies:
            with self.subTest(raw=raw):
                with self.assertRaises(CaseError) as caught:
                    extract_case("请帮林女士重新联系。", FakeModel([raw]), self.clients, NOW)
                self.assertEqual(caught.exception.field, "request")
                self.assertEqual(caught.exception.message, "无法读取顾问请求")

    def test_case_ids_are_unique(self):
        raw = reply(client_name="林女士", scenario="重新联系", client_message="")
        first = extract_case("请帮林女士重新联系。", FakeModel([raw]), self.clients, NOW)
        second = extract_case("请帮林女士重新联系。", FakeModel([raw]), self.clients, NOW)
        self.assertNotEqual(first.case_id, second.case_id)


if __name__ == "__main__":
    unittest.main()
