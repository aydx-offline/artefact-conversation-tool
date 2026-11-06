import argparse
import csv
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ca.brand import load_brand
from ca.clients import load_clients, store_hash
from ca.judge import evaluate_case, evaluation_id
from ca.llm import GlmModel, require_models
from ca.pipeline import generate
from ca.schema import load_case
from ca.store import RunStore, test_set_version
from ca.telemetry import open_telemetry, publish_prompts
from ca.version import GENERATOR_VERSION, JUDGE_VERSION

DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
EXPORT_HEADER = [
    "Case ID",
    "Scenario",
    "Client information",
    "Conversation history",
    "Product information",
    "Output 1",
    "Output 2",
    "Output 3",
    "Generator version",
]
COMPARE_HEADER = [
    "Case ID",
    "Scenario",
    "Before 1",
    "Before 2",
    "Before 3",
    "After 1",
    "After 2",
    "After 3",
    "Before version",
    "After version",
]


def _env(root):
    values = {}
    path = root / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                values[name.strip()] = value.strip().strip("\"'")
    values.update(os.environ)
    return values


def _hash_path(path):
    digest = hashlib.sha256()
    paths = sorted(item for item in path.rglob("*") if item.is_file()) if path.is_dir() else [path]
    for item in paths:
        digest.update(item.read_bytes())
    return digest.hexdigest()


def _run_dir(root, run_id):
    matches = list((root / "runs").glob(f"*/{run_id}"))
    if len(matches) != 1:
        raise SystemExit(f"Run not found or ambiguous: {run_id}")
    return matches[0]


def read_manifest(run_dir):
    data = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    end = run_dir / "manifest.end.json"
    if end.exists():
        data.update(json.loads(end.read_text(encoding="utf-8")))
    return data


_manifest = read_manifest


def _case_file(case, result):
    return {
        "case": asdict(case),
        "resolved": result.resolved,
        "steps": [asdict(step) for step in result.steps],
        "candidates": result.candidates,
        "checks": [asdict(check) for check in result.checks],
        "status": result.status,
    }


def _manifest_start(root, cases, source, writer_model):
    client_path = root / "data" / "clients.json"
    clients = load_clients(client_path)
    inputs = root / "cases" / "inputs.jsonl"
    tuning = root / "cases" / "tuning.jsonl"
    if inputs.exists() and tuning.exists():
        used = {
            json.loads(line)["client_id"]
            for path in (inputs, tuning)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        version = test_set_version(inputs, tuning, [clients[client_id] for client_id in sorted(used)])
    else:
        source_data = source.read_bytes() if source else json.dumps(
            [asdict(case) for case in cases],
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        digest = hashlib.sha256(source_data)
        profiles = [clients[client_id] for client_id in sorted({case.client_id for case in cases})]
        digest.update(json.dumps(profiles, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        version = digest.hexdigest()
    return {
        "writer_model": writer_model,
        "brand_hash": _hash_path(root / "data" / "brand"),
        "client_store_hash": store_hash(client_path),
        "test_set_version": version,
        "split": _shared_split(cases),
        "case_ids": [case.case_id for case in cases],
    }


def _shared_split(cases):
    splits = {case.split or "single" for case in cases}
    if len(splits) != 1:
        raise SystemExit("Case file mixes splits")
    return splits.pop()


def _reject_duplicate_ids(cases):
    seen = set()
    for case in cases:
        if case.case_id in seen:
            raise SystemExit(f"Duplicate case_id: {case.case_id}")
        seen.add(case.case_id)


def _models(env, model, judge_model):
    if model is not None or judge_model is not None:
        return model, judge_model
    writer_name, judge_name = require_models(env)
    url = env.get("GLM_BASE_URL") or DEFAULT_BASE_URL
    return (
        GlmModel(env["GLM_API_KEY"], url, writer_name, _positive_int(env, "GLM_TIMEOUT", 60), env.get("WRITER_REASONING") or "none"),
        GlmModel(env["GLM_API_KEY"], url, judge_name, _positive_int(env, "JUDGE_TIMEOUT", 300), env.get("JUDGE_REASONING") or None),
    )


def _positive_int(env, name, default):
    try:
        value = int(env.get(name, default))
        if value < 1:
            raise ValueError
        return value
    except (TypeError, ValueError):
        raise SystemExit(f"{name} must be a positive integer") from None


def _workers(env):
    return _positive_int(env, "CA_WORKERS", 2)


def _publish(telemetry, brand):
    if telemetry.client is None:
        return
    try:
        publish_prompts(telemetry.client, brand)
    except Exception as error:
        print(f"Langfuse prompts: {error}")


def _record_cases(telemetry, store, run_id, cases, writer_model=None):
    for case in cases:
        path = store.run_dir(run_id) / "cases" / f"{case.case_id}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        telemetry.record_case_file(data, run_id, writer_model=writer_model)


def _finish(store, run_id, statuses):
    store.finish_manifest(
        run_id,
        {
            "end": datetime.now(timezone.utc).isoformat(),
            "case_statuses": statuses,
        },
    )


def _generate_one(case, model, brand, clients, store, run_id):
    try:
        result = generate(case, model, brand, clients, None)
        data = _case_file(case, result)
    except Exception as error:
        data = {
            "case": asdict(case),
            "resolved": {},
            "steps": [],
            "candidates": [],
            "checks": [],
            "status": "failed",
            "error": str(error),
        }
    status = data["status"]
    store.write_case(run_id, case.case_id, data)
    store.append(run_id, "events.jsonl", {"case_id": case.case_id, "status": status})
    return status


def run_cases(cases, model, brand, clients, store, run_id, cancel_check=lambda: False, on_status=None, workers=2):
    statuses = {}

    def work(case):
        if cancel_check():
            data = {
                "case": asdict(case),
                "resolved": {},
                "steps": [],
                "candidates": [],
                "checks": [],
                "status": "cancelled",
            }
            store.write_case(run_id, case.case_id, data)
            store.append(run_id, "events.jsonl", {"case_id": case.case_id, "status": "cancelled"})
            return "cancelled"
        if on_status:
            on_status(case.case_id, "running")
        return _generate_one(case, model, brand, clients, store, run_id)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, case): case.case_id for case in cases}
        for future in as_completed(futures):
            case_id = futures[future]
            statuses[case_id] = future.result()
            if on_status:
                on_status(case_id, statuses[case_id])
    return statuses


def _generate_command(args, root, env, model):
    case = load_case(Path(args.case))
    writer, _ = _models(env, model, None)
    brand = load_brand(root / "data" / "brand")
    clients = load_clients(root / "data" / "clients.json")
    store = RunStore(root / "runs")
    run_id = store.begin(_manifest_start(root, [case], Path(args.case), getattr(writer, "model_name", type(writer).__name__)))
    telemetry = open_telemetry(env)
    _publish(telemetry, brand)
    status = _generate_one(case, writer, brand, clients, store, run_id)
    _finish(store, run_id, {case.case_id: status})
    _record_cases(telemetry, store, run_id, [case], getattr(writer, "model_name", None))
    telemetry.flush()
    case_data = json.loads((store.run_dir(run_id) / "cases" / f"{case.case_id}.json").read_text(encoding="utf-8"))
    for candidate in case_data["candidates"]:
        print(candidate["text"])
    print(store.run_dir(run_id))
    return int(status == "failed")


def _batch_command(args, root, env, model):
    source = Path(args.cases) if args.cases else root / "cases" / "tuning.jsonl"
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    cases = [load_case(row) for row in rows]
    if not cases:
        raise SystemExit("Case file is empty")
    _reject_duplicate_ids(cases)
    _shared_split(cases)
    writer, _ = _models(env, model, None)
    brand = load_brand(root / "data" / "brand")
    clients = load_clients(root / "data" / "clients.json")
    store = RunStore(root / "runs")
    run_id = store.begin(_manifest_start(root, cases, source, getattr(writer, "model_name", type(writer).__name__)))
    telemetry = open_telemetry(env)
    _publish(telemetry, brand)
    statuses = run_cases(
        cases,
        writer,
        brand,
        clients,
        store,
        run_id,
        on_status=lambda case_id, status: print(case_id, status) if status != "running" else None,
        workers=_workers(env),
    )
    _finish(store, run_id, statuses)
    _record_cases(telemetry, store, run_id, cases, getattr(writer, "model_name", None))
    telemetry.flush()
    print(store.run_dir(run_id))
    return int(any(status == "failed" for status in statuses.values()))


def _evaluate_command(args, root, env, judge_model):
    run_dir = _run_dir(root, args.run)
    manifest = _manifest(run_dir)
    _, judge = _models(env, None, judge_model)
    brand = load_brand(root / "data" / "brand")
    store = RunStore(root / "runs", run_dir.parent.name)
    telemetry = open_telemetry(env)
    _publish(telemetry, brand)
    case_files = []
    for case_id in manifest["case_ids"]:
        path = run_dir / "cases" / f"{case_id}.json"
        if not path.exists():
            continue
        case_file = json.loads(path.read_text(encoding="utf-8"))
        if case_file.get("status") == "failed" or len(case_file.get("candidates", [])) < 3:
            print(case_id, "skipped")
            continue
        case_files.append(case_file)

    def judge_one(case_file):
        try:
            rows = evaluate_case(case_file, judge, brand)
            return rows, getattr(rows, "call", None)
        except Exception as error:
            row = {
                "evaluation_id": evaluation_id(),
                "judge_model": getattr(judge, "model_name", type(judge).__name__),
                "judge_version": JUDGE_VERSION,
                "case_id": case_file["case"]["case_id"],
                "status": "failed",
                "reason": str(error),
            }
            if hasattr(error, "raw"):
                row["raw"] = error.raw
            return [row], getattr(error, "call", None)

    with ThreadPoolExecutor(max_workers=_workers(env)) as pool:
        judged = list(pool.map(judge_one, case_files))
    for case_file, (rows, judge_call) in zip(case_files, judged):
        for row in rows:
            store.append(args.run, "scores.jsonl", row)
        telemetry.record_case_file(
            case_file,
            args.run,
            scores=rows,
            writer_model=manifest.get("writer_model"),
            judge_call=judge_call,
        )
    telemetry.flush()
    return 0


def _values(value):
    if isinstance(value, dict):
        return [item for key, item in value.items() if key != "id" and not key.endswith("_id")]
    if isinstance(value, list):
        return value
    return [value]


def _readable(value):
    if not value:
        return ""
    if isinstance(value, list):
        return "；".join(filter(None, (_readable(item) for item in value)))
    if isinstance(value, dict):
        ordered = []
        if value.get("name"):
            ordered.append(value["name"])
        ordered.extend(item for item in _values(value) if item != value.get("name"))
        return "，".join(filter(None, (_readable(item) for item in ordered)))
    return str(value)


def _candidate_texts(case_file):
    return [item.get("text", "") for item in case_file.get("candidates", [])]


def _history_text(history):
    labels = {"client": "顾客", "ca": "顾问"}
    return "；".join(
        f"{labels.get(message.get('sender'), '对话')}：{message.get('text', '')}"
        for message in history or []
    )


def _export_run(args, root):
    run_dir = _run_dir(root, args.run)
    manifest = _manifest(run_dir)
    if manifest.get("split") == "tuning":
        raise SystemExit("Refusing to export a tuning run")
    rows = []
    for case_id in manifest["case_ids"]:
        case_file = json.loads((run_dir / "cases" / f"{case_id}.json").read_text(encoding="utf-8"))
        texts = _candidate_texts(case_file)
        texts = (texts + ["", "", ""])[:3]
        resolved = case_file["resolved"]
        rows.append(
            [
                case_id,
                case_file["case"]["scenario"],
                _readable(resolved.get("client")),
                _history_text(resolved.get("history")),
                _readable(resolved.get("products")),
                *texts,
                manifest["generator_version"],
            ]
        )
    _write_csv(root / "cases" / "cases.csv", EXPORT_HEADER, rows)
    return 0


def _export_comparison(args, root):
    before_dir = _run_dir(root, args.before)
    after_dir = _run_dir(root, args.after)
    before_manifest = _manifest(before_dir)
    after_manifest = _manifest(after_dir)
    rows = []
    common = [case_id for case_id in before_manifest["case_ids"] if case_id in after_manifest["case_ids"]]
    for case_id in common:
        before = json.loads((before_dir / "cases" / f"{case_id}.json").read_text(encoding="utf-8"))
        after = json.loads((after_dir / "cases" / f"{case_id}.json").read_text(encoding="utf-8"))
        before_texts, after_texts = _candidate_texts(before), _candidate_texts(after)
        if len(before_texts) == len(after_texts) == 3 and before_texts != after_texts:
            rows.append(
                [
                    case_id,
                    after["case"]["scenario"],
                    *before_texts,
                    *after_texts,
                    before_manifest["generator_version"],
                    after_manifest["generator_version"],
                ]
            )
    _write_csv(root / "cases" / "before-after.csv", COMPARE_HEADER, rows)
    return 0


def _write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def _parser():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    generate_parser = commands.add_parser("generate")
    generate_parser.add_argument("--case", required=True)
    batch_parser = commands.add_parser("batch")
    batch_parser.add_argument("--cases")
    evaluate_parser = commands.add_parser("evaluate")
    evaluate_parser.add_argument("--run", required=True)
    export_parser = commands.add_parser("export")
    choice = export_parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--run")
    choice.add_argument("--before")
    export_parser.add_argument("--after")
    return parser


def main(argv=None, *, model=None, judge_model=None, root=None):
    args = _parser().parse_args(argv)
    root = Path.cwd() if root is None else Path(root)
    env = _env(root)
    if args.command == "generate":
        return _generate_command(args, root, env, model)
    if args.command == "batch":
        return _batch_command(args, root, env, model)
    if args.command == "evaluate":
        return _evaluate_command(args, root, env, judge_model or model)
    if args.before:
        if not args.after:
            raise SystemExit("--before requires --after")
        return _export_comparison(args, root)
    return _export_run(args, root)


if __name__ == "__main__":
    raise SystemExit(main())
