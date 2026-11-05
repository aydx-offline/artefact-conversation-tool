import hashlib
import json
import os
import tempfile
from pathlib import Path

from ca.schema import CaseError, prose_is_chinese

ALLOWED_NAMES = ("Chengbai",)
PROSE_FIELDS = ("name", "tier", "relationship", "preferences")


def _canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _check(client):
    if client.get("address") not in ("您", "你"):
        raise CaseError("address", "must be 您 or 你")
    for name in PROSE_FIELDS:
        if not prose_is_chinese(client.get(name, ""), ALLOWED_NAMES):
            raise CaseError(name, f"must be Chinese: {client[name]!r}")
    for message in client.get("history", []):
        if not prose_is_chinese(message.get("text", ""), ALLOWED_NAMES):
            raise CaseError("history", f"text must be Chinese: {message['text']!r}")


def load_clients(path):
    clients = json.loads(Path(path).read_text(encoding="utf-8"))
    for client in clients.values():
        _check(client)
    return clients


def save_client(path, client):
    _check(client)
    clients = load_clients(path)
    clients[client["id"]] = client
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(_canonical(clients))
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def store_hash(path):
    clients = json.loads(Path(path).read_text(encoding="utf-8"))
    return hashlib.sha256(_canonical(clients).encode("utf-8")).hexdigest()
