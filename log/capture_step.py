import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "log" / "screenshots"
NAME = re.compile(r"step-\d{2}-[a-z0-9-]+")

SWIFT = r"""
import CoreGraphics
let opts = CGWindowListOption(arrayLiteral: .optionOnScreenOnly, .excludeDesktopElements)
guard let list = CGWindowListCopyWindowInfo(opts, kCGNullWindowID) as? [[String: Any]] else {
    fputs("no window list\n", stderr)
    exit(1)
}
var bestId = 0
for item in list {
    let owner = item["kCGWindowOwnerName"] as? String ?? ""
    let layer = item["kCGWindowLayer"] as? Int ?? 0
    if owner != "Cursor" || layer != 0 { continue }
    bestId = item["kCGWindowNumber"] as? Int ?? 0
    break
}
if bestId == 0 {
    fputs("Cursor window not found\n", stderr)
    exit(2)
}
print(bestId)
"""


def destination(name: str) -> Path:
    if NAME.fullmatch(name) is None:
        raise SystemExit(f"name must look like step-05-spec-revision, got {name}")
    return SHOTS / f"{name}.png"


def refuse_overwrite(path: Path) -> None:
    if path.exists():
        raise SystemExit(f"screenshot already exists: {path}")


def cursor_window_id() -> str:
    handle = tempfile.NamedTemporaryFile("w", suffix=".swift", delete=False)
    handle.write(SWIFT)
    handle.close()
    try:
        result = subprocess.run(
            ["swift", handle.name],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        Path(handle.name).unlink(missing_ok=True)
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        message = detail[-1] if detail else "could not find the Cursor window"
        raise SystemExit(message)
    window_id = result.stdout.strip()
    if not window_id:
        raise SystemExit("could not find the Cursor window")
    return window_id


def capture(path: Path) -> None:
    window_id = cursor_window_id()
    result = subprocess.run(
        ["screencapture", "-l", window_id, "-o", "-x", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    data = path.read_bytes() if path.exists() else b""
    if result.returncode != 0 or data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 10_000:
        path.unlink(missing_ok=True)
        detail = (result.stderr or result.stdout).strip()
        hint = "Enable Screen Recording for Cursor in System Settings, then run this script again."
        raise SystemExit(detail or hint)


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        raise SystemExit("usage: python3 log/capture_step.py step-NN-short-name")
    path = destination(argv[1])
    refuse_overwrite(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    capture(path)
    print(path.relative_to(ROOT))


if __name__ == "__main__":
    main(sys.argv)
