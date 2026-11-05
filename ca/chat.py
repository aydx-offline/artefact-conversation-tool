import time
import uuid

from ca.llm import complete_with_retries, parse_json
from ca.prompts import SCENARIO_ZH, chat_prompt
from ca.schema import Case, CaseError, Message, prose_is_chinese

INVALID_REQUEST = "无法读取顾问请求"


def extract_case(request, model, clients, now):
    allowed_names = ["Chengbai", *(client["name"] for client in clients.values())]
    if not prose_is_chinese(request, allowed_names):
        raise CaseError("request", "顾问请求必须使用中文")

    system, user = chat_prompt(request)
    raw = complete_with_retries(model, system, user, time.sleep)
    try:
        extracted = parse_json(raw)
        name = extracted["client_name"]
        scenario = {value: key for key, value in SCENARIO_ZH.items()}[extracted["scenario"]]
        client_message = extracted["client_message"]
        if not all(isinstance(value, str) for value in (name, client_message)):
            raise TypeError
    except (KeyError, TypeError):
        raise CaseError("request", INVALID_REQUEST) from None

    client_id = next(
        (client_id for client_id, client in clients.items() if client["name"] == name),
        None,
    )
    if client_id is None:
        return "未找到该客户，请选择客户。"

    history = [Message("client", client_message, now)] if client_message else None
    return Case(
        case_id=f"chat-{uuid.uuid4().hex}",
        client_id=client_id,
        scenario=scenario,
        timestamp=now,
        history=history,
    )
