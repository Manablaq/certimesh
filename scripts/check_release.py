"""Static R1 release gate; fail closed on forbidden bypass surfaces."""

from pathlib import Path
import ast
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "certimesh_core.py"
DEPLOY_ARTIFACT = ROOT / "contracts" / "certimesh_core_deploy.py"
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
        DEPLOY_ARTIFACT,
        ROOT / "scripts" / "build_deploy_artifact.py",
        ROOT / "tests" / "test_certimesh_direct.py",
        ROOT / "docs" / "SECURITY.md",
    ]
    for path in required:
        if not path.exists():
            failures.append(f"missing {path.relative_to(ROOT)}")
    source = CONTRACT.read_text(encoding="utf-8") if CONTRACT.exists() else ""
    if DEPLOY_ARTIFACT.exists():
        artifact_source = DEPLOY_ARTIFACT.read_text(encoding="utf-8")
        try:
            artifact = ast.parse(DEPLOY_ARTIFACT.read_text(encoding="utf-8"))
            contract = next(
                node for node in artifact.body
                if isinstance(node, ast.ClassDef) and node.name == "CertiMeshCore"
            )
        except (SyntaxError, StopIteration):
            failures.append("deployment artifact is not a valid CertiMeshCore module")
        else:
            methods = {node.name for node in contract.body if isinstance(node, ast.FunctionDef)}
            required_methods = {"__init__", "create_program", "create_assessment", "assess"}
            if not required_methods.issubset(methods):
                failures.append("deployment artifact is missing required public methods")
    for label, candidate in (("canonical", source), ("deployment artifact", artifact_source if DEPLOY_ARTIFACT.exists() else "")):
        for token in FORBIDDEN:
            if token in candidate.lower():
                failures.append(f"forbidden token in {label}: {token}")
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
