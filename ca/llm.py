import json
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


def build_body(model_name, system, user):
    return {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }


def parse_reply(raw):
    return json.loads(raw)["choices"][0]["message"]["content"]


class GlmModel:
    def __init__(self, api_key, base_url, model_name):
        self._api_key = api_key
        self.base_url = base_url
        self.model_name = model_name

    def __repr__(self):
        return f"GlmModel(base_url={self.base_url!r}, model_name={self.model_name!r})"

    def complete(self, system, user):
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(build_body(self.model_name, system, user)).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return parse_reply(response.read().decode("utf-8"))


def complete_with_retries(model, system, user, sleep):
    delays = [0.5, 1.0]
    for attempt in range(3):
        try:
            return model.complete(system, user)
        except Exception:
            if attempt == 2:
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
