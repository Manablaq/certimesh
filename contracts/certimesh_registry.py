# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Deterministic CertiMesh assessment and certificate registry."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, NoReturn, cast
from genlayer import *

ZERO_ADDRESS=Address("0x0000000000000000000000000000000000000000")
REQUESTED="REQUESTED"; EVIDENCE_BOUND="EVIDENCE_BOUND"; PROVISIONAL="PROVISIONAL"; CHALLENGED="CHALLENGED"; REPAIR_REQUIRED="REPAIR_REQUIRED"; FINAL="FINAL"; EXPIRED="EXPIRED"
CERTIFIED="CERTIFIED"; REJECTED="REJECTED"; REPAIR="REPAIR"; MAX_SUBJECT_ID_CHARS=256; MAX_TEXT_CHARS=4000; RETRY_COOLDOWN_SECONDS=1800

@gl.contract_interface
class CertiMeshProgramRegistry:
    class View:
        def get_program_snapshot(self,program_id:str,version:u256,/)->str:...

@gl.contract_interface
class CertiMeshEvidenceRegistry:
    class View:
        def registry_address(self,/)->Address:...
        def get_bound_snapshot(self,assessment_id:u256,/)->str:...
        def get_review_records(self,assessment_id:u256,generation:u256,/)->str:...

@gl.contract_interface
class CertiMeshAdjudicator:
    class View:
        def registry_address(self,/)->Address:...
    class Write:
        def assess(self,assessment_id:u256,generation:u256,evidence_set_hash:str,/)->None:...

def _fail(message:str)->NoReturn: raise gl.vm.UserError(message)
def _now()->u256: return u256(int(datetime.now(timezone.utc).timestamp()))
def _key(address:Address)->str:
    if hasattr(address,"as_hex"): return address.as_hex.lower()
    if isinstance(address,(bytes,bytearray,memoryview)):
        raw=bytes(address)
        if len(raw)!=20:_fail("Invalid address")
        return "0x"+raw.hex()
    value=str(address).lower()
    if value.startswith("0x") and len(value)==42:return value
    _fail("Invalid address")
def _addr(address:Address)->Address:return address if hasattr(address,"as_hex") else Address(_key(address))
def _nonzero(address:Address,label:str)->None:
    if _key(address)==_key(ZERO_ADDRESS):_fail(f"{label} cannot be the zero address")
def _text(value:str,label:str,maximum:int)->str:
    if not isinstance(value,str):_fail(f"{label} must be text")
    value=value.strip()
    if not value or len(value)>maximum:_fail(f"{label} is empty or too long")
    return value
def _hash(value:str)->str:return hashlib.sha256(value.encode("utf-8")).hexdigest()
def _hex64(value:str)->bool:return isinstance(value,str) and len(value)==64 and all(c in "0123456789abcdef" for c in value)
def _commitment(program_id:str,version:u256,subject_digest:str)->str:return _hash(json.dumps({"domain":"CERTIMESH_ASSESSMENT_COMMITMENT_V1","program_id":program_id,"program_version":int(version),"subject_digest":subject_digest},sort_keys=True,separators=(",",":")))

@allow_storage
@dataclass
class ProgramRecord:
    creator:Address; program_id:str; version:u256; criteria_json:str; evidence_policy_json:str; primary_authority:Address; corroborating_authority:Address; challenge_window_seconds:u256; max_evidence_age_seconds:u256; certificate_validity_seconds:u256; max_assessment_horizon_seconds:u256; retired:bool

@allow_storage
@dataclass
class AssessmentRecord:
    requester:Address; assessment_id:u256; program_id:str; program_version:u256; subject_id:str; subject_digest:str; state:str; generation:u256; evidence_set_hash:str; provisional_decision:str; challenge_hash:str; challenge_deadline:u256; assessment_deadline:u256; final_decision:str; certificate_digest:str; issued_at:u256; expires_at:u256; decision_nonce:u256; decision_recorded:bool; challenged:bool; last_retry_at:u256

@allow_storage
@dataclass
class CertificateRecord:
    assessment_id:u256; program_id:str; program_version:u256; subject_id:str; subject_digest:str; evidence_set_hash:str; final_decision:str; issued_at:u256; expires_at:u256; decision_nonce:u256; certificate_digest:str

class CertiMeshRegistry(gl.Contract):
    owner:Address; program_registry_address:Address; evidence_registry_address:Address; adjudicator_address:Address
    assessments:TreeMap[u256,AssessmentRecord]; assessment_commitment_seen:TreeMap[str,bool]; certificates:TreeMap[u256,CertificateRecord]; used_decisions:TreeMap[str,bool]
    next_assessment_id:u256; next_decision_nonce:u256
    def __init__(self,program_registry_address:Address):
        program_registry_address=_addr(program_registry_address); _nonzero(program_registry_address,"Program Registry")
        self.owner=gl.message.sender_address; self.program_registry_address=program_registry_address
        self.evidence_registry_address=ZERO_ADDRESS; self.adjudicator_address=ZERO_ADDRESS; self.next_assessment_id=u256(1); self.next_decision_nonce=u256(1)
    @gl.public.view
    def get_adjudicator_address(self)->Address:return self.adjudicator_address
    @gl.public.view
    def get_evidence_registry_address(self)->Address:return self.evidence_registry_address
    @gl.public.write
    def bind_evidence_registry(self,evidence_registry_address:Address)->None:
        if _key(gl.message.sender_address)!=_key(self.owner):_fail("Only the registry owner can bind the evidence registry")
        if _key(self.evidence_registry_address)!=_key(ZERO_ADDRESS):_fail("Evidence Registry is already bound")
        evidence=_addr(evidence_registry_address); _nonzero(evidence,"Evidence Registry")
        try:bound=CertiMeshEvidenceRegistry(evidence).view().registry_address()
        except Exception:_fail("Evidence Registry reciprocal binding check failed")
        if _key(bound)!=_key(gl.message.contract_address):_fail("Evidence Registry is bound to a different registry")
        self.evidence_registry_address=evidence
    @gl.public.write
    def bind_adjudicator(self,adjudicator_address:Address)->None:
        if _key(gl.message.sender_address)!=_key(self.owner):_fail("Only the registry owner can bind the adjudicator")
        if _key(self.adjudicator_address)!=_key(ZERO_ADDRESS):_fail("Adjudicator is already bound")
        adjudicator=_addr(adjudicator_address); _nonzero(adjudicator,"Adjudicator")
        try:bound=CertiMeshAdjudicator(adjudicator).view().registry_address()
        except Exception:_fail("Adjudicator reciprocal binding check failed")
        if _key(bound)!=_key(gl.message.contract_address):_fail("Adjudicator is bound to a different registry")
        self.adjudicator_address=adjudicator
    def _program(self,program_id:str,version:u256)->ProgramRecord:
        try:
            value=json.loads(CertiMeshProgramRegistry(self.program_registry_address).view().get_program_snapshot(program_id,version))
            return ProgramRecord(creator=_addr(value["creator"]),program_id=value["program_id"],version=u256(int(value["version"])),criteria_json=value["criteria_json"],evidence_policy_json=value["evidence_policy_json"],primary_authority=_addr(value["primary_authority"]),corroborating_authority=_addr(value["corroborating_authority"]),challenge_window_seconds=u256(int(value["challenge_window_seconds"])),max_evidence_age_seconds=u256(int(value["max_evidence_age_seconds"])),certificate_validity_seconds=u256(int(value["certificate_validity_seconds"])),max_assessment_horizon_seconds=u256(int(value["max_assessment_horizon_seconds"])),retired=bool(value["retired"]))
        except Exception:_fail("Unknown program version")
    def _assessment(self,assessment_id:u256)->AssessmentRecord:
        if assessment_id not in self.assessments:_fail("Unknown assessment")
        return self.assessments[assessment_id]
    @gl.public.write
    def create_assessment(self,program_id:str,program_version:u256,subject_id:str,subject_digest:str,assessment_deadline:u256)->u256:
        program=self._program(program_id,program_version)
        if program.retired:_fail("Retired program versions cannot accept assessments")
        subject_id=_text(subject_id,"Subject id",MAX_SUBJECT_ID_CHARS)
        if not _hex64(subject_digest):_fail("Subject digest must be 64 lowercase hexadecimal characters")
        now=_now()
        if int(assessment_deadline)<=int(now)+int(program.challenge_window_seconds):_fail("Assessment deadline must leave the full challenge window")
        if int(assessment_deadline)-int(now)>int(program.max_assessment_horizon_seconds):_fail("Assessment deadline exceeds the program horizon")
        key=_commitment(program_id,program_version,subject_digest)
        if key in self.assessment_commitment_seen:_fail("Assessment commitment already exists")
        assessment_id=self.next_assessment_id; self.next_assessment_id=u256(int(assessment_id)+1); self.assessment_commitment_seen[key]=True
        self.assessments[assessment_id]=AssessmentRecord(requester=_addr(gl.message.sender_address),assessment_id=assessment_id,program_id=program_id,program_version=program_version,subject_id=subject_id,subject_digest=subject_digest,state=REQUESTED,generation=u256(1),evidence_set_hash="",provisional_decision="",challenge_hash="",challenge_deadline=u256(0),assessment_deadline=assessment_deadline,final_decision="",certificate_digest="",issued_at=u256(0),expires_at=u256(0),decision_nonce=u256(0),decision_recorded=False,challenged=False,last_retry_at=u256(0))
        return assessment_id
    @gl.public.view
    def get_assessment_context(self,assessment_id:u256)->str:
        a=self._assessment(assessment_id)
        retry_available_at=int(a.last_retry_at)+RETRY_COOLDOWN_SECONDS if int(a.last_retry_at) else 0
        return json.dumps({"assessment_id":int(a.assessment_id),"requester":_key(a.requester),"program_id":a.program_id,"program_version":int(a.program_version),"subject_id":a.subject_id,"subject_digest":a.subject_digest,"state":a.state,"generation":int(a.generation),"assessment_deadline":int(a.assessment_deadline),"last_retry_at":int(a.last_retry_at),"retry_available_at":retry_available_at},sort_keys=True,separators=(",",":"))
    @gl.public.write
    def open_repair_generation(self,assessment_id:u256)->u256:
        a=self._assessment(assessment_id)
        if a.state not in (REPAIR_REQUIRED,CHALLENGED):_fail("Assessment is not eligible for a fresh generation")
        if int(_now())>=int(a.assessment_deadline):_fail("Expired assessments cannot open a new generation")
        a.generation=u256(int(a.generation)+1); a.state=REQUESTED; a.evidence_set_hash=""; a.provisional_decision=""; a.challenge_deadline=u256(0); a.challenged=False; a.decision_recorded=False; a.last_retry_at=u256(0)
        return a.generation
    @gl.public.write
    def assess(self,assessment_id:u256)->None:
        a=self._assessment(assessment_id)
        if a.state!=REQUESTED:_fail("Assessment is not awaiting evidence")
        if _key(self.evidence_registry_address)==_key(ZERO_ADDRESS):_fail("Evidence Registry is not bound")
        now=_now()
        if int(now)>=int(a.assessment_deadline):_fail("Assessment deadline has passed")
        try:bound=json.loads(CertiMeshEvidenceRegistry(self.evidence_registry_address).view().get_bound_snapshot(assessment_id))
        except Exception:_fail("Evidence binding is unavailable")
        if not bound.get("bound") or int(bound.get("generation",0))!=int(a.generation):_fail("Evidence is not bound for the current generation")
        evidence_set_hash=bound.get("evidence_set_hash","")
        if not _hex64(evidence_set_hash):_fail("Evidence binding is invalid")
        if _key(self.adjudicator_address)==_key(ZERO_ADDRESS):_fail("Adjudicator is not bound")
        a.evidence_set_hash=evidence_set_hash; a.state=EVIDENCE_BOUND; a.last_retry_at=now
        cast(Any,CertiMeshAdjudicator(self.adjudicator_address).emit)(on="finalized").assess(assessment_id,a.generation,evidence_set_hash)
    @gl.public.write
    def retry_assessment(self,assessment_id:u256)->None:
        """Re-dispatch the exact bound review after an adjudicator failure.

        This is deliberately not a new assessment generation: the requester,
        evidence-set hash, and generation remain immutable.  A late callback
        from an earlier dispatch is still accepted only while the assessment
        is EVIDENCE_BOUND and must match those same exact values.
        """
        a=self._assessment(assessment_id)
        if _key(gl.message.sender_address)!=_key(a.requester):_fail("Only the assessment requester can retry")
        if a.state!=EVIDENCE_BOUND:_fail("Only evidence-bound assessments can be retried")
        if _key(self.adjudicator_address)==_key(ZERO_ADDRESS):_fail("Adjudicator is not bound")
        now=_now()
        if int(now)>=int(a.assessment_deadline):_fail("Assessment deadline has passed")
        if int(a.last_retry_at) and int(now)<int(a.last_retry_at)+RETRY_COOLDOWN_SECONDS:_fail("Retry cooldown has not elapsed")
        a.last_retry_at=now
        cast(Any,CertiMeshAdjudicator(self.adjudicator_address).emit)(on="finalized").assess(assessment_id,a.generation,a.evidence_set_hash)
    @gl.public.view
    def get_review_context(self,assessment_id:u256)->str:
        a=self._assessment(assessment_id); p=self._program(a.program_id,a.program_version)
        if _key(self.evidence_registry_address)==_key(ZERO_ADDRESS):_fail("Evidence Registry is not bound")
        records=json.loads(CertiMeshEvidenceRegistry(self.evidence_registry_address).view().get_review_records(assessment_id,a.generation))
        return json.dumps({"assessment":{"assessment_id":int(a.assessment_id),"program_id":a.program_id,"program_version":int(a.program_version),"subject_id":a.subject_id,"subject_digest":a.subject_digest,"generation":int(a.generation),"evidence_set_hash":a.evidence_set_hash,"assessment_deadline":int(a.assessment_deadline)},"program":{"criteria_json":p.criteria_json,"evidence_policy_json":p.evidence_policy_json,"max_evidence_age_seconds":int(p.max_evidence_age_seconds),"challenge_window_seconds":int(p.challenge_window_seconds)},"evidence":records},sort_keys=True,separators=(",",":"))
    @gl.public.write
    def record_assessment_result(self,assessment_id:u256,generation:u256,evidence_set_hash:str,result_status:str,decision:str,failure_code:str,observed_sha256:str)->None:
        if _key(gl.message.sender_address)!=_key(self.adjudicator_address):_fail("Only the bound adjudicator can record an assessment result")
        a=self._assessment(assessment_id)
        if a.state!=EVIDENCE_BOUND or generation!=a.generation or evidence_set_hash!=a.evidence_set_hash:_fail("Assessment result does not match the bound generation")
        if result_status==REPAIR:
            if decision!=REPAIR:_fail("Repair result must use the REPAIR decision")
            a.state=REPAIR_REQUIRED; a.provisional_decision=REPAIR; return
        if result_status!="OK" or decision not in (CERTIFIED,REJECTED):_fail("Unsupported assessment result")
        now=_now()
        if int(now)>=int(a.assessment_deadline):_fail("Assessment deadline has passed")
        p=self._program(a.program_id,a.program_version); a.state=PROVISIONAL; a.provisional_decision=decision; a.challenge_deadline=u256(min(int(now)+int(p.challenge_window_seconds),int(a.assessment_deadline))); a.challenged=False
    @gl.public.write
    def challenge_assessment(self,assessment_id:u256,challenge_material:str)->None:
        a=self._assessment(assessment_id)
        if _key(gl.message.sender_address)!=_key(a.requester):_fail("Only the assessment requester can challenge")
        if a.state!=PROVISIONAL:_fail("Only provisional assessments can be challenged")
        if int(_now())>=int(a.challenge_deadline):_fail("Challenge window has closed")
        a.challenge_hash=_hash(_text(challenge_material,"Challenge material",MAX_TEXT_CHARS)); a.challenged=True; a.state=CHALLENGED
    def _certificate_digest(self,a:AssessmentRecord,issued_at:u256,expires_at:u256,nonce:u256)->str:
        return _hash(json.dumps({"domain":"CERTIMESH_CERTIFICATE_V1","assessment_id":int(a.assessment_id),"program_id":a.program_id,"program_version":int(a.program_version),"subject_digest":a.subject_digest,"evidence_set_hash":a.evidence_set_hash,"final_decision":a.provisional_decision,"issued_at":int(issued_at),"expires_at":int(expires_at),"decision_nonce":int(nonce)},sort_keys=True,separators=(",",":")))
    @gl.public.write
    def finalize_assessment(self,assessment_id:u256)->None:
        a=self._assessment(assessment_id)
        if a.state!=PROVISIONAL or a.challenged:_fail("Only unchallenged provisional assessments can be finalized")
        now=_now()
        if int(now)<=int(a.challenge_deadline):_fail("Challenge window has not closed")
        if int(now)>=int(a.assessment_deadline) or a.decision_recorded:_fail("Assessment cannot be finalized")
        p=self._program(a.program_id,a.program_version); nonce=self.next_decision_nonce; self.next_decision_nonce=u256(int(nonce)+1); a.decision_nonce=nonce; a.final_decision=a.provisional_decision; a.decision_recorded=True; a.state=FINAL
        if a.provisional_decision==CERTIFIED:
            expires_at=u256(int(now)+int(p.certificate_validity_seconds)); digest=self._certificate_digest(a,now,expires_at,nonce)
            if digest in self.used_decisions:_fail("Certificate decision has already been used")
            self.used_decisions[digest]=True; a.certificate_digest=digest; a.issued_at=now; a.expires_at=expires_at
            self.certificates[assessment_id]=CertificateRecord(assessment_id=assessment_id,program_id=a.program_id,program_version=a.program_version,subject_id=a.subject_id,subject_digest=a.subject_digest,evidence_set_hash=a.evidence_set_hash,final_decision=CERTIFIED,issued_at=now,expires_at=expires_at,decision_nonce=nonce,certificate_digest=digest)
    @gl.public.write
    def expire_assessment(self,assessment_id:u256)->None:
        a=self._assessment(assessment_id)
        if a.state in (FINAL,EXPIRED) or int(_now())<int(a.assessment_deadline):_fail("Assessment is not eligible for expiry")
        a.state=EXPIRED; a.final_decision=EXPIRED; a.decision_recorded=True; a.certificate_digest=""
    @gl.public.view
    def get_program(self,program_id:str,version:u256)->ProgramRecord:return self._program(program_id,version)
    @gl.public.view
    def get_assessment(self,assessment_id:u256)->AssessmentRecord:return self._assessment(assessment_id)
    @gl.public.view
    def get_certificate(self,assessment_id:u256)->CertificateRecord:
        if assessment_id not in self.certificates:_fail("No certificate exists for this assessment")
        return self.certificates[assessment_id]
    @gl.public.view
    def get_assessment_count(self)->u256:return u256(int(self.next_assessment_id)-1)
