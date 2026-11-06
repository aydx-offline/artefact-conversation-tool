import json
import tempfile
import unittest
from pathlib import Path

from ca.clients import load_clients, store_hash
from ca.schema import CaseError

FIXTURE = Path(__file__).resolve().parent.parent / "data" / "clients.json"

class ClientsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()) / "clients.json"
        self.tmp.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    def test_loads_lin(self):
        lin = load_clients(FIXTURE)["lin"]
        self.assertEqual(lin["name"], "林女士")
        self.assertEqual(lin["address"], "您")
        self.assertEqual(lin["history"], [])

    def test_every_purchase_has_a_catalog_colour(self):
        from ca.brand import load_brand

        colours = {p["id"]: p["colors"] for p in load_brand(FIXTURE.parent / "brand").catalog}
        for client in load_clients(FIXTURE).values():
            for purchase in client["purchases"]:
                self.assertIn(purchase["color"], colours[purchase["product_id"]], client["name"])

    def test_english_preferences_rejected(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        data["lin"]["preferences"] = "hello"
        self.tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(CaseError) as ctx:
            load_clients(self.tmp)
        self.assertEqual(ctx.exception.field, "preferences")

    def test_bad_address_rejected(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        data["lin"]["address"] = "tu"
        self.tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(CaseError) as ctx:
            load_clients(self.tmp)
        self.assertEqual(ctx.exception.field, "address")

    def test_hash_changes_with_file(self):
        before = store_hash(self.tmp)
        self.assertEqual(before, store_hash(self.tmp))
        data = json.loads(self.tmp.read_text(encoding="utf-8"))
        data["lin"]["preferences"] = "喜欢深色丝绸"
        self.tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        self.assertNotEqual(before, store_hash(self.tmp))


if __name__ == "__main__":
    unittest.main()
