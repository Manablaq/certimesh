import hashlib
import json
import os

import pytest

from tests.conftest import TEST_TIME_ISO, TEST_TIME_UNIX, to_hex


CONTRACT = os.environ.get("CERTIMESH_CONTRACT", "contracts/certimesh_core.py")
PRIMARY_TEXT = "Primary authority: subject satisfies every committed criterion."
CORROBORATING_TEXT = "Corroborating authority: independent record confirms compliance."
PRIMARY_URL = "https://primary.example/records/subject-v1"
CORROBORATING_URL = "https://corroborating.example/records/subject-v1"
PRIMARY_REF = "https://primary.example/archive/subject-v1"
CORROBORATING_REF = "https://corroborating.example/archive/subject-v1"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def criteria() -> str:
    return json.dumps({"all": ["subject satisfies every committed criterion"]})


def policy() -> str:
    return json.dumps({"max_age_seconds": 86_400, "require_independent_sources": True})


def create_program(contract, vm, owner, primary, corroborating):
    vm.sender = owner
    return contract.create_program(
        "certification",
        criteria(),
        policy(),
        primary,
        corroborating,
        3_600,
        86_400,
        7 * 86_400,
        3 * 86_400,
    )


def create_assessment(contract, vm, requester, deadline=None):
    vm.sender = requester
    return contract.create_assessment(
        "certification",
        1,
        "subject-001",
        "a" * 64,
        deadline or TEST_TIME_UNIX + 172_800,
    )


def attest_both(contract, vm, assessment_id, primary, corroborating, deadline=None):
    deadline = deadline or TEST_TIME_UNIX + 172_800
    vm.sender = primary
    contract.attest_evidence(
        assessment_id, 1, 1, "primary-v1", 1, PRIMARY_URL, PRIMARY_REF,
        digest(PRIMARY_TEXT), digest(PRIMARY_TEXT), TEST_TIME_UNIX - 120,
        TEST_TIME_UNIX - 60, deadline + 3_600,
    )
    vm.sender = corroborating
    contract.attest_evidence(
        assessment_id, 1, 2, "corroborating-v1", 1, CORROBORATING_URL,
        CORROBORATING_REF, digest(CORROBORATING_TEXT), digest(CORROBORATING_TEXT),
        TEST_TIME_UNIX - 120, TEST_TIME_UNIX - 60, deadline + 3_600,
    )


def bind_ready(contract, vm, assessment_id, primary, corroborating, deadline=None):
    attest_both(contract, vm, assessment_id, primary, corroborating, deadline)
    vm.sender = primary
    contract.bind_evidence(assessment_id)


def mock_sources(vm):
    vm.mock_web(r"primary\.example/records/subject-v1", {"status": 200, "body": PRIMARY_TEXT})
    vm.mock_web(r"corroborating\.example/records/subject-v1", {"status": 200, "body": CORROBORATING_TEXT})


def test_certified_path_requires_finalization_window(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie
):
    direct_vm.warp(TEST_TIME_ISO)
    contract = direct_deploy(CONTRACT)
    create_program(contract, direct_vm, direct_owner, direct_alice, direct_bob)
    assessment_id = create_assessment(contract, direct_vm, direct_charlie)
    bind_ready(contract, direct_vm, assessment_id, direct_alice, direct_bob)
    mock_sources(direct_vm)
    direct_vm.mock_llm(r"CERTIMESH_R1_ASSESSMENT_V1", json.dumps({"decision": "CERTIFIED"}))
    direct_vm.sender = direct_charlie
    contract.assess(assessment_id)
    assert contract.get_assessment(assessment_id).state == "PROVISIONAL"
    with direct_vm.expect_revert("Challenge window has not closed"):
        contract.finalize_assessment(assessment_id)
    direct_vm.warp("2026-09-27T11:01:00+00:00")
    contract.finalize_assessment(assessment_id)
    result = contract.get_assessment(assessment_id)
    assert result.state == "FINAL"
    assert result.final_decision == "CERTIFIED"
    assert len(result.certificate_digest) == 64
    assert contract.get_certificate(assessment_id).certificate_digest == result.certificate_digest


def test_duplicate_assessment_commitment_and_short_deadline_are_rejected(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie
):
    direct_vm.warp(TEST_TIME_ISO)
    contract = direct_deploy(CONTRACT)
    create_program(contract, direct_vm, direct_owner, direct_alice, direct_bob)
    create_assessment(contract, direct_vm, direct_charlie)
    with direct_vm.expect_revert("Assessment commitment already exists"):
        create_assessment(contract, direct_vm, direct_charlie)
    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("Assessment commitment already exists"):
        contract.create_assessment(
            "certification", 1, "renamed-subject", "a" * 64, TEST_TIME_UNIX + 7_200
        )
    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("full challenge window"):
        contract.create_assessment(
            "certification", 1, "subject-002", "b" * 64, TEST_TIME_UNIX + 3_600
        )


def test_payload_hash_must_match_committed_source_bytes(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie
):
    direct_vm.warp(TEST_TIME_ISO)
    contract = direct_deploy(CONTRACT)
    create_program(contract, direct_vm, direct_owner, direct_alice, direct_bob)
    assessment_id = create_assessment(contract, direct_vm, direct_charlie)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("payload hash must match"):
        contract.attest_evidence(
            assessment_id, 1, 1, "primary-v1", 1, PRIMARY_URL, PRIMARY_REF,
            "1" * 64, digest(PRIMARY_TEXT), TEST_TIME_UNIX - 120,
            TEST_TIME_UNIX - 60, TEST_TIME_UNIX + 173_000,
        )


def test_rejected_path_has_no_certificate(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie
):
    direct_vm.warp(TEST_TIME_ISO)
    contract = direct_deploy(CONTRACT)
    create_program(contract, direct_vm, direct_owner, direct_alice, direct_bob)
    assessment_id = create_assessment(contract, direct_vm, direct_charlie)
    bind_ready(contract, direct_vm, assessment_id, direct_alice, direct_bob)
    mock_sources(direct_vm)
    direct_vm.mock_llm(r"CERTIMESH_R1_ASSESSMENT_V1", json.dumps({"decision": "REJECTED"}))
    contract.assess(assessment_id)
    direct_vm.warp("2026-09-27T11:01:00+00:00")
    contract.finalize_assessment(assessment_id)
    assert contract.get_assessment(assessment_id).final_decision == "REJECTED"
    with direct_vm.expect_revert("No certificate exists"):
        contract.get_certificate(assessment_id)


def test_source_failure_enters_repair_and_never_certifies(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie
):
    direct_vm.warp(TEST_TIME_ISO)
    contract = direct_deploy(CONTRACT)
    create_program(contract, direct_vm, direct_owner, direct_alice, direct_bob)
    assessment_id = create_assessment(contract, direct_vm, direct_charlie)
    bind_ready(contract, direct_vm, assessment_id, direct_alice, direct_bob)
    direct_vm.mock_web(r"primary\.example/records/subject-v1", {"status": 503, "body": ""})
    contract.assess(assessment_id)
    assert contract.get_assessment(assessment_id).state == "REPAIR_REQUIRED"
    with direct_vm.expect_revert("Only provisional assessments can be finalized"):
        contract.finalize_assessment(assessment_id)


def test_validator_rejects_different_decision(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie
):
    direct_vm.warp(TEST_TIME_ISO)
    contract = direct_deploy(CONTRACT)
    create_program(contract, direct_vm, direct_owner, direct_alice, direct_bob)
    assessment_id = create_assessment(contract, direct_vm, direct_charlie)
    bind_ready(contract, direct_vm, assessment_id, direct_alice, direct_bob)
    mock_sources(direct_vm)
    direct_vm.mock_llm(r"CERTIMESH_R1_ASSESSMENT_V1", json.dumps({"decision": "CERTIFIED"}))
    contract.assess(assessment_id)
    direct_vm.clear_mocks()
    mock_sources(direct_vm)
    direct_vm.mock_llm(r"CERTIMESH_R1_ASSESSMENT_V1", json.dumps({"decision": "REJECTED"}))
    assert direct_vm.run_validator() is False


def test_wrong_authority_and_missing_corroboration_are_rejected(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie
):
    direct_vm.warp(TEST_TIME_ISO)
    contract = direct_deploy(CONTRACT)
    create_program(contract, direct_vm, direct_owner, direct_alice, direct_bob)
    assessment_id = create_assessment(contract, direct_vm, direct_charlie)
    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("Sender is not bound"):
        contract.attest_evidence(
            assessment_id, 1, 1, "bad", 1, PRIMARY_URL, PRIMARY_REF,
            digest(PRIMARY_TEXT), digest(PRIMARY_TEXT), TEST_TIME_UNIX - 120,
            TEST_TIME_UNIX - 60, TEST_TIME_UNIX + 173_000,
        )
    direct_vm.sender = direct_alice
    contract.attest_evidence(
        assessment_id, 1, 1, "primary-v1", 1, PRIMARY_URL, PRIMARY_REF,
        digest(PRIMARY_TEXT), digest(PRIMARY_TEXT), TEST_TIME_UNIX - 120,
        TEST_TIME_UNIX - 60, TEST_TIME_UNIX + 173_000,
    )
    with direct_vm.expect_revert("Exactly two independent"):
        contract.bind_evidence(assessment_id)


def test_duplicate_sources_and_stale_evidence_are_rejected(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie
):
    direct_vm.warp(TEST_TIME_ISO)
    contract = direct_deploy(CONTRACT)
    create_program(contract, direct_vm, direct_owner, direct_alice, direct_bob)
    assessment_id = create_assessment(contract, direct_vm, direct_charlie)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Evidence is stale"):
        contract.attest_evidence(
            assessment_id, 1, 1, "old", 1, PRIMARY_URL, PRIMARY_REF,
            digest(PRIMARY_TEXT), digest(PRIMARY_TEXT), TEST_TIME_UNIX - 90_000,
            TEST_TIME_UNIX - 90_000, TEST_TIME_UNIX + 173_000,
        )
    contract.attest_evidence(
        assessment_id, 1, 1, "primary-v1", 1, PRIMARY_URL, PRIMARY_REF,
        digest(PRIMARY_TEXT), digest(PRIMARY_TEXT), TEST_TIME_UNIX - 120,
        TEST_TIME_UNIX - 60, TEST_TIME_UNIX + 173_000,
    )
    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("Immutable source reference is duplicated"):
        contract.attest_evidence(
            assessment_id, 1, 2, "corroborating-v1", 1, CORROBORATING_URL,
            PRIMARY_REF, digest(CORROBORATING_TEXT), digest(CORROBORATING_TEXT),
            TEST_TIME_UNIX - 120, TEST_TIME_UNIX - 60, TEST_TIME_UNIX + 173_000,
        )


def test_retirement_and_version_immutability(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie
):
    direct_vm.warp(TEST_TIME_ISO)
    contract = direct_deploy(CONTRACT)
    create_program(contract, direct_vm, direct_owner, direct_alice, direct_bob)
    original_hash = contract.get_program("certification", 1).criteria_hash
    direct_vm.sender = direct_owner
    assert contract.create_program_version(
        "certification", criteria(), policy(), direct_alice, direct_bob,
        3_600, 86_400, 7 * 86_400, 3 * 86_400,
    ) == 2
    assert contract.get_program("certification", 1).criteria_hash == original_hash
    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("Only the program creator"):
        contract.create_program_version(
            "certification", criteria(), policy(), direct_alice, direct_bob,
            3_600, 86_400, 7 * 86_400, 3 * 86_400,
        )
    direct_vm.sender = direct_owner
    contract.retire_program_version("certification", 1)
    with direct_vm.expect_revert("Retired program"):
        create_assessment(contract, direct_vm, direct_charlie)


def test_challenge_requires_fresh_generation_and_old_evidence_cannot_bind(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie
):
    direct_vm.warp(TEST_TIME_ISO)
    contract = direct_deploy(CONTRACT)
    create_program(contract, direct_vm, direct_owner, direct_alice, direct_bob)
    assessment_id = create_assessment(contract, direct_vm, direct_charlie)
    bind_ready(contract, direct_vm, assessment_id, direct_alice, direct_bob)
    mock_sources(direct_vm)
    direct_vm.mock_llm(r"CERTIMESH_R1_ASSESSMENT_V1", json.dumps({"decision": "CERTIFIED"}))
    contract.assess(assessment_id)
    direct_vm.sender = direct_charlie
    contract.challenge_assessment(assessment_id, "conflicting observation")
    assert contract.get_assessment(assessment_id).state == "CHALLENGED"
    assert contract.open_repair_generation(assessment_id) == 2
    with direct_vm.expect_revert("Exactly two independent"):
        contract.bind_evidence(assessment_id)


def test_expired_assessment_cannot_produce_certificate(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie
):
    direct_vm.warp(TEST_TIME_ISO)
    contract = direct_deploy(CONTRACT)
    create_program(contract, direct_vm, direct_owner, direct_alice, direct_bob)
    deadline = TEST_TIME_UNIX + 7_200
    assessment_id = create_assessment(contract, direct_vm, direct_charlie, deadline)
    direct_vm.warp("2026-09-27T12:01:00+00:00")
    contract.expire_assessment(assessment_id)
    assert contract.get_assessment(assessment_id).state == "EXPIRED"
    with direct_vm.expect_revert("already terminal"):
        contract.expire_assessment(assessment_id)


def test_malformed_model_output_reverts_closed_output_surface(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie
):
    direct_vm.warp(TEST_TIME_ISO)
    contract = direct_deploy(CONTRACT)
    create_program(contract, direct_vm, direct_owner, direct_alice, direct_bob)
    assessment_id = create_assessment(contract, direct_vm, direct_charlie)
    bind_ready(contract, direct_vm, assessment_id, direct_alice, direct_bob)
    mock_sources(direct_vm)
    direct_vm.mock_llm(
        r"CERTIMESH_R1_ASSESSMENT_V1",
        json.dumps({"decision": "CERTIFIED", "confidence": 1}),
    )
    with direct_vm.expect_revert("only decision"):
        contract.assess(assessment_id)
