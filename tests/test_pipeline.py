import copy
import json
import unittest
from pathlib import Path

from ca.brand import load_brand
from ca.clients import load_clients
from ca.llm import FakeModel
from ca.pipeline import generate
from ca.schema import Case, CaseError, load_case

ROOT = Path(__file__).resolve().parent.parent
BRAND = load_brand(ROOT / "data" / "brand")
SCENARIO = "1 Birthday and festive greetings"
MENU = BRAND.menus[SCENARIO]
TEXTS = ["林女士，生日快乐，祝您今天一切顺心。", "上次的围巾还合用吗？有空来店里喝杯茶。", "最近天气转凉，记得添件衣裳。"]
NEW_TEXTS = ["林女士，愿您今天被喜欢的人和事围绕。", "秋意渐浓，店里新到了一些茶，等您来尝。"]


def clients():
    return copy.deepcopy(load_clients(ROOT / "data" / "clients.json"))


def make_case(**fields):
    base = dict(case_id="c1", client_id="lin", scenario=SCENARIO, timestamp="2026-11-04T10:00:00", occasion="生日")
    return Case(**{**base, **fields})


def plan(*strategies):
    return json.dumps({"picks": [{"strategy": s, "reason": "合她的情况"} for s in strategies]}, ensure_ascii=False)


def candidate(i, text, **fields):
    return {"strategy": MENU[i], "reason": "合她的情况", "tone": "亲切温暖", "length": "简短", "text": text, **fields}


def write(texts):
    return json.dumps({"candidates": [candidate(i, t) for i, t in enumerate(texts)]}, ensure_ascii=False)


def revise(items):
    return json.dumps({"candidates": [candidate(i, t, index=i) for i, t in items]}, ensure_ascii=False)


def fenced(raw):
    return f"结果如下：\n```json\n{raw}\n```\n"


def run(replies, case=None, store=None):
    model = FakeModel(replies)
    result = generate(case or make_case(), model, BRAND, store or clients(), None, sleep=lambda s: None)
    return model, result


class PipelineTests(unittest.TestCase):
    def test_scenario_1_without_occasion_is_rejected_before_any_model_call(self):
        model = FakeModel([])
        with self.assertRaises(CaseError) as caught:
            generate(make_case(occasion=""), model, BRAND, clients(), None, sleep=lambda s: None)
        self.assertEqual(caught.exception.field, "occasion")
        self.assertEqual(model.calls, [])

    def test_one_call_retries_then_finishes(self):
        first = json.dumps(
            {"candidates": [candidate(0, text) for text in TEXTS]},
            ensure_ascii=False,
        )
        model, result = run([first, fenced(write(TEXTS))])
        self.assertEqual(result.status, "done")
        self.assertEqual(len(model.calls), 2)
        self.assertEqual([s.name for s in result.steps], ["validate", "resolve", "select", "write", "check", "final"])
        self.assertEqual([c["text"] for c in result.candidates], TEXTS)
        self.assertTrue(all(c.passed for c in result.checks))

    def test_model_steps_keep_token_cost_and_latency(self):
        from ca.llm import Reply

        write_reply = Reply(fenced(write(TEXTS)), {"input": 4, "output": 5, "total": 9, "total_cost": 0.4}, 20)
        _, result = run([write_reply])
        write_step = next(step for step in result.steps if step.name == "write")
        self.assertEqual(write_step.usage["total_cost"], 0.4)
        self.assertEqual(write_step.latency_ms, 20)

    def test_revise_replaces_only_failing_indexes(self):
        model, result = run([write([TEXTS[0]] * 3), fenced(revise([(1, NEW_TEXTS[0]), (2, NEW_TEXTS[1])]))])
        self.assertEqual(result.status, "done")
        user = model.calls[1][1]
        self.assertIn("1. 策略", user)
        self.assertIn("2. 策略", user)
        self.assertNotIn("0. 策略", user)
        self.assertEqual([c["text"] for c in result.candidates], [TEXTS[0], *NEW_TEXTS])
        self.assertEqual(
            [s.name for s in result.steps],
            ["validate", "resolve", "select", "write", "check", "revise", "check", "final"],
        )

    def test_invalid_write_json_is_repaired_by_revise(self):
        _, result = run(["这不是 JSON", "还不是", revise(enumerate(TEXTS))])
        self.assertEqual(result.status, "done")
        self.assertEqual([c["text"] for c in result.candidates], TEXTS)

    def test_still_failing_after_revise_keeps_candidates(self):
        _, result = run([write([TEXTS[0]] * 3), revise([(1, TEXTS[0]), (2, TEXTS[0])])])
        self.assertEqual(result.status, "failed_checks")
        self.assertEqual(len(result.candidates), 3)

    def test_model_errors_fail_the_case_with_no_candidates(self):
        _, result = run([RuntimeError("断线")] * 3)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.candidates, [])
        self.assertEqual(result.steps[-1].name, "error")
        self.assertIn("断线", result.steps[-1].raw)
        self.assertIn('"candidates"', result.steps[-1].prompt)

    def test_revise_accepts_string_indexes(self):
        raw = json.dumps(
            {"candidates": [candidate(i, text, index=str(i)) for i, text in enumerate(NEW_TEXTS, 1)]},
            ensure_ascii=False,
        )
        _, result = run([write([TEXTS[0]] * 3), raw])
        self.assertEqual([c["text"] for c in result.candidates], [TEXTS[0], *NEW_TEXTS])

    def test_only_explicit_non_greeting_occasions_reach_prompts(self):
        rows = {
            row["case_id"]: row
            for line in (ROOT / "cases" / "inputs.jsonl").read_text(encoding="utf-8").splitlines()
            if (row := json.loads(line))["case_id"] in {"f13", "f14"}
        }
        for case_id, expected, absent in (("f13", "", "端午"), ("f14", "七夕", "")):
            case = load_case(rows[case_id])
            menu = BRAND.menus[case.scenario]
            model = FakeModel([plan(*menu[:3]), RuntimeError("stop"), RuntimeError("stop"), RuntimeError("stop")])

            result = generate(case, model, BRAND, clients(), None, sleep=lambda s: None)
            prompts = "\n".join(text for call in model.calls for text in call)

            self.assertEqual(result.resolved["occasion"], expected)
            if expected:
                self.assertIn(expected, prompts)
            if absent:
                self.assertNotIn(absent, prompts)

    def test_expectations_never_reach_the_model(self):
        case = make_case(expectations=["必须提到围巾保养"])
        model, result = run([write(TEXTS)], case)
        seen = [text for call in model.calls for text in call] + [s.prompt for s in result.steps]
        self.assertFalse(any("必须提到围巾保养" in text for text in seen))
        self.assertEqual(result.resolved["expectations"], ["必须提到围巾保养"])

    def test_resolved_is_a_copy_of_the_store(self):
        store = clients()
        _, result = run([write(TEXTS)], store=store)
        store["lin"]["name"] = "改名"
        self.assertEqual(result.resolved["client"]["name"], "林女士")

    def test_history_omission_and_empty_list_resolve_differently(self):
        store = clients()
        stored = [{"sender": "client", "text": "最近好吗？", "time": "2026-10-01T10:00:00"}]
        store["lin"]["history"] = stored

        _, omitted = run([write(TEXTS)], store=store)
        _, empty = run([write(TEXTS)], case=make_case(history=[]), store=store)

        self.assertEqual(omitted.resolved["history"], stored)
        self.assertEqual(empty.resolved["history"], [])

    def test_product_and_event_rules(self):
        for scenario, field in (("2 Product recommendation", "product_ids"), ("5 Event invitation", "event_id")):
            with self.assertRaises(CaseError) as caught:
                generate(make_case(scenario=scenario), FakeModel([]), BRAND, clients(), None, sleep=lambda s: None)
            self.assertEqual(caught.exception.field, field)

    def test_post_purchase_defaults_to_latest_purchase(self):
        case = make_case(scenario="3 Post-purchase care")
        menu = BRAND.menus[case.scenario]
        _, result = run([plan(*menu[:3]), "坏"], case)
        self.assertEqual([p["id"] for p in result.resolved["products"]], ["scarf"])
        self.assertEqual(result.resolved["days_since_purchase"], 247)


if __name__ == "__main__":
    unittest.main()
