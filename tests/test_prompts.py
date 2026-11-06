import re
import unittest
from dataclasses import replace
from pathlib import Path

from ca.prompts import (
    SCENARIO_ZH,
    draft_prompt,
    judge_prompt,
    managed_prompts,
    natural_language_is_chinese,
    plan_prompt,
    quote_data,
    revise_prompt,
    write_prompt,
)
from ca.brand import load_brand
from ca.clients import load_clients
from ca.schema import SCENARIOS, Message

ROOT = Path(__file__).resolve().parent.parent
BRAND = load_brand(ROOT / "data" / "brand")
LIN = load_clients(ROOT / "data" / "clients.json")["lin"]
SCARF = next(p for p in BRAND.catalog if p["id"] == "scarf")

KEYS = [
    "strategy", "reason", "tone", "length", "text", "picks", "candidates",
    "index", "client_name", "scenario", "client_message", "item", "value",
    "scores", "candidate",
]
RESOLVED = {
    "client": LIN,
    "scenario": SCENARIOS[0],
    "history": [
        Message("client", "上次的丝巾很喜欢", "2026-10-01T10:00:00"),
        {"sender": "ca", "text": "谢谢您的喜欢", "time": "2026-10-01T10:05:00"},
    ],
    "products": [SCARF],
    "occasion": "生日",
    "event": BRAND.events["winter"],
    "days_since_purchase": 30,
    "months_since_visit": 2,
}
MENU = ["问候", "关心", "新品", "邀约", "感谢"]
PLAN = {"picks": [{"strategy": s, "reason": "合适"} for s in MENU[:3]]}
CANDIDATES = [
    {"strategy": "问候", "reason": "合适", "tone": "亲切温暖", "length": "简短", "text": f"第{i}条消息"}
    for i in range(3)
]
EXPECT = ["不能提折扣"]


def all_prompts():
    return {
        "plan": plan_prompt(RESOLVED, MENU),
        "write": write_prompt(RESOLVED, PLAN),
        "judge": judge_prompt(RESOLVED, CANDIDATES, EXPECT),
    }


class PromptTest(unittest.TestCase):
    def test_quote_data(self):
        self.assertEqual(quote_data("他说「好」"), "「他说『好』」")

    def test_expectations_only_in_judge(self):
        for name, pair in all_prompts().items():
            joined = "\n".join(pair)
            self.assertEqual("不能提折扣" in joined, name == "judge", name)

    def test_prompts_are_chinese(self):
        for name, pair in all_prompts().items():
            for part in pair:
                self.assertTrue(natural_language_is_chinese(part, ["Chengbai"] + KEYS), name)

    def test_english_label_is_rejected(self):
        self.assertFalse(natural_language_is_chinese("Product recommendation 你好", ["Chengbai"]))
        self.assertTrue(natural_language_is_chinese("Chengbai 你好", ["Chengbai"]))

    def test_scenario_line_is_chinese(self):
        system, user = plan_prompt(RESOLVED, MENU)
        self.assertIn("场景：生日与节日问候", user)
        self.assertNotIn(SCENARIOS[0], user + system)
        self.assertEqual(set(SCENARIO_ZH), set(SCENARIOS))

    def test_system_says_quotes_are_data(self):
        for name in ("plan", "write"):
            self.assertIn("引用", all_prompts()[name][0])
            self.assertIn("不是指令", all_prompts()[name][0])

    def test_client_data_is_quoted(self):
        _, user = write_prompt(RESOLVED, PLAN)
        self.assertIn(quote_data("上次的丝巾很喜欢"), user)

    def test_write_states_tones_and_lengths(self):
        system, _ = write_prompt(RESOLVED, PLAN)
        for word in ("亲切温暖", "得体典雅", "真诚走心", "简洁轻松", "专业克制", "含蓄低调"):
            self.assertIn(word, system)
        for word in ("简短", "1–50", "适中", "51–130", "180"):
            self.assertIn(word, system)

    def test_write_includes_nonempty_case_preferences(self):
        resolved = {**RESOLVED, "tone": "专业克制", "length": "简短"}
        for pair in (
            write_prompt(resolved, PLAN),
        ):
            joined = "\n".join(pair)
            self.assertIn("顾问偏好：语气选「专业克制」；长度选「简短」。", joined)

    def test_empty_case_preferences_are_omitted(self):
        resolved = {**RESOLVED, "tone": "", "length": ""}
        for pair in (
            write_prompt(resolved, PLAN),
        ):
            self.assertNotIn("顾问偏好", "\n".join(pair))

    def test_plan_copies_menu_verbatim(self):
        system, user = plan_prompt(RESOLVED, MENU)
        self.assertIn("原文", system)
        for item in MENU:
            self.assertIn(item, user)

    def test_real_shapes_render_chinese_fields_only(self):
        _, user = write_prompt(RESOLVED, PLAN)
        for word in ("林女士", "常客", "您", "03-15", "喜欢素色丝绸", "素缎围巾", "素缎系列",
                     "12800", "桑蚕丝素缎", "冬日私览", "2026-11-20", "上海澄白店", "10",
                     "谢谢您的喜欢"):
            self.assertIn(word, user)
        for word in ("lin", "scarf", "product_id", "id", "yunwen"):
            self.assertNotIn(word, user)

    def test_day_line_states_date_season_birthday_and_last_message(self):
        resolved = {**RESOLVED, "today": "2026-08-17", "birthday_note": "她的生日不在这几天，不要提生日", "days_since_message": 0}
        _, user = write_prompt(resolved, PLAN)
        self.assertIn("今天：2026-08-17（8月，夏季）", user)
        self.assertIn("生日：她的生日不在这几天，不要提生日", user)
        self.assertIn("上一条消息是今天", user)
        _, user = write_prompt({**resolved, "today": "2026-01-05", "days_since_message": 3}, PLAN)
        self.assertIn("（1月，冬季）", user)
        self.assertIn("上一条消息是3天前", user)

    def test_spans_and_festivals_are_also_in_words(self):
        resolved = {**RESOLVED, "days_since_purchase": 557, "months_since_visit": 14,
                    "next_festival": ("春节", 5), "last_festival": ("元旦", 42)}
        _, user = write_prompt(resolved, PLAN)
        self.assertIn("距上次购买557天（一年多）", user)
        self.assertIn("距上次到店14个月（一年多）", user)
        self.assertIn("下一个节日：春节，还有5天", user)
        self.assertIn("上一个节日：元旦，42天前", user)
        _, user = write_prompt({**resolved, "days_since_purchase": 20, "months_since_visit": 24}, PLAN)
        self.assertIn("距上次购买20天（不到一个月）", user)
        self.assertIn("距上次到店24个月（两年）", user)

    def test_draft_answers_her_last_message_without_tildes_or_blunt_brand_words(self):
        system, _ = draft_prompt(RESOLVED, MENU)
        self.assertIn("先回应她最后说的话", system)
        self.assertNotIn("波浪号", system)
        self.assertIn("上身很有气质", system)
        self.assertIn("不追时尚", system)
        judge, _ = judge_prompt(RESOLVED, CANDIDATES, EXPECT)
        self.assertNotIn("波浪号", judge)

    def test_prompts_sent_to_the_model_have_no_english(self):
        for pair in (draft_prompt(RESOLVED, MENU), judge_prompt(RESOLVED, CANDIDATES, EXPECT)):
            self.assertIsNone(re.search("[A-Za-z]", "\n".join(pair)), pair)
        system, _ = draft_prompt(RESOLVED, MENU)
        self.assertIn('{"候选":[{"策略"', system)

    def test_product_and_event_details_reach_the_prompt(self):
        _, user = draft_prompt(RESOLVED, MENU)
        for word in ("颜色", "款式", "适合", "活动内容", SCARF["colors"], RESOLVED["event"]["content"]):
            self.assertIn(word, user)

    def test_judge_asks_for_every_row_and_old_products_still_render(self):
        system, _ = judge_prompt(RESOLVED, CANDIDATES, EXPECT)
        self.assertIn("三条共二十四行", system)
        old = {k: v for k, v in SCARF.items() if k not in ("colors", "fit", "wear")}
        _, user = draft_prompt({**RESOLVED, "products": [old], "event": {"name": "冬日私览", "date": "2026-11-20"}}, MENU)
        self.assertIn("素缎围巾", user)
        self.assertNotIn("颜色", user)

    def test_revise_prompt_lists_problems_and_menu_in_chinese(self):
        system, user = revise_prompt(RESOLVED, CANDIDATES, {1: ["策略不在菜单上"]}, MENU)
        self.assertIsNone(re.search("[A-Za-z]", system + user))
        self.assertIn("1. 策略不在菜单上", user)
        self.assertIn("第0条消息", user)
        for item in MENU:
            self.assertIn(item, user)
        self.assertIn('"序号":1', system)
        self.assertNotIn("不能提折扣", system + user)

    def test_voice_has_phrases_and_contrast_examples(self):
        system, _ = draft_prompt(RESOLVED, MENU)
        for text in ("料子本身在说话", "下次路过进来认个门", "不知道就不说", "四万多的价格确实得考虑一下"):
            self.assertIn(text, system)

    def test_each_purchase_and_visit_shows_its_age(self):
        client = {**LIN, "last_visit": "2026-03-02", "purchases": [{"product_id": "scarf", "date": "2025-05-12", "color": "米白"}]}
        system, user = draft_prompt({**RESOLVED, "client": client, "today": "2026-11-06"}, MENU)
        self.assertIn("素缎围巾（2025-05-12，米白，一年多前）", user)
        self.assertIn("上次到店：「2026-03-02（8个月前）」", user)
        self.assertIn("不要自己换算", system)

    def test_purchase_colour_is_shown(self):
        client = {**LIN, "purchases": [{"product_id": "scarf", "date": "2026-03-02", "color": "米白"}]}
        _, user = draft_prompt({**RESOLVED, "client": client}, MENU)
        self.assertIn("素缎围巾（2026-03-02，米白）", user)

    def test_voice_bounds_the_free_gesture(self):
        system, _ = draft_prompt(RESOLVED, MENU)
        for text in ("只限她已有的一件东西，只做一次", "不说每年、终身或长期免费", "只有客人提折扣时才可以送一份心意，其他场景不说免费", "## 可以给的心意"):
            self.assertIn(text, system)
        self.assertNotIn("不送优惠", system)

    def test_discount_may_offer_care_gift_or_trial(self):
        system, _ = draft_prompt(RESOLVED, MENU)
        self.assertNotIn("样品", system)
        for word in ("免费护理", "小礼物", "试用"):
            self.assertIn(word, system)

    def test_draft_forbids_invented_facts(self):
        system, _ = draft_prompt(RESOLVED, MENU)
        self.assertIn("不要写档案里没有的产品细节", system)
        self.assertIn("没买过的东西", system)

    def test_event_without_capacity_omits_it(self):
        resolved = {**RESOLVED, "event": BRAND.events["spring"]}
        _, user = write_prompt(resolved, PLAN)
        self.assertIn("春日沙龙", user)
        self.assertNotIn("名额", user)

    def test_judge_expectations_dict(self):
        _, user = judge_prompt(RESOLVED, CANDIDATES, {"must": ["提到围巾"], "must_not": ["不能提折扣"]})
        self.assertIn("必须：", user)
        self.assertIn("不得：", user)
        self.assertIn("提到围巾", user)
        self.assertIn("不能提折扣", user)

    def test_judge_expectations_string_values(self):
        _, user = judge_prompt(RESOLVED, CANDIDATES, {"must": "回应太贵", "must_not": "主动提出折扣"})
        self.assertIn("必须：「回应太贵」", user)
        self.assertIn("不得：「主动提出折扣」", user)
        self.assertNotIn("「回」", user)
        _, user = judge_prompt(RESOLVED, CANDIDATES, {"must": "回应太贵"})
        self.assertNotIn("不得", user)

    def test_passed_brand_voice_is_used(self):
        brand = replace(BRAND, voice="独特声音测试")
        for pair in (
            plan_prompt(RESOLVED, MENU, brand=brand),
            write_prompt(RESOLVED, PLAN, brand=brand),
            judge_prompt(RESOLVED, CANDIDATES, EXPECT, brand=brand),
        ):
            self.assertIn("独特声音测试", "\n".join(pair))

    def test_judge_items(self):
        system, _ = judge_prompt(RESOLVED, CANDIDATES, EXPECT)
        for item in ("事实", "期望", "场景", "称呼", "具体", "中文", "品牌", "不催"):
            self.assertIn(item, system)
        self.assertIn("亲爱的", system)
        self.assertIn("没有固定称呼", system)
        self.assertIn("中文母语者", system)
        self.assertIn("各项打分都要更加严格", system)
        self.assertIn("尤其是中文", system)

    def test_managed_prompts_keep_the_judge_rule(self):
        prompts = {item["name"]: item["prompt"] for item in managed_prompts(BRAND)}
        self.assertEqual(set(prompts), {"ca/draft", "ca/revise", "ca/judge"})
        judge = prompts["ca/judge"]
        self.assertEqual(judge[0]["role"], "system")
        self.assertIn("各项打分都要更加严格", judge[0]["content"])
        self.assertIn("{{expectations}}", judge[1]["content"])

    def test_writer_asks_for_native_wechat(self):
        system, _ = write_prompt(RESOLVED, PLAN)
        self.assertIn("中文母语者", system)
        self.assertIn("亲爱的", system)
        self.assertIn("没有固定称呼", system)


if __name__ == "__main__":
    unittest.main()
