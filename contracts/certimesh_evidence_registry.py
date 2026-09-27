# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""CertiMesh immutable evidence binding registry."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import NoReturn
from genlayer import *

ZERO_ADDRESS=Address("0x0000000000000000000000000000000000000000"); REQUESTED="REQUESTED"; PRIMARY=1; CORROBORATING=2; MAX_URI=1024; MAX_RECORD=192; MAX_REF=1024

@gl.contract_interface
class CertiMeshRegistry:
    class View:
        def get_assessment_context(self,assessment_id:u256,/)->str:...
@gl.contract_interface
class CertiMeshProgramRegistry:
    class View:
        def get_program_snapshot(self,program_id:str,version:u256,/)->str:...

def _fail(message:str)->NoReturn:raise gl.vm.UserError(message)
def _key(address:Address)->str:
    if hasattr(address,"as_hex"):return address.as_hex.lower()
    if isinstance(address,(bytes,bytearray,memoryview)):
        raw=bytes(address)
        if len(raw)!=20:_fail("Invalid address")
        return "0x"+raw.hex()
    value=str(address).lower()
    if value.startswith("0x") and len(value)==42:return value
    _fail("Invalid address")
def _addr(address:Address)->Address:return address if hasattr(address,"as_hex") else Address(_key(address))
def _text(value:str,label:str,maximum:int)->str:
    if not isinstance(value,str):_fail(f"{label} must be text")
    value=value.strip()
    if not value or len(value)>maximum:_fail(f"{label} is empty or too long")
    return value
def _hash(value:str)->str:return hashlib.sha256(value.encode("utf-8")).hexdigest()
def _hex64(value:str)->bool:return isinstance(value,str) and len(value)==64 and all(c in "0123456789abcdef" for c in value)
def _now()->u256:return u256(int(datetime.now(timezone.utc).timestamp()))

@allow_storage
@dataclass
class EvidenceRecord:
    assessment_id:u256; generation:u256; role:u256; authority:Address; evidence_record_id:str; evidence_record_version:u256; source_url:str; immutable_source_ref:str; evidence_payload_hash:str; source_content_hash:str; published_at:u256; observed_at:u256; expires_at:u256

class CertiMeshEvidenceRegistry(gl.Contract):
    registry_address_value:Address; program_registry_address:Address; evidence:TreeMap[str,EvidenceRecord]; present:TreeMap[str,bool]; record_seen:TreeMap[str,bool]; source_seen:TreeMap[str,bool]; bound:TreeMap[u256,bool]; bound_generation:TreeMap[u256,u256]; bound_hash:TreeMap[u256,str]
    def __init__(self,registry_address:Address,program_registry_address:Address):
        self.registry_address_value=_addr(registry_address); self.program_registry_address=_addr(program_registry_address)
        if _key(self.registry_address_value)==_key(ZERO_ADDRESS) or _key(self.program_registry_address)==_key(ZERO_ADDRESS):_fail("Registry addresses cannot be zero")
    @gl.public.view
    def registry_address(self)->Address:return self.registry_address_value
    def _context(self,assessment_id:u256)->dict:
        try:value=json.loads(CertiMeshRegistry(self.registry_address_value).view().get_assessment_context(assessment_id))
        except Exception:_fail("Assessment context is unavailable")
        if value.get("state")!=REQUESTED:_fail("Evidence can only be attested for a requested assessment")
        return value
    def _program(self,context:dict)->dict:
        try:return json.loads(CertiMeshProgramRegistry(self.program_registry_address).view().get_program_snapshot(context["program_id"],u256(int(context["program_version"]))))
        except Exception:_fail("Program is unavailable")
    def _evidence_key(self,assessment_id:u256,generation:u256,role:u256)->str:return f"{int(assessment_id)}:{int(generation)}:{int(role)}"
    @gl.public.write
    def attest_evidence(self,assessment_id:u256,generation:u256,role:u256,evidence_record_id:str,evidence_record_version:u256,source_url:str,immutable_source_ref:str,evidence_payload_hash:str,source_content_hash:str,published_at:u256,observed_at:u256,expires_at:u256)->None:
        context=self._context(assessment_id)
        if int(generation)!=int(context["generation"]):_fail("Wrong evidence generation")
        if int(role) not in (PRIMARY,CORROBORATING):_fail("Unsupported evidence role")
        program=self._program(context); authority=program["primary_authority"] if int(role)==PRIMARY else program["corroborating_authority"]
        if _key(gl.message.sender_address)!=_key(authority):_fail("Sender is not bound to the evidence role")
        evidence_record_id=_text(evidence_record_id,"Evidence record id",MAX_RECORD); source_url=_text(source_url,"Source URL",MAX_URI)
        if not source_url.startswith("https://"):_fail("Source URL must use HTTPS")
        immutable_source_ref=_text(immutable_source_ref,"Immutable source reference",MAX_REF)
        if not (immutable_source_ref.startswith("https://") or immutable_source_ref.startswith("ipfs://")):_fail("Immutable source reference must use HTTPS or IPFS")
        if int(evidence_record_version)<=0 or not _hex64(evidence_payload_hash) or not _hex64(source_content_hash):_fail("Evidence version and hashes are invalid")
        if evidence_payload_hash!=source_content_hash:_fail("Evidence payload hash must match source content hash")
        now=_now()
        if int(published_at)>int(observed_at) or int(observed_at)>int(now):_fail("Evidence timestamps are invalid")
        if int(now)-int(observed_at)>int(program["max_evidence_age_seconds"]):_fail("Evidence is stale")
        if int(expires_at)<=int(now) or int(expires_at)<=int(context["assessment_deadline"]):_fail("Evidence must remain valid through the assessment deadline")
        key=self._evidence_key(assessment_id,generation,role)
        if key in self.present:_fail("Evidence role is already attested")
        record_key=f"{int(assessment_id)}:{int(generation)}:record:{evidence_record_id}"; source_key=f"{int(assessment_id)}:{int(generation)}:source:{immutable_source_ref}"
        if record_key in self.record_seen or source_key in self.source_seen:_fail("Evidence identity is duplicated")
        self.evidence[key]=EvidenceRecord(assessment_id=assessment_id,generation=generation,role=role,authority=_addr(gl.message.sender_address),evidence_record_id=evidence_record_id,evidence_record_version=evidence_record_version,source_url=source_url,immutable_source_ref=immutable_source_ref,evidence_payload_hash=evidence_payload_hash,source_content_hash=source_content_hash,published_at=published_at,observed_at=observed_at,expires_at=expires_at)
        self.present[key]=True; self.record_seen[record_key]=True; self.source_seen[source_key]=True
    def _bound_hash(self,assessment_id:u256,generation:u256)->str:
        rows=[]
        for role in (PRIMARY,CORROBORATING):
            key=self._evidence_key(assessment_id,generation,u256(role))
            if key not in self.present:_fail("Exactly two independent evidence records are required")
            record=self.evidence[key]
            rows.append({"role":int(record.role),"authority":_key(record.authority),"record_id":record.evidence_record_id,"record_version":int(record.evidence_record_version),"source_url":record.source_url,"immutable_source_ref":record.immutable_source_ref,"evidence_payload_hash":record.evidence_payload_hash,"source_content_hash":record.source_content_hash,"published_at":int(record.published_at),"observed_at":int(record.observed_at),"expires_at":int(record.expires_at)})
        if rows[0]["authority"]==rows[1]["authority"] or rows[0]["record_id"]==rows[1]["record_id"] or rows[0]["immutable_source_ref"]==rows[1]["immutable_source_ref"]:_fail("Evidence sources and authorities must be distinct")
        return _hash(json.dumps({"domain":"CERTIMESH_EVIDENCE_SET_V1","assessment_id":int(assessment_id),"generation":int(generation),"records":rows},sort_keys=True,separators=(",",":")))
    @gl.public.write
    def bind_evidence(self,assessment_id:u256)->None:
        context=self._context(assessment_id)
        if _key(gl.message.sender_address)!=context["requester"]:_fail("Only the assessment requester can bind evidence")
        generation=u256(int(context["generation"])); now=_now(); program=self._program(context)
        for role in (PRIMARY,CORROBORATING):
            record=self.evidence[self._evidence_key(assessment_id,generation,u256(role))]
            if int(now)-int(record.observed_at)>int(program["max_evidence_age_seconds"]) or int(record.expires_at)<=int(now) or int(record.expires_at)<=int(context["assessment_deadline"]):_fail("Evidence is stale or expires too soon")
        self.bound_hash[assessment_id]=self._bound_hash(assessment_id,generation); self.bound_generation[assessment_id]=generation; self.bound[assessment_id]=True
    @gl.public.view
    def get_bound_snapshot(self,assessment_id:u256)->str:return json.dumps({"bound":assessment_id in self.bound,"generation":int(self.bound_generation[assessment_id]) if assessment_id in self.bound_generation else 0,"evidence_set_hash":self.bound_hash[assessment_id] if assessment_id in self.bound_hash else ""},sort_keys=True,separators=(",",":"))
    @gl.public.view
    def get_review_records(self,assessment_id:u256,generation:u256)->str:
        rows=[]
        for role in (PRIMARY,CORROBORATING):
            key=self._evidence_key(assessment_id,generation,u256(role))
            if key not in self.present:_fail("Required evidence is unavailable")
            record=self.evidence[key]
            rows.append({"role":int(record.role),"authority":_key(record.authority),"evidence_record_id":record.evidence_record_id,"evidence_record_version":int(record.evidence_record_version),"source_url":record.source_url,"immutable_source_ref":record.immutable_source_ref,"evidence_payload_hash":record.evidence_payload_hash,"source_content_hash":record.source_content_hash,"published_at":int(record.published_at),"observed_at":int(record.observed_at),"expires_at":int(record.expires_at)})
        return json.dumps(rows,sort_keys=True,separators=(",",":"))
    @gl.public.view
    def get_evidence(self,assessment_id:u256,generation:u256,role:u256)->EvidenceRecord:
        key=self._evidence_key(assessment_id,generation,role)
        if key not in self.present:_fail("Unknown evidence")
        return self.evidence[key]
