"""Static R1 release gate; fail closed on forbidden bypass surfaces."""

from pathlib import Path
import hashlib
import sys


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "certimesh_core.py"
FORBIDDEN = (
    "force_certify",
    "force_reject",
    "set_assessment_result",
    "leader_only",
    "frontend",
    "transfer_tokens",
    "stake_tokens",
)


def main() -> int:
    failures: list[str] = []
    required = [
        ROOT / ".python-version",
        ROOT / "requirements-lock.txt",
        CONTRACT,
        ROOT / "tests" / "test_certimesh_direct.py",
        ROOT / "docs" / "SECURITY.md",
    ]
    for path in required:
        if not path.exists():
            failures.append(f"missing {path.relative_to(ROOT)}")
    source = CONTRACT.read_text(encoding="utf-8") if CONTRACT.exists() else ""
    for token in FORBIDDEN:
        if token in source.lower():
            failures.append(f"forbidden token in contract: {token}")
    if source and "gl.vm.run_nondet_unsafe" not in source:
        failures.append("validator consensus boundary is missing")
    if source and "used_decisions" not in source:
        failures.append("decision replay gate is missing")
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    print("CERTIMESH_SOURCE_SHA256=" + digest)
    print("CERTIMESH_RELEASE_GATE=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
