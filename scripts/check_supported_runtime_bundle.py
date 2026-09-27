"""Fail-closed check for the multi-validator evidence package location."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "verification" / "supported_runtime"


def main() -> int:
    required = [
        ROOT / "docs" / "BRADBURY_VERIFICATION.md",
        BUNDLE / ".gitkeep",
        BUNDLE / "README.md",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        print("FAIL missing supported-runtime files: " + ", ".join(missing))
        return 1
    print("SUPPORTED_RUNTIME_BUNDLE=READY_FOR_MULTI_VALIDATOR_RUN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
