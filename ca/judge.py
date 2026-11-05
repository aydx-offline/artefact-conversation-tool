import json
import time
import uuid
from datetime import datetime, timezone

from ca.llm import complete_with_retries
from ca.prompts import JUDGE_FACT_ITEMS, JUDGE_SCORE_ITEMS, judge_prompt
from ca.version import JUDGE_VERSION


class JudgeError(ValueError):
    def __init__(self, message, raw):
        super().__init__(message)
        self.raw = raw


def _get(item, name, default=None):
    return item.get(name, default) if isinstance(item, dict) else getattr(item, name, default)


def evaluation_id():
    started = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    return f"{started}:{uuid.uuid4().hex}"


def _validated_scores(raw):
    try:
        scores = json.loads(raw)["scores"]
        if not isinstance(scores, list) or not all(isinstance(row, dict) for row in scores):
            raise TypeError
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise JudgeError("invalid judge JSON: expected a scores list", raw) from error

    items = set(JUDGE_FACT_ITEMS + JUDGE_SCORE_ITEMS)
    expected = {(candidate, item) for candidate in range(3) for item in items}
    seen = set()
    for row in scores:
        candidate = row.get("candidate")
        item = row.get("item")
        value = row.get("value")
        if isinstance(candidate, bool) or not isinstance(candidate, int) or candidate not in range(3):
            raise JudgeError("invalid judge row: candidate must be an integer from 0 to 2", raw)
        if item not in items:
            raise JudgeError("invalid judge row: unknown item", raw)
        key = (candidate, item)
        if key in seen:
            raise JudgeError("invalid judge rows: duplicate candidate and item", raw)
        seen.add(key)
        if item in JUDGE_FACT_ITEMS:
            if isinstance(value, bool):
                row["value"] = "pass" if value else "fail"
            elif value not in ("pass", "fail"):
                raise JudgeError("invalid judge row: fact value must be pass or fail", raw)
        elif isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise JudgeError("invalid judge row: score value must be an integer from 1 to 5", raw)
    if seen != expected:
        raise JudgeError("invalid judge rows: all candidates and items are required", raw)
    return scores


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
    scores = _validated_scores(raw)

    current_evaluation_id = evaluation_id()
    common = {
        "evaluation_id": current_evaluation_id,
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


def candidate_acceptable(checks, scores, candidate=None) -> bool:
    if candidate is None:
        candidates = {row.get("candidate") for row in scores if row.get("candidate") is not None}
        if len(candidates) != 1:
            return False
        candidate = candidates.pop()
    scores = [row for row in scores if row.get("candidate") == candidate]
    for check in checks:
        if _get(check, "passed"):
            continue
        indexes = _get(check, "indexes", [])
        if not indexes or candidate in indexes:
            return False

    by_item = {row.get("item"): row.get("value") for row in scores}
    if any(by_item.get(item) != "pass" for item in JUDGE_FACT_ITEMS):
        return False
    return all(
        isinstance(by_item.get(item), int)
        and not isinstance(by_item[item], bool)
        and by_item[item] >= 3
        for item in JUDGE_SCORE_ITEMS
    )


def case_good(per_candidate: list[bool]) -> bool:
    return len(per_candidate) == 3 and all(per_candidate)
