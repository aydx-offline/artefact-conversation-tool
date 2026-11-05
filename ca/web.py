import argparse
import json
import os
import threading
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote, urlsplit

from ca.brand import load_brand
from ca.chat import extract_case
from ca.cli import (
    _case_file,
    _env,
    _finish,
    _manifest_start,
    _models,
    _workers,
    read_manifest,
    run_cases,
)
from ca.clients import ALLOWED_NAMES, load_clients, save_client
from ca.context import resolve_context
from ca.pipeline import generate
from ca.schema import CaseError, load_case, validate_case
from ca.store import RunStore
from ca.telemetry import open_telemetry

MAX_BODY_SIZE = 1024 * 1024
CLIENTS_LOCK = threading.Lock()


def _get(deps, name, default=None):
    return deps.get(name, default) if isinstance(deps, dict) else getattr(deps, name, default)


def _set(deps, name, value):
    if isinstance(deps, dict):
        deps[name] = value
    else:
        setattr(deps, name, value)


def _json_body(body):
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8")
    if isinstance(body, str):
        body = json.loads(body)
    if not isinstance(body, dict):
        raise ValueError("请求正文必须是 JSON 对象")
    return body


def _safe(value):
    return (
        bool(value)
        and value not in (".", "..")
        and not any(char in value for char in "/\\*?[")
    )


def _request_guard(method, headers, port, length=0):
    headers = {name.lower(): value for name, value in headers.items()}
    try:
        length = int(headers.get("content-length", length))
    except (TypeError, ValueError):
        return 400, {"error": "Content-Length 必须是非负整数"}
    if length < 0:
        return 400, {"error": "Content-Length 必须是非负整数"}
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    if headers.get("host") not in allowed_hosts:
        return 403, {"error": "请求来源无效"}
    if method not in ("POST", "PUT"):
        return None
    if length > MAX_BODY_SIZE:
        return 413, {"error": "请求正文过大"}
    if headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        return 415, {"error": "Content-Type 必须是 application/json"}
    origin = headers.get("origin")
    if origin and origin not in {f"http://{host}" for host in allowed_hosts}:
        return 403, {"error": "请求来源无效"}
    return None


def _root(deps):
    return Path(_get(deps, "root", Path.cwd()))


def _clients_path(deps):
    return Path(_get(deps, "clients_path", _root(deps) / "data" / "clients.json"))


def _model(deps):
    model = _get(deps, "model")
    if model is None:
        raise RuntimeError(_get(deps, "model_error", "缺少写作模型或 GLM 配置"))
    return model


def _run_location(root, run_id):
    matches = list((root / "runs").glob(f"*/{run_id}"))
    return matches[0] if len(matches) == 1 else None


def _confirm_case(case, brand, clients):
    validate_case(case, allowed_names=ALLOWED_NAMES)
    if case.client_id not in clients:
        raise CaseError("client_id", "unknown client")
    if (case.scenario == "2 Product recommendation" or case.scenario.startswith("6")) and not case.product_ids:
        raise CaseError("product_ids", "this scenario needs product_ids")
    if case.scenario == "5 Event invitation" and not case.event_id:
        raise CaseError("event_id", "scenario 5 needs event_id")
    if case.scenario == "1 Birthday and festive greetings":
        context = resolve_context(case.timestamp, clients[case.client_id], brand.festivals, case.occasion)
        if not context.occasion:
            raise CaseError("occasion", "scenario 1 needs an occasion")


class BatchState:
    def __init__(self):
        self.lock = threading.Lock()
        self.cancel = threading.Event()
        self.finished = threading.Event()
        self.running = False
        self.run_id = ""
        self.rows = []
        self.error = ""

    def update(self, case_id, status):
        with self.lock:
            for row in self.rows:
                if row["case_id"] == case_id:
                    row["status"] = status
                    break


def _batch_state(deps):
    state = _get(deps, "batch_state")
    if state is None:
        state = BatchState()
        _set(deps, "batch_state", state)
    return state


def _run_batch(deps, state, cases, source, model):
    root = _root(deps)
    store = RunStore(root / "runs")
    try:
        clients = load_clients(_clients_path(deps))
        brand = _get(deps, "brand") or load_brand(root / "data" / "brand")
        runner = _get(deps, "run_cases", run_cases)
        args = (cases, model, brand, clients, store, state.run_id, state.cancel.is_set, state.update)
        statuses = runner(*args, workers=_get(deps, "workers", 2)) if runner is run_cases else runner(*args)
        _finish(store, state.run_id, statuses)
        telemetry = _get(deps, "telemetry")
        if telemetry:
            telemetry.flush()
    except Exception as error:
        with state.lock:
            state.error = str(error)
            for row in state.rows:
                if row["status"] not in ("done", "failed", "failed_checks", "cancelled"):
                    row["status"] = "failed"
            statuses = {row["case_id"]: row["status"] for row in state.rows}
        try:
            _finish(store, state.run_id, statuses)
        except Exception:
            pass
    finally:
        with state.lock:
            state.running = False
        state.finished.set()


def _start_batch(body, deps):
    split = body.get("split")
    if split not in ("tuning", "final"):
        return 400, {"error": "split 必须是 tuning 或 final"}
    state = _batch_state(deps)
    with state.lock:
        if state.running:
            return 409, {"error": "已有批次正在运行"}
        source = _root(deps) / "cases" / ("tuning.jsonl" if split == "tuning" else "inputs.jsonl")
        if not source.exists():
            return 400, {"error": f"缺少批次文件：{source.name}"}
        try:
            rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
            cases = [load_case(row) for row in rows]
            model = _model(deps)
        except (json.JSONDecodeError, TypeError, CaseError, RuntimeError) as error:
            return 503 if isinstance(error, RuntimeError) else 400, {"error": str(error)}
        if not cases:
            return 400, {"error": "批次文件为空"}
        brand = _get(deps, "brand") or load_brand(_root(deps) / "data" / "brand")
        store = RunStore(_root(deps) / "runs")
        run_id = store.begin(
            _manifest_start(
                _root(deps),
                cases,
                source,
                getattr(model, "model_name", type(model).__name__),
            )
        )
        state.cancel.clear()
        state.finished.clear()
        state.running = True
        state.run_id = run_id
        state.error = ""
        state.rows = [{"case_id": case.case_id, "status": "queued"} for case in cases]
    threading.Thread(target=_run_batch, args=(deps, state, cases, source, model), daemon=True).start()
    return 202, {"run_id": run_id, "rows": list(state.rows)}


def _list_runs(root):
    groups = []
    flat = []
    runs_root = root / "runs"
    if runs_root.exists():
        for version_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
            runs = []
            for run_dir in sorted((path for path in version_dir.iterdir() if path.is_dir()), reverse=True):
                try:
                    manifest = read_manifest(run_dir)
                except (FileNotFoundError, json.JSONDecodeError):
                    continue
                item = {"run_id": run_dir.name, "version": version_dir.name, **manifest}
                runs.append(item)
                flat.append(item)
            groups.append({"version": version_dir.name, "runs": runs})
    comparisons = []
    for index, left in enumerate(flat):
        for right in flat[index + 1 :]:
            flags = [
                key
                for key in ("client_store_hash", "test_set_version")
                if left.get(key) != right.get(key)
            ]
            comparisons.append({"left": left["run_id"], "right": right["run_id"], "flags": flags})
    return {"versions": groups, "comparisons": comparisons}


def _trace(root, version, run_id, case_id):
    if not all(_safe(value) for value in (version, run_id, case_id)):
        return 400, {"error": "路径参数无效"}
    run_dir = root / "runs" / version / run_id
    path = run_dir / "cases" / f"{case_id}.json"
    if not path.is_file():
        return 404, {"error": "未找到运行或案例"}
    data = json.loads(path.read_text(encoding="utf-8"))
    scores_path = run_dir / "scores.jsonl"
    scores = []
    if scores_path.exists():
        scores = [
            row
            for line in scores_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and (row := json.loads(line)).get("case_id") == case_id
        ]
    steps = data.get("steps", [])
    return 200, {
        **data,
        "steps": steps,
        "prompts": [step.get("prompt", "") for step in steps if step.get("prompt")],
        "raw": [step.get("raw", "") for step in steps if step.get("raw")],
        "checks": data.get("checks", []),
        "scores": scores,
    }


def _feedback(body, deps):
    required = (
        "run_id",
        "case_id",
        "candidate",
        "strategy",
        "tone",
        "original_text",
        "copied_text",
        "edited",
        "time",
    )
    missing = next((name for name in required if name not in body), None)
    if missing:
        return 400, {"error": f"{missing}: 必填"}
    if not all(_safe(str(body[name])) for name in ("run_id", "case_id")):
        return 400, {"error": "路径参数无效"}
    run_dir = _run_location(_root(deps), body["run_id"])
    if run_dir is None or not (run_dir / "cases" / f"{body['case_id']}.json").exists():
        return 404, {"error": "未找到运行或案例"}
    client = None
    if body.get("action") == "copy":
        client_id = body.get("client_id")
        if not _safe(str(client_id)):
            return 400, {"error": "client_id: 必填"}
        clients = load_clients(_clients_path(deps))
        if client_id not in clients:
            return 404, {"error": "未找到客户"}
        client = clients[client_id]
    row = {name: body[name] for name in required}
    RunStore(_root(deps) / "runs", run_dir.parent.name).append(body["run_id"], "feedback.jsonl", row)
    if client is not None:
        with CLIENTS_LOCK:
            clients = load_clients(_clients_path(deps))
            client = clients[body["client_id"]]
            client.setdefault("history", []).append(
                {"sender": "ca", "text": body["copied_text"], "time": body["time"]}
            )
            save_client(_clients_path(deps), client)
    return 200, {"feedback": row}


def handle(method, path, body, deps, headers=None):
    try:
        if headers is not None:
            guard = _request_guard(
                method,
                headers,
                _get(deps, "port", 8765),
                len(body) if isinstance(body, (bytes, bytearray)) else 0,
            )
            if guard:
                return guard
        raw_path = urlsplit(path).path
        if "%2f" in raw_path.lower() or "%5c" in raw_path.lower():
            return 400, {"error": "路径参数无效"}
        route = unquote(raw_path)
        parts = [part for part in route.split("/") if part]
        if method in ("POST", "PUT"):
            body = _json_body(body)

        if method == "GET" and route == "/":
            html = (_root(deps) / "web" / "index.html").read_text(encoding="utf-8")
            return 200, {"content_type": "text/html; charset=utf-8", "body": html}

        if route == "/api/clients" and method == "GET":
            return 200, {"clients": load_clients(_clients_path(deps))}
        if route == "/api/clients" and method == "POST":
            if not _safe(str(body.get("id", ""))):
                return 400, {"error": "id: 必填或无效"}
            with CLIENTS_LOCK:
                if body["id"] in load_clients(_clients_path(deps)):
                    return 409, {"error": "客户已存在"}
                save_client(_clients_path(deps), body)
            return 201, {"client": body}
        if route.startswith("/api/clients/") and method == "PUT":
            if len(parts) != 3 or not _safe(parts[2]):
                return 400, {"error": "id: 路径参数无效"}
            client = {**body, "id": parts[2]}
            with CLIENTS_LOCK:
                save_client(_clients_path(deps), client)
            return 200, {"client": client}

        if route == "/api/chat" and method == "POST":
            request = body.get("request")
            if not isinstance(request, str) or not request:
                return 400, {"error": "request: 必填"}
            clients = load_clients(_clients_path(deps))
            now = datetime.now(timezone(timedelta(hours=8))).isoformat()
            case = extract_case(request, _model(deps), clients, now)
            if isinstance(case, str):
                return 404, {"error": case}
            case_data = asdict(case)
            stored = clients[case.client_id].get("history", [])
            case_data["history"] = [*stored, *(case_data["history"] or [])]
            return 200, {"case": case_data}

        if route == "/api/generate" and method == "POST":
            product_ids = body.get("product_ids", [])
            if not isinstance(product_ids, list) or not all(isinstance(item, str) for item in product_ids):
                return 400, {"error": "product_ids: 每项必须是字符串"}
            case = load_case(body)
            brand = _get(deps, "brand") or load_brand(_root(deps) / "data" / "brand")
            clients = load_clients(_clients_path(deps))
            _confirm_case(case, brand, clients)
            model = _model(deps)
            result = generate(case, model, brand, clients, None)
            store = RunStore(_root(deps) / "runs")
            run_id = store.begin(
                _manifest_start(
                    _root(deps),
                    [case],
                    None,
                    getattr(model, "model_name", type(model).__name__),
                )
            )
            store.write_case(run_id, case.case_id, _case_file(case, result))
            _finish(store, run_id, {case.case_id: result.status})
            telemetry = _get(deps, "telemetry")
            if telemetry:
                telemetry.trace_case(case.case_id, input=asdict(case))
                telemetry.flush()
            return 200, {
                "run_id": run_id,
                "case_id": case.case_id,
                "status": result.status,
                "candidates": result.candidates,
                "steps": [asdict(step) for step in result.steps],
                "checks": [asdict(check) for check in result.checks],
            }

        if route == "/api/feedback" and method == "POST":
            return _feedback(body, deps)
        if route == "/api/runs" and method == "GET":
            return 200, _list_runs(_root(deps))
        if method == "GET" and len(parts) == 6 and parts[:2] == ["api", "runs"] and parts[4] == "cases":
            return _trace(_root(deps), parts[2], parts[3], parts[5])
        if route.startswith("/api/runs/") and method == "GET":
            if any(part in (".", "..") for part in parts):
                return 400, {"error": "路径参数无效"}
            return 404, {"error": "未找到运行或案例"}

        if route == "/api/batch" and method == "POST":
            return _start_batch(body, deps)
        if route == "/api/batch/stop" and method == "POST":
            state = _batch_state(deps)
            if not state.running:
                return 409, {"error": "没有运行中的批次"}
            state.cancel.set()
            return 200, {"status": "stopping"}
        if route == "/api/batch" and method == "GET":
            state = _batch_state(deps)
            with state.lock:
                return 200, {
                    "running": state.running,
                    "run_id": state.run_id,
                    "rows": list(state.rows),
                    "error": state.error,
                }
        return 404, {"error": "未找到路由"}
    except json.JSONDecodeError:
        return 400, {"error": "请求正文不是有效 JSON"}
    except (CaseError, TypeError, ValueError, KeyError) as error:
        return 400, {"error": str(error)}
    except RuntimeError as error:
        message = str(error)
        settings = {"GLM_API_KEY", "WRITER_MODEL", "JUDGE_MODEL"}
        if message not in {f"Missing required setting: {name}" for name in settings} and any(
            word in message.lower() for word in ("key", "secret", "token")
        ):
            message = message.split(":", 1)[0].strip() or "模型配置不可用"
        return 503, {"error": message}
    except Exception:
        return 500, {"error": "服务器内部错误"}


class Handler(BaseHTTPRequestHandler):
    deps = None

    def _serve(self):
        length = self.headers.get("Content-Length", "0")
        guard = _request_guard(self.command, self.headers, self.server.server_port, length)
        if guard:
            status, payload = guard
        else:
            length = int(length)
            body = self.rfile.read(length) if length else None
            status, payload = handle(
                self.command,
                self.path,
                body,
                self.deps,
                headers=self.headers,
            )
        content_type = payload.get("content_type", "application/json; charset=utf-8")
        data = (
            payload["body"].encode("utf-8")
            if content_type.startswith("text/html")
            else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        )
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if status == 413:
            self.close_connection = True
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)

    do_GET = _serve
    do_POST = _serve
    do_PUT = _serve

    def log_message(self, format, *args):
        return


def _server_args(argv=None, env=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("port", nargs="?", type=int, default=8765)
    parser.add_argument("--host", default=(env or os.environ).get("CA_WEB_HOST", "127.0.0.1"))
    return parser.parse_args(argv)


def main(argv=None):
    root = Path.cwd()
    env = _env(root)
    args = _server_args(argv, env)
    model = None
    model_error = ""
    try:
        model, _ = _models(env, None, None)
    except SystemExit as error:
        model_error = str(error)
    Handler.deps = SimpleNamespace(
        root=root,
        clients_path=root / "data" / "clients.json",
        brand=load_brand(root / "data" / "brand"),
        model=model,
        model_error=model_error,
        telemetry=open_telemetry(env),
        batch_state=BatchState(),
        port=args.port,
        workers=_workers(env),
    )
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
