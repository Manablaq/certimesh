"""Static R1 release gate; fail closed on forbidden bypass surfaces."""

from pathlib import Path
import ast
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "certimesh_core.py"
DEPLOY_ARTIFACT = ROOT / "contracts" / "certimesh_core_deploy.py"
REGISTRY = ROOT / "contracts" / "certimesh_registry.py"
REGISTRY_ARTIFACT = ROOT / "contracts" / "certimesh_registry_deploy.py"
PROGRAM_REGISTRY = ROOT / "contracts" / "certimesh_program_registry.py"
PROGRAM_REGISTRY_ARTIFACT = ROOT / "contracts" / "certimesh_program_registry_deploy.py"
ADJUDICATOR = ROOT / "contracts" / "certimesh_adjudicator.py"
ADJUDICATOR_ARTIFACT = ROOT / "contracts" / "certimesh_adjudicator_deploy.py"
EVIDENCE_REGISTRY = ROOT / "contracts" / "certimesh_evidence_registry.py"
EVIDENCE_REGISTRY_ARTIFACT = ROOT / "contracts" / "certimesh_evidence_registry_deploy.py"
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
        ROOT / "tests" / "test_certimesh_split.py",
        ROOT / "docs" / "SECURITY.md",
        REGISTRY,
        REGISTRY_ARTIFACT,
        PROGRAM_REGISTRY,
        PROGRAM_REGISTRY_ARTIFACT,
        ADJUDICATOR,
        ADJUDICATOR_ARTIFACT,
        ROOT / "scripts" / "build_registry_artifact.py",
        ROOT / "scripts" / "build_program_registry_artifact.py",
        ROOT / "scripts" / "build_adjudicator_artifact.py",
        EVIDENCE_REGISTRY,
        EVIDENCE_REGISTRY_ARTIFACT,
        ROOT / "scripts" / "build_evidence_registry_artifact.py",
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
    split_candidates = (
        ("registry", REGISTRY, REGISTRY_ARTIFACT, "CertiMeshRegistry"),
        ("program registry", PROGRAM_REGISTRY, PROGRAM_REGISTRY_ARTIFACT, "CertiMeshProgramRegistry"),
        ("adjudicator", ADJUDICATOR, ADJUDICATOR_ARTIFACT, "CertiMeshAdjudicator"),
        ("evidence registry", EVIDENCE_REGISTRY, EVIDENCE_REGISTRY_ARTIFACT, "CertiMeshEvidenceRegistry"),
    )
    for label, canonical_path, artifact_path, class_name in split_candidates:
        canonical = canonical_path.read_text(encoding="utf-8") if canonical_path.exists() else ""
        artifact_text = artifact_path.read_text(encoding="utf-8") if artifact_path.exists() else ""
        for candidate_label, candidate in ((label, canonical), (f"{label} artifact", artifact_text)):
            if candidate and "CertiMeshCore" in candidate:
                failures.append(f"legacy monolith name in {candidate_label}")
            for token in FORBIDDEN:
                if token in candidate.lower():
                    failures.append(f"forbidden token in {candidate_label}: {token}")
        for candidate_label, candidate in ((label, canonical), (f"{label} artifact", artifact_text)):
            try:
                tree = ast.parse(candidate)
                contract = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
            except (SyntaxError, StopIteration):
                failures.append(f"{candidate_label} is not a valid {class_name} module")
                continue
            methods = {node.name for node in contract.body if isinstance(node, ast.FunctionDef)}
            if class_name == "CertiMeshRegistry":
                required_methods = {"__init__", "bind_adjudicator", "record_assessment_result", "assess", "retry_assessment"}
                if not required_methods.issubset(methods):
                    failures.append("registry is missing split binding or callback methods")
                if "run_nondet_unsafe" in candidate:
                    failures.append(f"nondeterministic evaluator leaked into {candidate_label}")
            elif class_name == "CertiMeshProgramRegistry":
                if not {"__init__", "create_program", "get_program_snapshot"}.issubset(methods):
                    failures.append("program registry is missing immutable version methods")
                if "run_nondet_unsafe" in candidate:
                    failures.append(f"nondeterminism leaked into {candidate_label}")
            else:
                if class_name == "CertiMeshEvidenceRegistry":
                    if not {"__init__", "registry_address", "attest_evidence", "bind_evidence", "get_review_records"}.issubset(methods):
                        failures.append("evidence registry is missing authenticated evidence methods")
                    if "run_nondet_unsafe" in candidate:
                        failures.append(f"nondeterminism leaked into {candidate_label}")
                    continue
                if not {"__init__", "registry_address", "assess"}.issubset(methods):
                    failures.append("adjudicator is missing authenticated assessment methods")
                if "prompt_non_comparative" not in candidate:
                    failures.append(f"subjective validator consensus boundary missing from {candidate_label}")
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    split_manifest = []
    for _, canonical_path, artifact_path, _ in split_candidates:
        split_manifest.extend(
            (
                canonical_path.relative_to(ROOT).as_posix(),
                canonical_path.read_text(encoding="utf-8"),
                artifact_path.relative_to(ROOT).as_posix(),
                artifact_path.read_text(encoding="utf-8"),
            )
        )
    split_digest = hashlib.sha256("\n".join(split_manifest).encode("utf-8")).hexdigest()
    print("CERTIMESH_SOURCE_SHA256=" + digest)
    print("CERTIMESH_SPLIT_MANIFEST_SHA256=" + split_digest)
    print("CERTIMESH_RELEASE_GATE=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
