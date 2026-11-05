import json
import tempfile
import unittest
from pathlib import Path

from ca.clients import load_clients, save_client, store_hash
from ca.schema import CaseError

FIXTURE = Path(__file__).resolve().parent.parent / "data" / "clients.json"

WANG = {
    "id": "wang",
    "name": "王先生",
    "tier": "新客",
    "relationship": "生",
    "address": "你",
    "birthday": "08-20",
    "preferences": "喜欢深色皮具",
    "purchases": [],
    "last_visit": "2026-05-10",
    "history": [{"sender": "client", "text": "你好", "time": "2026-05-10T10:00"}],
}


class ClientsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()) / "clients.json"
        self.tmp.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    def test_loads_lin(self):
        lin = load_clients(FIXTURE)["lin"]
        self.assertEqual(lin["name"], "林女士")
        self.assertEqual(lin["address"], "您")
        self.assertEqual(lin["history"], [])

    def test_english_preferences_rejected(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        data["lin"]["preferences"] = "hello"
        self.tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(CaseError) as ctx:
            load_clients(self.tmp)
        self.assertEqual(ctx.exception.field, "preferences")

    def test_bad_address_rejected(self):
        with self.assertRaises(CaseError) as ctx:
            save_client(self.tmp, {**WANG, "address": "tu"})
        self.assertEqual(ctx.exception.field, "address")

    def test_save_round_trips(self):
        save_client(self.tmp, WANG)
        clients = load_clients(self.tmp)
        self.assertEqual(clients["wang"], WANG)
        self.assertIn("lin", clients)

    def test_hash_changes_with_file(self):
        before = store_hash(self.tmp)
        self.assertEqual(before, store_hash(self.tmp))
        save_client(self.tmp, WANG)
        self.assertNotEqual(before, store_hash(self.tmp))


if __name__ == "__main__":
    unittest.main()
