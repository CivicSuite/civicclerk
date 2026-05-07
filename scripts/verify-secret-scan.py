"""Fail release recovery if tracked source contains obvious secrets or prompt-injection sentinels."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |)PRIVATE KEY-----"),
    re.compile(r"\bghp_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
    re.compile(r"(?i)(api[_-]?key|client[_-]?secret|password|token)\s*=\s*['\"][^'\"<][^'\"]{12,}['\"]"),
    re.compile(r"(?i)stop\s+claude"),
]
ALLOWLIST = {
    "scripts/verify-secret-scan.py",
}
TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".env",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOWLIST or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            if match:
                matched = match.group(0)
                if "$" in matched or "mock-" in matched.lower() or "not-reported" in matched.lower():
                    continue
                line = text[: match.start()].count("\n") + 1
                findings.append(f"{rel}:{line}: matched {pattern.pattern}")

    if findings:
        print("SECRET-SCAN: FAILED")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print("SECRET-SCAN: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
