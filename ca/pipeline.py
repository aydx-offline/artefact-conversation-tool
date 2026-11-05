import copy
import json
import time
from dataclasses import asdict, dataclass, field, is_dataclass

from ca.checks import check_candidates
from ca.clients import ALLOWED_NAMES
from ca.context import resolve_context
from ca.llm import complete_with_retries
from ca.prompts import plan_prompt, revise_prompt, write_prompt
from ca.schema import CaseError, validate_case

CHECK_ZH = {
    "count": "数量或空白",
    "chinese": "中文比例",
    "length": "长度",
    "overlap": "与前面的消息太像",
    "menu": "策略不在菜单上",
    "distinct_strategies": "策略重复",
    "forbidden": "含催促用语",
    "offer": "含不允许的优惠",
    "product": "提到了不该提的产品",
    "capacity": "提到了名额",
}
CANDIDATE_KEYS = ("strategy", "reason", "tone", "length", "text")


class ModelError(Exception):
    pass


@dataclass
class Step:
    name: str
    prompt: str = ""
    raw: str = ""


@dataclass
class Result:
    status: str
    resolved: dict = field(default_factory=dict)
    steps: list = field(default_factory=list)
    candidates: list = field(default_factory=list)
    checks: list = field(default_factory=list)


def _json_object(raw):
    try:
        return json.loads(raw[raw.index("{") : raw.rindex("}") + 1])
    except ValueError:
        return None


def _candidate_list(raw):
    data = _json_object(raw)
    items = data.get("candidates") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    return [i for i in items if isinstance(i, dict) and all(isinstance(i.get(k), str) for k in CANDIDATE_KEYS)]


def _picks(raw, menu):
    data = _json_object(raw)
    picks = data.get("picks") if isinstance(data, dict) else None
    if not isinstance(picks, list) or len(picks) != 3 or not all(isinstance(p, dict) for p in picks):
        return None
    strategies = [p.get("strategy") for p in picks]
    if len(set(strategies)) != 3 or any(s not in menu for s in strategies):
        return None
    if not all(isinstance(p.get("reason"), str) for p in picks):
        return None
    return {"picks": picks}


def _products(case, client, brand):
    ids = list(case.product_ids)
    if not ids and case.scenario == "3 Post-purchase care":
        purchases = client.get("purchases", [])
        if not purchases:
            raise CaseError("product_ids", "scenario 3 needs a purchase")
        ids = [max(purchases, key=lambda p: p["date"])["product_id"]]
    if not ids and (case.scenario.startswith("6") or case.scenario == "2 Product recommendation"):
        raise CaseError("product_ids", "this scenario needs product_ids")
    by_id = {p["id"]: p for p in brand.catalog}
    for pid in ids:
        if pid not in by_id:
            raise CaseError("product_ids", f"unknown product {pid!r}")
    return [copy.deepcopy(by_id[pid]) for pid in ids]


def _resolve(case, brand, clients):
    if case.client_id not in clients:
        raise CaseError("client_id", f"unknown client {case.client_id!r}")
    client = clients[case.client_id]
    products = _products(case, client, brand)
    if (case.event_id or case.scenario == "5 Event invitation") and case.event_id not in brand.events:
        raise CaseError("event_id", f"missing or unknown event {case.event_id!r}")
    event = copy.deepcopy(brand.events[case.event_id]) if case.event_id else None
    context = resolve_context(case.timestamp, client, brand.festivals, case.occasion)
    if case.scenario == "1 Birthday and festive greetings" and not context.occasion:
        raise CaseError("occasion", "scenario 1 needs an occasion")
    history = case.history if case.history is not None else client.get("history", [])
    return copy.deepcopy(
        {
            "client": client,
            "scenario": case.scenario,
            "products": products,
            "event": event,
            "history": [asdict(m) if is_dataclass(m) else m for m in history],
            "occasion": context.occasion,
            "days_since_purchase": context.days_since_purchase,
            "months_since_visit": context.months_since_visit,
            "expectations": case.expectations,
        }
    )


def _failures(checks):
    failures = {}
    for check in checks:
        for i in check.indexes:
            failures.setdefault(i, []).append(CHECK_ZH[check.name])
    return failures


def generate(case, model, brand, clients, recorder, sleep=time.sleep):
    result = Result("failed")

    def record(step):
        result.steps.append(step)
        if recorder:
            recorder.step(case.case_id, step)

    def finish(status):
        result.status = status
        if recorder:
            recorder.finish(case.case_id, result)
        return result

    def call(prompt):
        try:
            return complete_with_retries(model, *prompt, sleep)
        except Exception as error:
            raise ModelError(str(error)) from error

    validate_case(case, allowed_names=ALLOWED_NAMES)
    record(Step("validate"))
    resolved = result.resolved = _resolve(case, brand, clients)
    record(Step("resolve"))
    menu = brand.menus[case.scenario]
    record(Step("select"))

    try:
        prompt = plan_prompt(resolved, menu, brand)
        raws, plan = [], None
        for _ in range(2):
            raws.append(call(prompt))
            plan = _picks(raws[-1], menu)
            if plan:
                break
        record(Step("plan", "\n".join(prompt), "\n---\n".join(raws)))
        if not plan:
            return finish("failed")

        prompt = write_prompt(resolved, plan, brand)
        raw = call(prompt)
        record(Step("write", "\n".join(prompt), raw))
        candidates = _candidate_list(raw)
        if len(candidates) != 3:
            candidates = [{"strategy": p["strategy"], "reason": p["reason"], "tone": "", "length": "", "text": ""} for p in plan["picks"]]

        owned = [p["product_id"] for p in resolved["client"].get("purchases", [])]
        product_ids = [p["id"] for p in resolved["products"]]

        def check():
            checks = check_candidates(candidates, brand, case.scenario, product_ids, owned, resolved["event"])
            record(Step("check"))
            return checks

        checks = check()
        if not all(c.passed for c in checks):
            failures = _failures(checks)
            prompt = revise_prompt(resolved, candidates, failures, brand)
            raw = call(prompt)
            record(Step("revise", "\n".join(prompt), raw))
            for item in _candidate_list(raw):
                if item.get("index") in failures:
                    candidates[item["index"]] = {k: item[k] for k in CANDIDATE_KEYS}
            checks = check()
    except ModelError:
        result.candidates, result.checks = [], []
        return finish("failed")

    result.candidates, result.checks = candidates, checks
    record(Step("final"))
    return finish("done" if all(c.passed for c in checks) else "failed_checks")
