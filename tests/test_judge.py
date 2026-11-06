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
            {"candidate": candidate, "item": item, "value": "pass", "reason": "符合输入"}
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

    def test_evaluate_case_keeps_the_judge_call(self):
        from ca.llm import Reply

        raw = Reply(json.dumps({"scores": judge_scores()}, ensure_ascii=False), {"input": 1, "output": 1, "total": 2}, 15)
        rows = evaluate_case(case_file(), FakeModel([raw]), BRAND)
        self.assertEqual(rows.call["usage"]["total"], 2)
        self.assertEqual(rows.call["latency_ms"], 15)
        self.assertIn("林女士", rows.call["prompt"])
        self.assertIn("scores", rows.call["raw"])

    def test_each_evaluation_gets_a_fresh_id(self):
        reply = json.dumps({"scores": judge_scores()}, ensure_ascii=False)
        first = evaluate_case(case_file(), FakeModel([reply]), BRAND)[0]["evaluation_id"]
        second = evaluate_case(case_file(), FakeModel([reply]), BRAND)[0]["evaluation_id"]
        self.assertNotEqual(first, second)

    def test_invalid_judge_json_raises_clear_error(self):
        raw = "不是 JSON"
        with self.assertRaisesRegex(ValueError, "judge JSON") as raised:
            evaluate_case(case_file(), FakeModel(["不是 JSON", raw]), BRAND)
        self.assertEqual(raised.exception.raw, raw)

    def test_invalid_judge_json_is_retried_once(self):
        good = json.dumps({"scores": judge_scores()}, ensure_ascii=False)
        model = FakeModel(["不是 JSON", good])
        rows = evaluate_case(case_file(), model, BRAND)
        self.assertEqual(len(model.calls), 2)
        self.assertEqual(rows.call["raw"], good)

    def test_evaluate_case_normalises_boolean_fact_values(self):
        scores = judge_scores()
        scores[0]["value"] = True
        scores[1]["value"] = False

        rows = evaluate_case(
            case_file(),
            FakeModel([json.dumps({"scores": scores}, ensure_ascii=False)]),
            BRAND,
        )

        self.assertEqual(rows[0]["value"], "pass")
        self.assertEqual(rows[1]["value"], "fail")

    def test_evaluate_case_accepts_integer_fact_values_in_fenced_json(self):
        scores = judge_scores()
        scores[0]["value"] = 1
        scores[1]["value"] = 0
        raw = "说明\n```json\n" + json.dumps({"scores": scores}, ensure_ascii=False) + "\n```\n完毕"

        rows = evaluate_case(case_file(), FakeModel([raw]), BRAND)

        self.assertEqual(rows[0]["value"], "pass")
        self.assertEqual(rows[1]["value"], "fail")

    def test_evaluate_case_rejects_invalid_score_grids_with_raw_reply(self):
        invalid_scores = {
            "bool candidate": [{**row, "candidate": True} if index == 0 else row
                               for index, row in enumerate(judge_scores())],
            "candidate out of range": [{**row, "candidate": 3} if index == 0 else row
                                       for index, row in enumerate(judge_scores())],
            "unknown item": [{**row, "item": "未知"} if index == 0 else row
                             for index, row in enumerate(judge_scores())],
            "bad fact": [{**row, "value": 2} if index == 0 else row
                         for index, row in enumerate(judge_scores())],
            "bool score": [{**row, "value": True} if index == 2 else row
                           for index, row in enumerate(judge_scores())],
            "float score": [{**row, "value": 3.0} if index == 2 else row
                            for index, row in enumerate(judge_scores())],
            "score out of range": [{**row, "value": 6} if index == 2 else row
                                   for index, row in enumerate(judge_scores())],
            "duplicate": judge_scores() + [judge_scores()[0]],
            "missing": judge_scores()[:-1],
        }
        for label, scores in invalid_scores.items():
            raw = json.dumps({"scores": scores}, ensure_ascii=False)
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, "invalid judge") as raised:
                    evaluate_case(case_file(), FakeModel([raw, raw]), BRAND)
                self.assertEqual(raised.exception.raw, raw)

    def test_candidate_is_acceptable_at_threshold(self):
        scores = [row for row in judge_scores() if row["candidate"] == 0]
        self.assertTrue(candidate_acceptable([Check("count", True)], scores))

    def test_candidate_argument_filters_scores_and_check_indexes(self):
        scores = judge_scores()
        scores[-1]["value"] = 2
        check = Check("length", False, "candidate 2 failed", [2])

        self.assertTrue(candidate_acceptable([check], scores, candidate=0))
        self.assertFalse(candidate_acceptable([check], scores, candidate=2))

    def test_candidate_acceptable_uses_strict_validated_values(self):
        scores = [row for row in judge_scores() if row["candidate"] == 0]
        fact = next(row for row in scores if row["item"] in JUDGE_FACT_ITEMS)
        scored = next(row for row in scores if row["item"] in JUDGE_SCORE_ITEMS)

        fact["value"] = True
        self.assertFalse(candidate_acceptable([Check("count", True)], scores))
        fact["value"] = "pass"
        scored["value"] = 3.0
        self.assertFalse(candidate_acceptable([Check("count", True)], scores))

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
