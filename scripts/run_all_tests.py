"""Run every microservice's unit & API test suite in an isolated subprocess."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITES = [
    (ROOT / "packages" / "service-kit", "tests"),
    (ROOT / "services" / "gateway", "tests"),
    (ROOT / "services" / "identity-service", "tests"),
    (ROOT / "services" / "subscription-service", "tests"),
    (ROOT / "services" / "asset-service", "tests"),
    (ROOT / "services" / "lifecycle-service", "tests"),
    (ROOT / "services" / "integration-service", "tests"),
    (ROOT / "services" / "governance-service", "tests"),
    (ROOT, "infra/postgres"),
]


def main() -> int:
    failed = []
    for cwd, test_dir in SUITES:
        label = str(cwd.relative_to(ROOT)) if cwd != ROOT else test_dir
        print(f"\n=== Running tests for {label} ===", flush=True)
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", test_dir, "-p", "test_*.py", "-v"],
            cwd=str(cwd),
        )
        if proc.returncode != 0:
            failed.append(label)
    if failed:
        print(f"\nFAILED suites: {', '.join(failed)}")
        return 1
    print("\nALL microservice test suites PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
