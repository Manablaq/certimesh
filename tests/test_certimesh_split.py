import json
import hashlib
import os

import pytest

from tests.conftest import TEST_TIME_UNIX, to_hex


REGISTRY = "contracts/certimesh_registry.py"
ADJUDICATOR = "contracts/certimesh_adjudicator.py"


def _success(result):
    from genlayer.py import calldata

    return bytes([0]) + calldata.encode(result)


def _install_registry_hook(vm):
    calls = []

    def hook(active_vm, request):
        if "CallContract" in request:
            data = request["CallContract"]
            calldata_obj = data.get("calldata", {})
            method = calldata_obj.get("method")
            calls.append((data.get("address"), method))
            if method == "registry_address":
                from genlayer.py.types import Address

                return _success(Address(active_vm._contract_address))
        if "PostMessage" in request:
            calls.append((request["PostMessage"].get("address"), "post_message"))
            return {"ok": None}
        return None

    vm._gl_call_hook = hook
    return calls


def test_registry_adjudicator_binding_is_reciprocal_and_one_shot(
    direct_vm, direct_deploy, direct_owner, direct_alice
):
    registry = direct_deploy(REGISTRY, direct_owner)
    calls = _install_registry_hook(direct_vm)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only the registry owner"):
        registry.bind_adjudicator(direct_alice)
    direct_vm.sender = direct_owner
    registry.bind_adjudicator(direct_alice)
    assert to_hex(registry.get_adjudicator_address()) == "0x" + direct_alice.hex()
    assert any(method == "registry_address" for _, method in calls)
    with direct_vm.expect_revert("already bound"):
        registry.bind_adjudicator(direct_owner)


def test_registry_rejects_an_adjudicator_bound_to_another_registry(
    direct_vm, direct_deploy, direct_owner, direct_alice
):
    registry = direct_deploy(REGISTRY, direct_owner)

    def hook(_active_vm, request):
        if "CallContract" in request:
            from genlayer.py.types import Address

            return _success(Address("0x" + "12" * 20))
        return None

    direct_vm._gl_call_hook = hook
    direct_vm.sender = direct_owner
    with direct_vm.expect_revert("different registry"):
        registry.bind_adjudicator(direct_alice)


def test_adjudicator_only_accepts_calls_from_its_registry(
    direct_vm, direct_deploy, direct_owner, direct_alice
):
    adjudicator = direct_deploy(ADJUDICATOR, direct_owner)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only the bound Registry"):
        adjudicator.assess(1, 1, "0" * 64)


def test_registry_callback_cannot_be_called_by_a_client(
    direct_vm, direct_deploy, direct_owner, direct_alice
):
    registry = direct_deploy(REGISTRY, direct_owner)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only the bound adjudicator"):
        registry.record_assessment_result(1, 1, "0" * 64, "OK", "CERTIFIED", "", "")


def test_retry_replays_only_the_same_bound_request_for_the_requester(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_charlie
):
    registry = direct_deploy(REGISTRY, direct_owner)
    calls = []

    def hook(active_vm, request):
        if "CallContract" in request:
            data = request["CallContract"]
            calldata_obj = data.get("calldata", {})
            method = calldata_obj.get("method")
            calls.append((data.get("address"), method, calldata_obj.get("args", [])))
            from genlayer.py.types import Address

            if method == "registry_address":
                return _success(Address(active_vm._contract_address))
            if method == "get_program_snapshot":
                snapshot = {
                    "creator": "0x" + "11" * 20,
                    "program_id": "certification",
                    "version": 1,
                    "criteria_json": "{}",
                    "evidence_policy_json": "{}",
                    "primary_authority": "0x" + "22" * 20,
                    "corroborating_authority": "0x" + "33" * 20,
                    "challenge_window_seconds": 3600,
                    "max_evidence_age_seconds": 86400,
                    "certificate_validity_seconds": 86400,
                    "max_assessment_horizon_seconds": 172800,
                    "retired": False,
                }
                return _success(json.dumps(snapshot))
        if "PostMessage" in request:
            calls.append((request["PostMessage"].get("address"), "post_message", request["PostMessage"].get("calldata")))
            return {"ok": None}
        return None

    direct_vm._gl_call_hook = hook
    direct_vm.warp("2026-09-27T10:00:00+00:00")
    direct_vm.sender = direct_owner
    registry.bind_adjudicator(direct_alice)
    direct_vm.sender = direct_charlie
    assessment_id = registry.create_assessment(
        "certification", 1, "subject-001", "a" * 64, TEST_TIME_UNIX + 172800
    )
    assessment = registry.get_assessment(assessment_id)
    assessment.state = "EVIDENCE_BOUND"
    assessment.evidence_set_hash = "b" * 64
    assessment.last_retry_at = 1790501400
    registry.assessments[assessment_id] = assessment

    with direct_vm.expect_revert("Only the assessment requester"):
        direct_vm.sender = direct_owner
        registry.retry_assessment(assessment_id)

    direct_vm.sender = direct_charlie
    registry.retry_assessment(assessment_id)
    assert registry.get_assessment(assessment_id).generation == 1
    assert registry.get_assessment(assessment_id).evidence_set_hash == "b" * 64
    assert any(method == "post_message" for _, method, _ in calls)

    with direct_vm.expect_revert("Retry cooldown has not elapsed"):
        registry.retry_assessment(assessment_id)

    direct_vm.warp("2026-09-27T10:31:00+00:00")
    registry.retry_assessment(assessment_id)
    assert registry.get_assessment(assessment_id).last_retry_at == 1790505060

    assessment = registry.get_assessment(assessment_id)
    assessment.state = "PROVISIONAL"
    registry.assessments[assessment_id] = assessment
    with direct_vm.expect_revert("Only evidence-bound assessments"):
        registry.retry_assessment(assessment_id)


def test_initial_assessment_dispatch_starts_retry_cooldown(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_charlie
):
    registry = direct_deploy(REGISTRY, direct_owner)

    def hook(active_vm, request):
        if "CallContract" in request:
            data = request["CallContract"]
            calldata_obj = data.get("calldata", {})
            method = calldata_obj.get("method")
            from genlayer.py.types import Address

            if method == "registry_address":
                return _success(Address(active_vm._contract_address))
            if method == "get_program_snapshot":
                return _success(json.dumps({
                    "creator": "0x" + "11" * 20,
                    "program_id": "certification",
                    "version": 1,
                    "criteria_json": "{}",
                    "evidence_policy_json": "{}",
                    "primary_authority": "0x" + "22" * 20,
                    "corroborating_authority": "0x" + "33" * 20,
                    "challenge_window_seconds": 3600,
                    "max_evidence_age_seconds": 86400,
                    "certificate_validity_seconds": 86400,
                    "max_assessment_horizon_seconds": 172800,
                    "retired": False,
                }))
            if method == "get_bound_snapshot":
                return _success(json.dumps({
                    "bound": True,
                    "generation": 1,
                    "evidence_set_hash": "b" * 64,
                }))
        if "PostMessage" in request:
            return {"ok": None}
        return None

    direct_vm._gl_call_hook = hook
    direct_vm.warp("2026-09-27T10:00:00+00:00")
    direct_vm.sender = direct_owner
    registry.bind_evidence_registry(direct_alice)
    registry.bind_adjudicator(direct_alice)
    direct_vm.sender = direct_charlie
    assessment_id = registry.create_assessment(
        "certification", 1, "subject-002", "c" * 64, TEST_TIME_UNIX + 172800
    )
    registry.assessments[assessment_id].state = "REQUESTED"
    registry.assess(assessment_id)

    with direct_vm.expect_revert("Retry cooldown has not elapsed"):
        registry.retry_assessment(assessment_id)


def test_adjudicator_uses_subjective_equivalence_and_emits_validated_result(
    direct_vm, direct_deploy, direct_owner
):
    registry_address = "0x" + "55" * 20
    primary_text = "Primary authority confirms the committed criterion."
    corroborating_text = "Corroborating authority independently confirms the criterion."
    primary_hash = hashlib.sha256(primary_text.encode()).hexdigest()
    corroborating_hash = hashlib.sha256(corroborating_text.encode()).hexdigest()
    evidence_hash = "e" * 64
    context = {
        "assessment": {
            "assessment_id": 7,
            "generation": 1,
            "evidence_set_hash": evidence_hash,
            "subject_id": "subject-007",
            "subject_digest": "a" * 64,
            "program_id": "certification",
            "program_version": 1,
            "assessment_deadline": TEST_TIME_UNIX + 172800,
        },
        "program": {
            "criteria_json": "{}",
            "evidence_policy_json": "{}",
        },
        "evidence": [
            {
                "role": 1,
                "authority": "0x" + "11" * 20,
                "evidence_record_id": "primary-007",
                "evidence_record_version": 1,
                "source_url": "https://primary.example/records/subject-007",
                "immutable_source_ref": "https://primary.example/archive/subject-007",
                "source_content_hash": primary_hash,
            },
            {
                "role": 2,
                "authority": "0x" + "22" * 20,
                "evidence_record_id": "corroborating-007",
                "evidence_record_version": 1,
                "source_url": "https://corroborating.example/records/subject-007",
                "immutable_source_ref": "https://corroborating.example/archive/subject-007",
                "source_content_hash": corroborating_hash,
            },
        ],
    }
    emitted = []

    def hook(_active_vm, request):
        if "ExecPromptTemplate" in request:
            return {
                "ok": {
                    "assessment_id": 7,
                    "generation": 1,
                    "evidence_set_hash": evidence_hash,
                    "result_status": "OK",
                    "decision": "CERTIFIED",
                    "failure_code": "",
                    "observed_sha256": "",
                }
            }
        if "CallContract" in request:
            data = request["CallContract"]
            if data.get("calldata", {}).get("method") == "get_review_context":
                return _success(json.dumps(context))
        if "PostMessage" in request:
            emitted.append(request["PostMessage"])
            return {"ok": None}
        return None

    direct_vm._gl_call_hook = hook
    direct_vm.warp("2026-09-27T10:00:00+00:00")
    direct_vm.mock_web(r"primary\.example/records/subject-007", {"status": 200, "body": primary_text})
    direct_vm.mock_web(r"corroborating\.example/records/subject-007", {"status": 200, "body": corroborating_text})
    direct_vm.mock_llm(r"CERTIMESH_R1_ASSESSMENT_V1", json.dumps({"decision": "CERTIFIED"}))
    adjudicator = direct_deploy(ADJUDICATOR, registry_address)
    direct_vm.sender = bytes.fromhex("55" * 20)
    adjudicator.assess(7, 1, evidence_hash)
    assert emitted
