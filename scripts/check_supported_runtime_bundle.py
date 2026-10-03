"""Fail-closed check for the multi-validator evidence package location."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "verification" / "supported_runtime"


def main() -> int:
    required = [
        ROOT / "docs" / "BRADBURY_VERIFICATION.md",
        BUNDLE / "README.md",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        print("FAIL missing supported-runtime files: " + ", ".join(missing))
        return 1
    manifest = BUNDLE / "manifest.json"
    raw_dir = BUNDLE / "raw"
    if not manifest.is_file() or not raw_dir.is_dir():
        print("FAIL supported-runtime evidence package is incomplete")
        print("  requires verification/supported_runtime/manifest.json and raw/")
        return 1
    raw_files = [path for path in raw_dir.rglob("*") if path.is_file()]
    if not raw_files:
        print("FAIL supported-runtime evidence package has no raw validator artifacts")
        return 1
    print("SUPPORTED_RUNTIME_BUNDLE=COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
