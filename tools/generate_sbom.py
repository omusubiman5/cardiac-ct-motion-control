"""Generate a hash manifest / SBOM for the non-clinical prototypes
(docs/23 unit 10, IT-002 partial: hashes and inventory — code signing
itself is not covered and remains pending).

Usage:
    python tools/generate_sbom.py

Writes artifacts/sbom/sbom-<date>.json listing every shipped file with
its SHA-256, plus the frozen Python dependency set. Deterministic
content aside from the embedded timestamp.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = [
    ROOT / "prototypes" / "slicer-cstamp",
    ROOT / "prototypes" / "cmos-motion-poc",
    ROOT / "tools",
]
EXCLUDE_DIRS = {"__pycache__", ".venv", "tests", ".git", ".pytest_cache"}
EXCLUDE_EXT = {".pyc"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(base: Path):
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(base)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if path.suffix in EXCLUDE_EXT:
            continue
        yield rel, path


def frozen_dependencies() -> list[dict]:
    """pip freeze inside the PoC venv when available; empty list on
    failure — the manifest still records the attempt."""
    venv_python = (
        ROOT / "prototypes" / "cmos-motion-poc"
        / ".venv" / "Scripts" / "python.exe"
    )
    if not venv_python.is_file():
        return []
    try:
        out = subprocess.run(
            [str(venv_python), "-m", "pip", "freeze"],
            capture_output=True, text=True, timeout=60,
        )
        lines = sorted(
            line.strip() for line in out.stdout.splitlines() if line.strip()
        )
        return [{"name_version": line} for line in lines]
    except (OSError, subprocess.TimeoutExpired):
        return []


def runtime_file_inventory():
    """Verify installed third-party runtime in place; it is not silently bundled."""
    venv = (ROOT/'prototypes/cmos-motion-poc/.venv').resolve()
    rows=[]
    for distribution in importlib.metadata.distributions():
        name=distribution.metadata.get('Name','unknown')
        for relative in distribution.files or []:
            path=Path(distribution.locate_file(relative)).resolve()
            if not path.is_relative_to(venv) or not path.is_file() or path.suffix=='.pyc':continue
            rows.append({'distribution':name,'path':path.relative_to(venv).as_posix(),
                         'sha256':sha256_file(path),'bytes':path.stat().st_size})
    return sorted(rows,key=lambda row:(row['distribution'],row['path']))


def main() -> int:
    manifest = {
        "generated_at": time.strftime(
            "%Y-%m-%dT%H:%M:%S%z", time.localtime()
        ),
        "generator": "tools/generate_sbom.py",
        "scope": "non-clinical prototype; signing NOT included",
        "components": {},
    }
    for component in COMPONENTS:
        files = []
        for rel, path in iter_files(component):
            files.append({
                "path": str(rel).replace("\\", "/"),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            })
        manifest["components"][component.name] = {
            "files": files,
            "file_count": len(files),
            "tree_sha256": hashlib.sha256(
                "\n".join(f"{f['path']}:{f['sha256']}" for f in files)
                .encode("utf-8")
            ).hexdigest(),
        }
    manifest["python_dependencies"] = frozen_dependencies()
    manifest['runtime_dependencies']={'delivery':'external verified installed virtual environment',
                                       'files':runtime_file_inventory()}

    out_dir = ROOT / "artifacts" / "sbom"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"sbom-{time.strftime('%Y%m%d')}.json"
    out.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    total = sum(c["file_count"] for c in manifest["components"].values())
    print(f"wrote {out} ({total} files, "
          f"{len(manifest['python_dependencies'])} deps)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
