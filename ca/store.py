import hashlib
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ca.clients import _canonical
from ca.version import GENERATOR_VERSION

APPEND_FILES = {"events.jsonl", "scores.jsonl"}


def _run_id(instant):
    return instant.strftime("%Y%m%dT%H%M%S") + f"{instant.microsecond // 1000:03d}Z"


def _write_once(path, obj):
    with path.open("x", encoding="utf-8") as file:
        file.write(_canonical(obj))


class RunStore:
    def __init__(self, root: Path, version=GENERATOR_VERSION):
        self.root = Path(root)
        self.version = version
        self._locks = {}
        self._locks_guard = threading.Lock()

    def run_dir(self, run_id):
        return self.root / self.version / run_id

    def _lock(self, run_id):
        with self._locks_guard:
            return self._locks.setdefault(run_id, threading.Lock())

    def begin(self, manifest: dict) -> str:
        parent = self.root / self.version
        parent.mkdir(parents=True, exist_ok=True)
        started = datetime.now(timezone.utc)
        instant = started
        while True:
            run_id = _run_id(instant)
            run_dir = self.run_dir(run_id)
            try:
                run_dir.mkdir()
                break
            except FileExistsError:
                instant += timedelta(milliseconds=1)

        data = dict(manifest)
        data.pop("end", None)
        data["generator_version"] = GENERATOR_VERSION
        data["start"] = started.isoformat()
        _write_once(run_dir / "manifest.json", data)
        self._lock(run_id)
        return run_id

    def append(self, run_id, filename, obj) -> None:
        if filename not in APPEND_FILES:
            raise ValueError(f"not an append-only run file: {filename}")
        path = self.run_dir(run_id) / filename
        with self._lock(run_id), path.open("a", encoding="utf-8") as file:
            file.write(_canonical(obj) + "\n")

    def write_case(self, run_id, case_id, obj) -> None:
        cases = self.run_dir(run_id) / "cases"
        cases.mkdir(exist_ok=True)
        _write_once(cases / f"{case_id}.json", obj)

    def finish_manifest(self, run_id, manifest) -> None:
        _write_once(self.run_dir(run_id) / "manifest.end.json", manifest)


def test_set_version(inputs: Path, tuning: Path, profiles: list[dict]) -> str:
    digest = hashlib.sha256()
    for data in (
        Path(inputs).read_bytes(),
        Path(tuning).read_bytes(),
        _canonical(profiles).encode("utf-8"),
    ):
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()
