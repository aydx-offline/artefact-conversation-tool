import json
import time
import uuid
from datetime import datetime, timezone

from ca.llm import complete_with_retries
from ca.prompts import JUDGE_FACT_ITEMS, JUDGE_SCORE_ITEMS, judge_prompt
from ca.version import JUDGE_VERSION


def _get(item, name, default=None):
    return item.get(name, default) if isinstance(item, dict) else getattr(item, name, default)


def _evaluation_id():
    started = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    return f"{started}:{uuid.uuid4().hex}"


def evaluate_case(case_file: dict, model, brand) -> list[dict]:
    case = case_file["case"]
    case_id = case["case_id"]
    prompt = judge_prompt(
        case_file["resolved"],
        case_file["candidates"],
        case.get("expectations") or [],
        brand,
    )
    raw = complete_with_retries(model, *prompt, time.sleep)
    try:
        data = json.loads(raw)
        scores = data["scores"]
        if not isinstance(scores, list) or not all(isinstance(row, dict) for row in scores):
            raise TypeError
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError("invalid judge JSON: expected a scores list") from error

    evaluation_id = _evaluation_id()
    common = {
        "evaluation_id": evaluation_id,
        "judge_model": getattr(model, "model_name", type(model).__name__),
        "judge_version": JUDGE_VERSION,
        "case_id": case_id,
    }
    rows = [
        {
            **common,
            "candidate": row.get("candidate"),
            "item": row.get("item"),
            "value": row.get("value"),
            "reason": row.get("reason", ""),
        }
        for row in scores
    ]
    rows.extend(
        {
            **common,
            "candidate": None,
            "item": _get(check, "name"),
            "value": "pass" if _get(check, "passed") else "fail",
            "reason": _get(check, "reason", ""),
        }
        for check in case_file.get("checks", [])
    )
    return rows


def candidate_acceptable(checks, scores) -> bool:
    candidates = {row.get("candidate") for row in scores if row.get("candidate") is not None}
    if len(candidates) != 1:
        return False
    candidate = candidates.pop()
    for check in checks:
        if _get(check, "passed"):
            continue
        indexes = _get(check, "indexes", [])
        if not indexes or candidate in indexes:
            return False

    by_item = {row.get("item"): row.get("value") for row in scores}
    if any(by_item.get(item) not in (1, True, "pass") for item in JUDGE_FACT_ITEMS):
        return False
    try:
        return all(float(by_item[item]) >= 3 for item in JUDGE_SCORE_ITEMS)
    except (KeyError, TypeError, ValueError):
        return False


def case_good(per_candidate: list[bool]) -> bool:
    return len(per_candidate) == 3 and all(per_candidate)
