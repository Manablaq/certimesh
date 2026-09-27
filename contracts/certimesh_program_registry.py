# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""CertiMesh immutable program/version registry.

Program terms are committed in this small contract so the assessment registry
does not carry deployment-time code for version creation and retirement.
Versions are write-once; only the original creator can add or retire a version.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import NoReturn

from genlayer import *


ZERO_ADDRESS = Address("0x0000000000000000000000000000000000000000")
MAX_PROGRAM_ID_CHARS = 128
MAX_JSON_CHARS = 24_000
MIN_CHALLENGE_SECONDS = 60
MAX_CHALLENGE_SECONDS = 30 * 24 * 60 * 60


def _fail(message: str) -> NoReturn:
    raise gl.vm.UserError(message)


def _address_key(address: Address) -> str:
    if hasattr(address, "as_hex"):
        return address.as_hex.lower()
    if isinstance(address, (bytes, bytearray, memoryview)):
        value = bytes(address)
        if len(value) != 20:
            _fail("Invalid address")
        return "0x" + value.hex()
    value = str(address).lower()
    if value.startswith("0x") and len(value) == 42:
        return value
    _fail("Invalid address")


def _as_address(address: Address) -> Address:
    return address if hasattr(address, "as_hex") else Address(_address_key(address))


def _bounded(value: str, label: str, maximum: int) -> str:
    if not isinstance(value, str):
        _fail(f"{label} must be text")
    # The current GenLayer CLI documents `str: value` arguments but passes
    # that compatibility marker through literally. Normalize only that exact
    # marker here, then apply the same strict validation to the resulting text.
    if value.startswith("str:"):
        value = value[4:]
    value = value.strip()
    if not value or len(value) > maximum:
        _fail(f"{label} is empty or too long")
    return value


def _json(value: str, label: str) -> str:
    value = _bounded(value, label, MAX_JSON_CHARS)
    try:
        parsed = json.loads(value)
    except Exception:
        _fail(f"{label} must be valid JSON")
    if not isinstance(parsed, (dict, list)) or not parsed:
        _fail(f"{label} must be a non-empty JSON object or array")
    return value


def _json_object(value: dict, label: str) -> str:
    if not isinstance(value, dict) or not value:
        _fail(f"{label} must be a non-empty JSON object")
    return _json(json.dumps(value, sort_keys=True, separators=(",", ":")), label)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _key(program_id: str, version: u256) -> str:
    return f"{program_id}:{int(version)}"


@allow_storage
@dataclass
class ProgramRecord:
    creator: Address
    program_id: str
    version: u256
    criteria_json: str
    evidence_policy_json: str
    criteria_hash: str
    evidence_policy_hash: str
    authority_set_hash: str
    primary_authority: Address
    corroborating_authority: Address
    challenge_window_seconds: u256
    max_evidence_age_seconds: u256
    certificate_validity_seconds: u256
    max_assessment_horizon_seconds: u256
    retired: bool
    created_at: str


class CertiMeshProgramRegistry(gl.Contract):
    programs: TreeMap[str, ProgramRecord]
    latest_program_version: TreeMap[str, u256]

    def __init__(self):
        pass

    def _require(self, program_id: str, version: u256) -> ProgramRecord:
        key = _key(program_id, version)
        if key not in self.programs:
            _fail("Unknown program version")
        return self.programs[key]

    def _validate_terms(
        self,
        primary_authority: Address,
        corroborating_authority: Address,
        challenge_window_seconds: u256,
        max_evidence_age_seconds: u256,
        certificate_validity_seconds: u256,
        max_assessment_horizon_seconds: u256,
    ) -> None:
        primary_authority = _as_address(primary_authority)
        corroborating_authority = _as_address(corroborating_authority)
        if _address_key(primary_authority) == _address_key(ZERO_ADDRESS) or _address_key(corroborating_authority) == _address_key(ZERO_ADDRESS):
            _fail("Authorities cannot be zero addresses")
        if _address_key(primary_authority) == _address_key(corroborating_authority):
            _fail("Authorities must be distinct")
        if not MIN_CHALLENGE_SECONDS <= int(challenge_window_seconds) <= MAX_CHALLENGE_SECONDS:
            _fail("Challenge window is outside the supported range")
        if int(max_evidence_age_seconds) <= 0 or int(certificate_validity_seconds) <= 0:
            _fail("Program durations must be positive")
        if int(max_assessment_horizon_seconds) <= int(challenge_window_seconds):
            _fail("Assessment horizon must exceed challenge window")

    def _create(
        self,
        program_id: str,
        version: u256,
        criteria_json: str,
        evidence_policy_json: str,
        primary_authority: Address,
        corroborating_authority: Address,
        challenge_window_seconds: u256,
        max_evidence_age_seconds: u256,
        certificate_validity_seconds: u256,
        max_assessment_horizon_seconds: u256,
    ) -> u256:
        program_id = _bounded(program_id, "Program id", MAX_PROGRAM_ID_CHARS)
        criteria_json = _json(criteria_json, "Criteria")
        evidence_policy_json = _json(evidence_policy_json, "Evidence policy")
        self._validate_terms(primary_authority, corroborating_authority, challenge_window_seconds, max_evidence_age_seconds, certificate_validity_seconds, max_assessment_horizon_seconds)
        key = _key(program_id, version)
        if key in self.programs:
            _fail("Program version already exists")
        primary_authority = _as_address(primary_authority)
        corroborating_authority = _as_address(corroborating_authority)
        self.programs[key] = ProgramRecord(
            creator=_as_address(gl.message.sender_address),
            program_id=program_id,
            version=version,
            criteria_json=criteria_json,
            evidence_policy_json=evidence_policy_json,
            criteria_hash=_sha(criteria_json),
            evidence_policy_hash=_sha(evidence_policy_json),
            authority_set_hash=_sha(json.dumps({"primary": _address_key(primary_authority), "corroborating": _address_key(corroborating_authority)}, sort_keys=True, separators=(",", ":"))),
            primary_authority=primary_authority,
            corroborating_authority=corroborating_authority,
            challenge_window_seconds=challenge_window_seconds,
            max_evidence_age_seconds=max_evidence_age_seconds,
            certificate_validity_seconds=certificate_validity_seconds,
            max_assessment_horizon_seconds=max_assessment_horizon_seconds,
            retired=False,
            created_at=str(datetime.now(timezone.utc).isoformat()),
        )
        self.latest_program_version[program_id] = version
        return version

    @gl.public.write
    def create_program(self, program_id: str, criteria_json: str, evidence_policy_json: str, primary_authority: Address, corroborating_authority: Address, challenge_window_seconds: u256, max_evidence_age_seconds: u256, certificate_validity_seconds: u256, max_assessment_horizon_seconds: u256) -> u256:
        program_id = _bounded(program_id, "Program id", MAX_PROGRAM_ID_CHARS)
        if program_id in self.latest_program_version:
            _fail("Program already exists")
        return self._create(program_id, u256(1), criteria_json, evidence_policy_json, primary_authority, corroborating_authority, challenge_window_seconds, max_evidence_age_seconds, certificate_validity_seconds, max_assessment_horizon_seconds)

    @gl.public.write
    def create_program_from_objects(self, program_id: str, criteria: dict, evidence_policy: dict, primary_authority: Address, corroborating_authority: Address, challenge_window_seconds: u256, max_evidence_age_seconds: u256, certificate_validity_seconds: u256, max_assessment_horizon_seconds: u256) -> u256:
        program_id = _bounded(program_id, "Program id", MAX_PROGRAM_ID_CHARS)
        if program_id in self.latest_program_version:
            _fail("Program already exists")
        return self._create(program_id, u256(1), _json_object(criteria, "Criteria"), _json_object(evidence_policy, "Evidence policy"), primary_authority, corroborating_authority, challenge_window_seconds, max_evidence_age_seconds, certificate_validity_seconds, max_assessment_horizon_seconds)

    @gl.public.write
    def create_program_version(self, program_id: str, criteria_json: str, evidence_policy_json: str, primary_authority: Address, corroborating_authority: Address, challenge_window_seconds: u256, max_evidence_age_seconds: u256, certificate_validity_seconds: u256, max_assessment_horizon_seconds: u256) -> u256:
        program_id = _bounded(program_id, "Program id", MAX_PROGRAM_ID_CHARS)
        if program_id not in self.latest_program_version:
            _fail("Unknown program")
        prior = self._require(program_id, self.latest_program_version[program_id])
        if _address_key(gl.message.sender_address) != _address_key(prior.creator):
            _fail("Only the program creator can create a version")
        return self._create(program_id, u256(int(self.latest_program_version[program_id]) + 1), criteria_json, evidence_policy_json, primary_authority, corroborating_authority, challenge_window_seconds, max_evidence_age_seconds, certificate_validity_seconds, max_assessment_horizon_seconds)

    @gl.public.write
    def retire_program_version(self, program_id: str, version: u256) -> None:
        program = self._require(program_id, version)
        if _address_key(gl.message.sender_address) != _address_key(program.creator):
            _fail("Only the program creator can retire a version")
        if program.retired:
            _fail("Program version is already retired")
        program.retired = True

    def _snapshot(self, program: ProgramRecord) -> str:
        return json.dumps(
            {
                "creator": _address_key(program.creator), "program_id": program.program_id, "version": int(program.version),
                "criteria_json": program.criteria_json, "evidence_policy_json": program.evidence_policy_json,
                "criteria_hash": program.criteria_hash, "evidence_policy_hash": program.evidence_policy_hash,
                "authority_set_hash": program.authority_set_hash, "primary_authority": _address_key(program.primary_authority),
                "corroborating_authority": _address_key(program.corroborating_authority),
                "challenge_window_seconds": int(program.challenge_window_seconds), "max_evidence_age_seconds": int(program.max_evidence_age_seconds),
                "certificate_validity_seconds": int(program.certificate_validity_seconds), "max_assessment_horizon_seconds": int(program.max_assessment_horizon_seconds),
                "retired": program.retired, "created_at": program.created_at,
            }, sort_keys=True, separators=(",", ":")
        )

    @gl.public.view
    def get_program(self, program_id: str, version: u256) -> ProgramRecord:
        return self._require(program_id, version)

    @gl.public.view
    def get_program_snapshot(self, program_id: str, version: u256) -> str:
        return self._snapshot(self._require(program_id, version))

    @gl.public.view
    def get_latest_program_version(self, program_id: str) -> u256:
        if program_id not in self.latest_program_version:
            _fail("Unknown program")
        return self.latest_program_version[program_id]
