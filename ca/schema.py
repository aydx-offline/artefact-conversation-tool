import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

SCENARIOS = (
    "1 Birthday and festive greetings",
    "2 Product recommendation",
    "3 Post-purchase care",
    "4 Reactivation",
    "5 Event invitation",
    "6 Price objection — price too high",
    "6 Price objection — comparison",
    "6 Price objection — discount request",
)

PRICE_MARKERS = {
    "6 Price objection — price too high": ("贵", "价格高"),
    "6 Price objection — comparison": ("别处", "别家", "代购", "其他店", "别的店"),
    "6 Price objection — discount request": ("折扣", "优惠", "打折", "便宜点", "便宜一点"),
}


class CaseError(ValueError):
    def __init__(self, field, message):
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message


@dataclass
class Message:
    sender: str
    text: str
    time: str


@dataclass
class Case:
    case_id: str
    client_id: str
    scenario: str
    timestamp: str
    history: list | None = None
    product_ids: list = field(default_factory=list)
    event_id: str = ""
    occasion: str = ""
    tone: str = ""
    length: str = ""
    split: str = ""
    expectations: list = field(default_factory=list)


def load_case(source):
    data = json.loads(Path(source).read_text(encoding="utf-8")) if isinstance(source, (str, Path)) else dict(source)
    if data.get("history") is not None:
        data["history"] = [message if isinstance(message, Message) else Message(**message) for message in data["history"]]
    return Case(**data)


def prose_is_chinese(text, allowed_names):
    for name in allowed_names:
        text = text.replace(name, "")
    return re.search("[A-Za-z]", text) is None


def validate_case(case, *, allowed_names):
    for name in ("case_id", "client_id"):
        if not getattr(case, name):
            raise CaseError(name, "must not be empty")
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", case.case_id):
        raise CaseError("case_id", "use letters, digits, underscores, dots, and hyphens only")
    if case.scenario not in SCENARIOS:
        raise CaseError("scenario", f"unknown scenario {case.scenario!r}")
    try:
        datetime.fromisoformat(case.timestamp)
    except ValueError:
        raise CaseError("timestamp", "must be ISO-8601")
    for message in case.history or []:
        if message.sender not in ("client", "ca"):
            raise CaseError("history", f"unknown sender {message.sender!r}")
        if not prose_is_chinese(message.text, allowed_names):
            raise CaseError("history", f"text must be Chinese: {message.text!r}")
    if case.scenario.startswith("6"):
        markers = PRICE_MARKERS[case.scenario]
        if not any(m.sender == "client" and any(k in m.text for k in markers) for m in case.history or []):
            raise CaseError("history", "scenario 6 needs a client message with a price marker")
