import json
import time
import urllib.error
import urllib.request


class FakeModel:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def complete(self, system, user):
        self.calls.append((system, user))
        if not self.replies:
            raise RuntimeError("FakeModel script ran out of replies")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def build_body(model_name, system, user, reasoning_effort=None):
    body = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if reasoning_effort == "none":
        body["thinking"] = {"type": "disabled"}
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    return body


class Reply(str):
    def __new__(cls, content, usage=None, latency_ms=None):
        reply = str.__new__(cls, content)
        reply.usage = usage
        reply.latency_ms = latency_ms
        return reply


def parse_reply(raw):
    return json.loads(raw)["choices"][0]["message"]["content"]


def parse_usage(payload):
    usage = payload.get("usage") if isinstance(payload, dict) else None
    if not isinstance(usage, dict):
        return None
    details = {}
    pairs = (
        ("prompt_tokens", "input"),
        ("input_tokens", "input"),
        ("completion_tokens", "output"),
        ("output_tokens", "output"),
        ("total_tokens", "total"),
    )
    for source, name in pairs:
        value = usage.get(source)
        if isinstance(value, int) and not isinstance(value, bool):
            details.setdefault(name, value)
    for name in ("input_cost", "output_cost", "total_cost"):
        value = usage.get(name)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            details[name] = float(value)
    return details or None


def combine_calls(replies):
    usage = {}
    latency = 0
    saw_usage = False
    saw_latency = False
    for reply in replies:
        for key, value in (getattr(reply, "usage", None) or {}).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            usage[key] = usage.get(key, 0) + value
            saw_usage = True
        milliseconds = getattr(reply, "latency_ms", None)
        if isinstance(milliseconds, int):
            latency += milliseconds
            saw_latency = True
    return (usage or None) if saw_usage else None, latency if saw_latency else None


JSON_KEYS_ZH = {
    "候选": "candidates", "策略": "strategy", "理由": "reason", "语气": "tone", "长度": "length",
    "正文": "text", "选择": "picks", "评分": "scores", "序号": "candidate", "项目": "item",
    "分数": "value",
}


def _english_keys(value):
    if isinstance(value, dict):
        return {JSON_KEYS_ZH.get(k, k): _english_keys(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_english_keys(v) for v in value]
    return value


def parse_json(raw):
    try:
        return _english_keys(json.loads(raw[raw.index("{") : raw.rindex("}") + 1]))
    except (json.JSONDecodeError, ValueError):
        return None


class RejectedRequest(RuntimeError):
    pass


class GlmModel:
    def __init__(self, api_key, base_url, model_name, timeout=60, reasoning_effort=None):
        self._api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout
        self.reasoning_effort = reasoning_effort

    def __repr__(self):
        return f"GlmModel(base_url={self.base_url!r}, model_name={self.model_name!r})"

    def complete(self, system, user):
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(
                build_body(self.model_name, system, user, self.reasoning_effort)
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                latency_ms = int((time.perf_counter() - started) * 1000)
                try:
                    content = payload["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError):
                    content = None
                if not isinstance(content, str) or not content:
                    raise RuntimeError("GLM empty or unexpected reply")
                return Reply(content, parse_usage(payload), latency_ms)
        except urllib.error.HTTPError as error:
            try:
                body = error.read().decode("utf-8", errors="replace")[:500]
            finally:
                error.close()
            raise (RejectedRequest if error.code in (400, 401, 403, 404) else RuntimeError)(f"GLM {error.code}: {body}") from error


def complete_with_retries(model, system, user, sleep):
    delays = [2, 8]
    for attempt in range(3):
        try:
            return model.complete(system, user)
        except Exception as error:
            if attempt == 2 or isinstance(error, (TimeoutError, RejectedRequest)):
                raise
            sleep(delays[attempt])


def require_models(env):
    for name in ("GLM_API_KEY", "WRITER_MODEL", "JUDGE_MODEL"):
        if not env.get(name):
            raise SystemExit(f"Missing required setting: {name}")
    writer, judge = env["WRITER_MODEL"], env["JUDGE_MODEL"]
    if writer == judge:
        raise SystemExit("WRITER_MODEL and JUDGE_MODEL must be different models")
    return writer, judge
