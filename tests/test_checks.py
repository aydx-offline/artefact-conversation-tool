import unittest
from pathlib import Path

from ca.brand import load_brand
from ca.checks import check_candidates

BRAND = load_brand(Path(__file__).resolve().parent.parent / "data" / "brand")
SCENARIO = "1 Birthday and festive greetings"
MENU = BRAND.menus[SCENARIO]
TEXTS = ["林女士，生日快乐，祝您今天一切顺心。", "上次的围巾还合用吗？有空来店里喝杯茶。", "最近天气转凉，记得添件衣裳。"]


def candidate(text, i=0, length="简短"):
    return {"strategy": MENU[i], "reason": "r", "tone": "温和", "length": length, "text": text}


def run(texts=TEXTS, *, product_ids=(), owned_ids=(), event=None, **fix):
    cands = [candidate(t, i) for i, t in enumerate(texts)]
    for index, patch in fix.items():
        cands[int(index[1:])].update(patch)
    checks = check_candidates(cands, BRAND, SCENARIO, list(product_ids), list(owned_ids), event)
    return {c.name: c for c in checks}


class CheckTests(unittest.TestCase):
    def test_all_pass(self):
        self.assertTrue(all(c.passed for c in run().values()), run())

    def test_count(self):
        self.assertTrue(run()["count"].passed)
        self.assertFalse(run(TEXTS[:2])["count"].passed)
        self.assertFalse(run(TEXTS[:2] + [" "])["count"].passed)

    def test_chinese_ratio(self):
        ok = "你" * 9 + "a"
        self.assertTrue(run([ok, TEXTS[1], TEXTS[2]])["chinese"].passed)
        self.assertFalse(run(["hello 你好", TEXTS[1], TEXTS[2]])["chinese"].passed)
        self.assertTrue(run(["欢迎来到 Chengbai 澄白店", TEXTS[1], TEXTS[2]])["chinese"].passed)

    def test_length(self):
        def length(text, label):
            return run([text, TEXTS[1], TEXTS[2]], c0={"length": label})["length"].passed

        self.assertTrue(length("好" * 54, "简短"))
        self.assertTrue(length("好" * 40, "适中"))
        self.assertTrue(length("好" * 180, "适中"))
        self.assertFalse(length("好" * 181, "适中"))

    def test_overlap(self):
        self.assertFalse(run([TEXTS[0], TEXTS[0], TEXTS[2]])["overlap"].passed)
        self.assertTrue(run()["overlap"].passed)

    def test_menu_and_distinct(self):
        self.assertFalse(run(c1={"strategy": "不在菜单上"})["menu"].passed)
        self.assertFalse(run(c1={"strategy": MENU[0]})["distinct_strategies"].passed)
        self.assertTrue(run()["distinct_strategies"].passed)

    def test_forbidden(self):
        self.assertFalse(run(["这是最后机会，快来。", TEXTS[1], TEXTS[2]])["forbidden"].passed)

    def test_offer(self):
        self.assertFalse(run(["给您打八折", TEXTS[1], TEXTS[2]])["offer"].passed)
        self.assertTrue(run(["折扣我们没有，价格对每位客人都一样", TEXTS[1], TEXTS[2]])["offer"].passed)

    def test_offer_clauses(self):
        def offer(text):
            return run([text, TEXTS[1], TEXTS[2]])["offer"].passed

        self.assertFalse(offer("给您打八折，没有别的优惠"))
        self.assertFalse(offer("给您打八折，没有"))
        self.assertTrue(offer("我们没有优惠"))
        self.assertTrue(offer("我们不能打折"))
        self.assertTrue(offer("澄白从来不打折"))
        self.assertTrue(offer("实在没法给优惠"))
        self.assertTrue(offer("优惠这边确实给不了"))

    def test_chinese_empty_remainder(self):
        for text in ["", "Chengbai", "，。！"]:
            self.assertFalse(run([text, TEXTS[1], TEXTS[2]])["chinese"].passed, text)

    def test_indexes(self):
        self.assertEqual(run()["count"].indexes, [])
        blank = run(TEXTS[:2] + [" "])["count"]
        self.assertEqual(blank.indexes, [2])
        self.assertNotEqual(blank.reason, run(TEXTS[:2])["count"].reason)
        self.assertEqual(run(["这是最后机会，快来。", TEXTS[1], "给您打八折"])["forbidden"].indexes, [0])
        self.assertEqual(run([TEXTS[0], TEXTS[0], TEXTS[2]])["overlap"].indexes, [1])
        self.assertEqual(run(c1={"strategy": MENU[0]})["distinct_strategies"].indexes, [1])
        self.assertEqual(run(c1={"strategy": "不在菜单上"})["menu"].indexes, [1])
        self.assertEqual(run(c0={"text": "好" * 181})["length"].indexes, [0])

    def test_product(self):
        texts = ["素缎围巾很衬您。", TEXTS[1], TEXTS[2]]
        self.assertFalse(run(texts)["product"].passed)
        self.assertTrue(run(texts, product_ids=["scarf"])["product"].passed)
        self.assertTrue(run(texts, owned_ids=["scarf"])["product"].passed)
        self.assertFalse(run(texts, product_ids=["pearl"])["product"].passed)
        self.assertTrue(run(texts, event={"content": "现场有素缎围巾可以试"})["product"].passed)

    def test_capacity(self):
        texts = ["本次仅限十位", TEXTS[1], TEXTS[2]]
        self.assertFalse(run(texts, event={"capacity": None})["capacity"].passed)
        self.assertFalse(run(texts)["capacity"].passed)
        self.assertTrue(run(texts, event={"capacity": 10})["capacity"].passed)


if __name__ == "__main__":
    unittest.main()
