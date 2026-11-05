import unittest
from pathlib import Path

from ca.brand import load_brand
from ca.schema import SCENARIOS, prose_is_chinese

ROOT = Path(__file__).resolve().parent.parent / "data" / "brand"


class BrandTest(unittest.TestCase):
    def setUp(self):
        self.brand = load_brand(ROOT)

    def test_shape(self):
        self.assertEqual(set(self.brand.menus), set(SCENARIOS))
        self.assertTrue(all(len(v) == 5 for v in self.brand.menus.values()))
        self.assertEqual(len(self.brand.catalog), 4)
        self.assertEqual(len(self.brand.events), 2)
        self.assertEqual(len(self.brand.festivals), 20)

    def test_rules(self):
        rules = self.brand.rules
        self.assertEqual(rules["allowed_english"], ["Chengbai"])
        self.assertEqual(rules["lengths"], {"简短": [1, 50], "适中": [51, 130], "max": 150})
        self.assertIn("%", rules["offer_patterns"])
        for word in ("最后机会", "仅此一天", "马上涨价", "限时"):
            self.assertIn(word, rules["forbidden"])

    def test_chinese_prose(self):
        allowed = self.brand.rules["allowed_english"]
        self.assertTrue(prose_is_chinese(self.brand.voice, allowed))
        for items in self.brand.menus.values():
            for item in items:
                self.assertTrue(prose_is_chinese(item, allowed), item)
        for product in self.brand.catalog:
            for key in ("name", "line", "materials", "care"):
                self.assertTrue(prose_is_chinese(product[key], allowed), product[key])

    def test_events(self):
        self.assertEqual(self.brand.events["winter"]["capacity"], 10)
        self.assertIsNone(self.brand.events["spring"]["capacity"])


if __name__ == "__main__":
    unittest.main()
