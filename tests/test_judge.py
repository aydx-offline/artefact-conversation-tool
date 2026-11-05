import copy
import json
import unittest
from dataclasses import asdict
from pathlib import Path

from ca.brand import load_brand
from ca.checks import Check
from ca.judge import candidate_acceptable, case_good, evaluate_case
from ca.llm import FakeModel
from ca.prompts import JUDGE_FACT_ITEMS, JUDGE_SCORE_ITEMS
from ca.version import JUDGE_VERSION

ROOT = Path(__file__).resolve().parent.parent
BRAND = load_brand(ROOT / "data" / "brand")
CANDIDATES = [
    {"strategy": "只问好，不提购买", "reason": "适合生日", "tone": "亲切温暖", "length": "简短", "text": "林女士，祝您生日快乐。"},
    {"strategy": "提起她之前买过的一件东西", "reason": "贴合购买记录", "tone": "得体典雅", "length": "简短", "text": "林女士，愿素缎围巾陪您度过好时光。"},
    {"strategy": "把这个日子和她的生活连起来", "reason": "贴合日子", "tone": "真诚走心", "length": "简短", "text": "林女士，愿新一岁皆是从容欢喜。"},
]


def judge_scores(value=3):
    rows = []
    for candidate in range(3):
        rows.extend(
            {"candidate": candidate, "item": item, "value": 1, "reason": "符合输入"}
            for item in JUDGE_FACT_ITEMS
        )
        rows.extend(
            {"candidate": candidate, "item": item, "value": value, "reason": "表现合格"}
            for item in JUDGE_SCORE_ITEMS
        )
    return rows


def case_file(checks=None):
    return {
        "case": {"case_id": "c1", "expectations": {"must": "祝福生日", "must_not": "催促购买"}},
        "resolved": {
            "client": {
                "name": "林女士",
                "tier": "常客",
                "relationship": "熟",
                "address": "您",
                "birthday": "03-15",
                "preferences": "喜欢素色丝绸",
                "purchases": [],
            },
            "scenario": "1 Birthday and festive greetings",
            "history": [],
            "products": [],
            "event": None,
            "occasion": "生日",
            "days_since_purchase": None,
            "months_since_visit": None,
        },
        "candidates": copy.deepcopy(CANDIDATES),
        "checks": [asdict(c) for c in (checks or [Check("count", True)])],
    }


class JudgeTests(unittest.TestCase):
    def test_evaluate_case_returns_judge_and_code_score_rows(self):
        model = FakeModel([json.dumps({"scores": judge_scores()}, ensure_ascii=False)])
        model.model_name = "glm-judge"

        rows = evaluate_case(case_file(), model, BRAND)

        self.assertEqual(len(rows), 25)
        self.assertEqual({row["evaluation_id"] for row in rows}, {rows[0]["evaluation_id"]})
        self.assertTrue(all(set(row) == {
            "evaluation_id", "judge_model", "judge_version", "case_id",
            "candidate", "item", "value", "reason",
        } for row in rows))
        self.assertEqual(rows[-1]["value"], "pass")
        self.assertEqual(rows[-1]["candidate"], None)
        self.assertTrue(all(row["judge_version"] == JUDGE_VERSION for row in rows))
        self.assertIn("祝福生日", model.calls[0][1])

    def test_each_evaluation_gets_a_fresh_id(self):
        reply = json.dumps({"scores": judge_scores()}, ensure_ascii=False)
        first = evaluate_case(case_file(), FakeModel([reply]), BRAND)[0]["evaluation_id"]
        second = evaluate_case(case_file(), FakeModel([reply]), BRAND)[0]["evaluation_id"]
        self.assertNotEqual(first, second)

    def test_invalid_judge_json_raises_clear_error(self):
        with self.assertRaisesRegex(ValueError, "judge JSON"):
            evaluate_case(case_file(), FakeModel(["不是 JSON"]), BRAND)

    def test_candidate_is_acceptable_at_threshold(self):
        scores = [row for row in judge_scores() if row["candidate"] == 0]
        self.assertTrue(candidate_acceptable([Check("count", True)], scores))

    def test_low_judge_item_is_not_acceptable(self):
        scores = [row for row in judge_scores() if row["candidate"] == 0]
        scores[-1]["value"] = 2
        self.assertFalse(candidate_acceptable([Check("count", True)], scores))

    def test_indexed_check_only_fails_flagged_candidate(self):
        check = Check("length", False, "candidates [1]", [1])
        first = [row for row in judge_scores() if row["candidate"] == 0]
        second = [row for row in judge_scores() if row["candidate"] == 1]
        self.assertTrue(candidate_acceptable([check], first))
        self.assertFalse(candidate_acceptable([check], second))

    def test_global_failed_check_fails_every_candidate(self):
        check = Check("overlap", False, "pair failed")
        scores = [row for row in judge_scores() if row["candidate"] == 0]
        self.assertFalse(candidate_acceptable([check], scores))

    def test_case_is_good_only_when_all_three_are_acceptable(self):
        self.assertTrue(case_good([True, True, True]))
        self.assertFalse(case_good([True, True, False]))
        self.assertFalse(case_good([True, True]))


if __name__ == "__main__":
    unittest.main()
