"""Run CivicClerk prompt evaluations in deterministic offline mode."""

from __future__ import annotations

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from civicclerk.prompt_evals import run_prompt_evaluations


def main() -> int:
    provider = os.environ.get("CIVICCORE_LLM_PROVIDER", "")
    offline = os.environ.get("CIVICCLERK_EVAL_OFFLINE") == "1"
    results = run_prompt_evaluations(provider=provider, offline=offline)

    failures = [result for result in results if not result.passed]
    for result in results:
        print(
            f"{result.prompt_reference} provider={result.provider} "
            f"offline={str(result.offline).lower()} passed={str(result.passed).lower()} "
            f"- {result.message}"
        )

    if failures:
        print("PROMPT-EVALS: FAILED")
        return 1

    print("PROMPT-EVALS: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
