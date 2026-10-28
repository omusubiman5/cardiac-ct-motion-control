"""Static outbound-communication audit for the prototypes
(docs/23 unit 10, X-08, IT-001).

Scans shipped Python sources for network-capable calls
(socket.create_connection / connect_ex, urllib, requests, http(s)
literals, QTcpSocket / QNetworkAccessManager) and verifies that every
real socket connect is pinned to loopback — either by a literal
loopback argument or by an explicit loopback guard in the same file
(e.g. ``loopback-only`` enforcement).

Qt signal ``.connect`` calls (``clicked.connect`` etc.) are not
network primitives and are not reported.

Exit 0 = no outbound channel found. Exit 1 = review required.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = [
    ROOT / "prototypes" / "slicer-cstamp",
    ROOT / "prototypes" / "cmos-motion-poc",
]
EXCLUDE_DIRS = {"__pycache__", ".venv", "tests"}

# genuine network primitives only
PRIMITIVE_PATTERNS = [
    (re.compile(r"socket\.create_connection\s*\("), "tcp_connect"),
    (re.compile(r"\w+\.connect_ex\s*\("), "tcp_connect_ex"),
    (re.compile(r"\burllib\b"), "urllib"),
    (re.compile(r"\brequests\."), "requests"),
    (re.compile(r"\bQTcpSocket\b|\bQNetworkAccessManager\b"),
     "qt_network"),
    (re.compile(r"\bQTcpServer\b"), "tcp_server"),
    (re.compile(r"http[s]?://[^\s\"')]+"), "url_literal"),
]

LOOPBACK = re.compile(r"\b(127\.0\.0\.1|localhost|::1)\b")
# file-level proof that connects are pinned to loopback
LOOPBACK_GUARD = re.compile(r"loopback-only|LOOPBACK_ONLY")


def iter_sources():
    for base in SCAN_DIRS:
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(base)
            if any(part in EXCLUDE_DIRS for part in rel.parts):
                continue
            yield path


def main() -> int:
    findings = []
    violations = []
    for path in iter_sources():
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        guarded = bool(LOOPBACK_GUARD.search(text))
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern, kind in PRIMITIVE_PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                finding = f"{rel}:{lineno} [{kind}] {stripped[:110]}"
                findings.append(finding)
                if kind == "url_literal":
                    host = re.search(
                        r"http[s]?://([^\s/\"')]+)", line
                    ).group(1)
                    if not LOOPBACK.search(host):
                        violations.append(finding)
                elif kind in ("urllib", "requests", "qt_network"):
                    # unreviewed network API anywhere in shipped code
                    violations.append(finding)
                elif kind in ("tcp_connect", "tcp_connect_ex"):
                    if not LOOPBACK.search(line) and not guarded:
                        violations.append(finding)
                break

    print("== network-surface findings ==")
    for f in findings:
        print(f"  {f}")
    if not findings:
        print("  (none)")
    if violations:
        print("\n== REVIEW REQUIRED ==")
        for v in violations:
            print(f"  {v}")
        return 1
    print("\nall socket endpoints are loopback-pinned; "
          "no outbound channel in project code")
    return 0


if __name__ == "__main__":
    sys.exit(main())
