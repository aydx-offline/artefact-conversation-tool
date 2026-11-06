import copy
import time
from dataclasses import asdict, dataclass, field, is_dataclass

from ca.checks import check_candidates
from ca.clients import ALLOWED_NAMES
from ca.context import resolve_context
from ca.llm import combine_calls, complete_with_retries, parse_json
from ca.prompts import draft_prompt
from ca.schema import CaseError, validate_case

CANDIDATE_KEYS = ("strategy", "reason", "tone", "length", "text")


class ModelError(Exception):
    pass


@dataclass
class Step:
    name: str
    prompt: str = ""
    raw: str = ""
    usage: dict | None = None
    latency_ms: int | None = None


@dataclass
class Result:
    status: str
    resolved: dict = field(default_factory=dict)
    steps: list = field(default_factory=list)
    candidates: list = field(default_factory=list)
    checks: list = field(default_factory=list)


def _candidate_list(raw):
    data = parse_json(raw)
    items = data.get("candidates") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    return [i for i in items if isinstance(i, dict) and all(isinstance(i.get(k), str) for k in CANDIDATE_KEYS)]


def _ready(candidates, menu):
    if len(candidates) != 3:
        return False
    strategies = [item["strategy"] for item in candidates]
    return len(set(strategies)) == 3 and all(item in menu for item in strategies)


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
    history = [asdict(m) if is_dataclass(m) else m for m in (case.history if case.history is not None else client.get("history", []))]
    context = resolve_context(case.timestamp, client, brand.festivals, case.occasion, history[-1]["time"] if history else None)
    if case.scenario == "1 Birthday and festive greetings" and not context.occasion:
        raise CaseError("occasion", "scenario 1 needs an occasion")
    return copy.deepcopy(
        {
            "client": client,
            "scenario": case.scenario,
            "products": products,
            "event": event,
            "history": history,
            "occasion": context.occasion if case.scenario == "1 Birthday and festive greetings" else case.occasion,
            "days_since_purchase": context.days_since_purchase,
            "months_since_visit": context.months_since_visit,
            "today": context.today,
            "days_to_birthday": context.days_to_birthday,
            "days_since_message": context.days_since_message,
            "tone": case.tone,
            "length": case.length,
            "expectations": case.expectations,
        }
    )


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
        prompt = draft_prompt(resolved, menu, brand)
        raws, candidates = [], []
        for _ in range(2):
            raws.append(call(prompt))
            candidates = _candidate_list(raws[-1])
            if _ready(candidates, menu):
                break
        record(Step("write", "\n".join(prompt), "\n---\n".join(raws), *combine_calls(raws)))
        if len(candidates) != 3:
            candidates = [{"strategy": "", "reason": "", "tone": "", "length": "", "text": ""} for _ in range(3)]

        owned = [p["product_id"] for p in resolved["client"].get("purchases", [])]
        product_ids = [p["id"] for p in resolved["products"]]
        checks = check_candidates(candidates, brand, case.scenario, product_ids, owned, resolved["event"])
        record(Step("check"))
    except ModelError as error:
        result.candidates, result.checks = [], []
        record(Step("error", "\n".join(prompt), str(error)))
        return finish("failed")

    result.candidates, result.checks = candidates, checks
    record(Step("final"))
    return finish("done" if all(c.passed for c in checks) else "failed_checks")
