from datetime import datetime


TEST_TIME_ISO = "2026-09-27T10:00:00+00:00"
TEST_TIME_UNIX = int(datetime.fromisoformat(TEST_TIME_ISO).timestamp())


def to_hex(address) -> str:
    value = address.as_hex if hasattr(address, "as_hex") else address
    return str(value).lower()


def pytest_configure(config):
    config.addinivalue_line("markers", "direct: Direct Mode contract tests")


import pytest


@pytest.fixture(autouse=True)
def strict_direct_mode(direct_vm):
    direct_vm.strict_mocks = True
    direct_vm.check_pickling = True
