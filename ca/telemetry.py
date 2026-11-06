from ca.version import GENERATOR_VERSION

from ca.prompts import managed_prompts

DATASETS = {"tuning", "final"}
MODEL_STEPS = {"plan", "write"}
_off_printed = False


class Telemetry:
    def __init__(self, client=None):
        self.client = client

    def trace_case(self, name, **kwargs):
        if self.client is None:
            return None
        return self.client.start_observation(name=name, **kwargs)

    def record_case(self, name, case_input, output):
        observation = self.trace_case(name, input=case_input)
        if observation is None:
            return None
        update = getattr(observation, "update", None)
        end = getattr(observation, "end", None)
        if callable(update):
            update(output=output)
        if callable(end):
            end()
        return observation

    def record_case_file(self, case_file, run_id, scores=None, writer_model=None, judge_call=None):
        if self.client is None:
            return None
        case = case_file.get("case") or {}
        resolved = case_file.get("resolved") or {}
        candidates = case_file.get("candidates") or []
        calls = [
            step
            for step in case_file.get("steps") or []
            if step.get("name") in MODEL_STEPS and (step.get("prompt") or step.get("raw"))
        ]
        if judge_call:
            calls.append(judge_call)
        usage, latency = _totals(calls)
        root = self.client.start_observation(
            name=case.get("case_id", ""),
            input={
                "case_id": case.get("case_id"),
                "scenario": case.get("scenario") or resolved.get("scenario"),
                "run_id": run_id,
                "client": resolved.get("client"),
                "occasion": resolved.get("occasion"),
                "tone": resolved.get("tone"),
                "length": resolved.get("length"),
                "products": resolved.get("products"),
                "event": resolved.get("event"),
                "history": resolved.get("history"),
                "expectations": resolved.get("expectations"),
            },
            output={
                "status": case_file.get("status"),
                "texts": [item.get("text", "") for item in candidates],
                "plan": [
                    {
                        "strategy": item.get("strategy"),
                        "reason": item.get("reason"),
                        "tone": item.get("tone"),
                        "length": item.get("length"),
                    }
                    for item in candidates
                ],
                "checks": case_file.get("checks") or [],
            },
            metadata={
                "run_id": run_id,
                "writer_model": writer_model,
                "usage": usage,
                "latency_ms": latency,
            },
        )
        context = _trace_context(root)
        for step in calls:
            if step is judge_call:
                name, model = "judge", judge_call.get("model")
            else:
                name, model = step.get("name"), writer_model
            child = self.client.start_observation(
                name=name,
                as_type="generation",
                trace_context=context,
                input=step.get("prompt"),
                output=step.get("raw"),
                model=model,
                usage_details=_tokens(step.get("usage")),
                cost_details=_costs(step.get("usage")),
                metadata={"latency_ms": step.get("latency_ms")},
            )
            end = getattr(child, "end", None)
            if callable(end):
                end()
        trace_id = getattr(root, "trace_id", None)
        for check in case_file.get("checks") or []:
            self.score(
                name=f"check:{check.get('name')}",
                value=1.0 if check.get("passed") else 0.0,
                trace_id=trace_id,
                data_type="NUMERIC",
                comment=(check.get("reason") or "")[:500],
            )
        for row in scores or []:
            if row.get("candidate") is None or "item" not in row:
                continue
            self.score(
                name=row["item"],
                value=_score_value(row.get("value")),
                trace_id=trace_id,
                data_type="NUMERIC",
                comment=(row.get("reason") or "")[:500],
                metadata={"candidate": row["candidate"], "judge_model": row.get("judge_model")},
            )
        end = getattr(root, "end", None)
        if callable(end):
            end()
        return root

    def score(self, *args, **kwargs):
        if self.client is not None:
            return self.client.create_score(*args, **kwargs)
        return None

    def dataset_run(self, split, run_id, input, task):
        if split not in DATASETS:
            raise ValueError("dataset must be tuning or final")
        if self.client is None:
            return None
        self.client.create_dataset(name=split)
        item = self.client.create_dataset_item(dataset_name=split, input=input)
        return self.client.run_experiment(
            name=split,
            run_name=f"{GENERATOR_VERSION}:{run_id}",
            data=[item],
            task=task,
        )

    def flush(self):
        if self.client is not None:
            return self.client.flush()
        return None


def _tokens(usage):
    if not usage:
        return None
    tokens = {key: usage[key] for key in ("input", "output", "total") if key in usage}
    return tokens or None


def _costs(usage):
    if not usage:
        return None
    costs = {}
    for source, name in (("input_cost", "input"), ("output_cost", "output"), ("total_cost", "total")):
        if source in usage:
            costs[name] = usage[source]
    return costs or None


def _totals(calls):
    usage = {}
    latency = 0
    saw_usage = False
    saw_latency = False
    for call in calls:
        for key, value in (call.get("usage") or {}).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            usage[key] = usage.get(key, 0) + value
            saw_usage = True
        milliseconds = call.get("latency_ms")
        if isinstance(milliseconds, int):
            latency += milliseconds
            saw_latency = True
    return (usage or None) if saw_usage else None, latency if saw_latency else None


def _trace_context(observation):
    trace_id = getattr(observation, "trace_id", None)
    if not trace_id:
        return None
    context = {"trace_id": trace_id}
    parent = getattr(observation, "id", None)
    if parent:
        context["parent_span_id"] = parent
    return context


def _score_value(value):
    if value == "pass":
        return 1.0
    if value == "fail":
        return 0.0
    return float(value)


def _langfuse_client(env):
    from langfuse import Langfuse

    settings = {
        "public_key": env["LANGFUSE_PUBLIC_KEY"],
        "secret_key": env["LANGFUSE_SECRET_KEY"],
    }
    if env.get("LANGFUSE_HOST"):
        settings["host"] = env["LANGFUSE_HOST"]
    return Langfuse(**settings)


def _off():
    global _off_printed
    if not _off_printed:
        print("Langfuse off")
        _off_printed = True
    return Telemetry()


def _same_prompt(current, messages):
    prompt = getattr(current, "prompt", None)
    if not isinstance(prompt, list) or len(prompt) != len(messages):
        return False
    for item, wanted in zip(prompt, messages):
        if isinstance(item, dict):
            role, content = item.get("role"), item.get("content")
        else:
            role, content = getattr(item, "role", None), getattr(item, "content", None)
        if role != wanted["role"] or content != wanted["content"]:
            return False
    return True


def publish_prompts(client, brand):
    if client is None:
        return []
    created = []
    for item in managed_prompts(brand):
        try:
            current = client.get_prompt(item["name"], label="production")
        except Exception:
            current = None
        if current is not None and _same_prompt(current, item["prompt"]):
            continue
        client.create_prompt(
            name=item["name"],
            type="chat",
            prompt=item["prompt"],
            labels=["production"],
            commit_message="Update CA prompt",
        )
        created.append(item["name"])
    return created


def open_telemetry(env) -> Telemetry:
    if not env.get("LANGFUSE_PUBLIC_KEY") or not env.get("LANGFUSE_SECRET_KEY"):
        return _off()
    try:
        return Telemetry(_langfuse_client(env))
    except ImportError:
        return _off()
