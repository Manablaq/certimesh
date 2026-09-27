import os

import pytest

from tests.conftest import to_hex


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
