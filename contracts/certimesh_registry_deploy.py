# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib
import json
from typing import Any,NoReturn,cast
from genlayer import*
G4=Address('0x0000000000000000000000000000000000000000')
G9='REQUESTED'
G2='EVIDENCE_BOUND'
G5='PROVISIONAL'
G7='CHALLENGED'
G1='REPAIR_REQUIRED'
G15='FINAL'
G12='EXPIRED'
G8='CERTIFIED'
G10='REJECTED'
G13='REPAIR'
G0=256
G3=4000
@gl.contract_interface
class CertiMeshProgramRegistry:
	class View:
		def get_program_snapshot(self,a:str,b:u256,/)->str:...
@gl.contract_interface
class CertiMeshEvidenceRegistry:
	class View:
		def registry_address(self,/)->Address:...
		def get_bound_snapshot(self,a:u256,/)->str:...
		def get_review_records(self,a:u256,b:u256,/)->str:...
@gl.contract_interface
class CertiMeshAdjudicator:
	class View:
		def registry_address(self,/)->Address:...
	class Write:
		def assess(self,b:u256,c:u256,a:str,/)->None:...
def G17(a):raise gl.vm.UserError(a)
def G21():return u256(int(datetime.now(timezone.utc).timestamp()))
def G20(a):
	if hasattr(a,'as_hex'):return a.as_hex.lower()
	if isinstance(a,(bytes,bytearray,memoryview)):
		c=bytes(a)
		if len(c)!=20:G17('Invalid address')
		return '0x'+c.hex()
	b=str(a).lower()
	if b.startswith('0x')and len(b)==42:return b
	G17('Invalid address')
def G16(a):return a if hasattr(a,'as_hex')else Address(G20(a))
def G11(a,b):
	if G20(a)==G20(G4):G17(f'{b} cannot be the zero address')
def G19(c,b,a):
	if not isinstance(c,str):G17(f'{b} must be text')
	c=c.strip()
	if not c or len(c)>a:G17(f'{b} is empty or too long')
	return c
def G18(a):return hashlib.sha256(a.encode('utf-8')).hexdigest()
def G14(a):return isinstance(a,str)and len(a)==64 and all((b in '0123456789abcdef' for b in a))
def G6(b,c,a):return G18(json.dumps({'domain':'CERTIMESH_ASSESSMENT_COMMITMENT_V1','program_id':b,'program_version':int(c),'subject_digest':a},sort_keys=True,separators=(',',':')))
@allow_storage
@dataclass
class ProgramRecord:
	creator:Address;program_id:str;version:u256;criteria_json:str;evidence_policy_json:str;primary_authority:Address;corroborating_authority:Address;challenge_window_seconds:u256;max_evidence_age_seconds:u256;certificate_validity_seconds:u256;max_assessment_horizon_seconds:u256;retired:bool
@allow_storage
@dataclass
class AssessmentRecord:
	requester:Address;assessment_id:u256;program_id:str;program_version:u256;subject_id:str;subject_digest:str;state:str;generation:u256;evidence_set_hash:str;provisional_decision:str;challenge_hash:str;challenge_deadline:u256;assessment_deadline:u256;final_decision:str;certificate_digest:str;issued_at:u256;expires_at:u256;decision_nonce:u256;decision_recorded:bool;challenged:bool
@allow_storage
@dataclass
class CertificateRecord:
	assessment_id:u256;program_id:str;program_version:u256;subject_id:str;subject_digest:str;evidence_set_hash:str;final_decision:str;issued_at:u256;expires_at:u256;decision_nonce:u256;certificate_digest:str
class CertiMeshRegistry(gl.Contract):
	owner:Address;program_registry_address:Address;evidence_registry_address:Address;adjudicator_address:Address;assessments:TreeMap[u256,AssessmentRecord];assessment_commitment_seen:TreeMap[str,bool];certificates:TreeMap[u256,CertificateRecord];used_decisions:TreeMap[str,bool];next_assessment_id:u256;next_decision_nonce:u256
	def __init__(self,a:Address):
		a=G16(a);G11(a,'Program Registry');self.owner=gl.message.sender_address;self.program_registry_address=a;self.evidence_registry_address=G4;self.adjudicator_address=G4;self.next_assessment_id=u256(1);self.next_decision_nonce=u256(1)
	@gl.public.view
	def get_adjudicator_address(self)->Address:return self.adjudicator_address
	@gl.public.view
	def get_evidence_registry_address(self)->Address:return self.evidence_registry_address
	@gl.public.write
	def bind_evidence_registry(self,evidence_registry_address:Address)->None:
		if G20(gl.message.sender_address)!=G20(self.owner):G17('Only the registry owner can bind the evidence registry')
		if G20(self.evidence_registry_address)!=G20(G4):G17('Evidence Registry is already bound')
		a=G16(evidence_registry_address);G11(a,'Evidence Registry')
		try:b=CertiMeshEvidenceRegistry(a).view().registry_address()
		except Exception:G17('Evidence Registry reciprocal binding check failed')
		if G20(b)!=G20(gl.message.contract_address):G17('Evidence Registry is bound to a different registry')
		self.evidence_registry_address=a
	@gl.public.write
	def bind_adjudicator(self,adjudicator_address:Address)->None:
		if G20(gl.message.sender_address)!=G20(self.owner):G17('Only the registry owner can bind the adjudicator')
		if G20(self.adjudicator_address)!=G20(G4):G17('Adjudicator is already bound')
		a=G16(adjudicator_address);G11(a,'Adjudicator')
		try:b=CertiMeshAdjudicator(a).view().registry_address()
		except Exception:G17('Adjudicator reciprocal binding check failed')
		if G20(b)!=G20(gl.message.contract_address):G17('Adjudicator is bound to a different registry')
		self.adjudicator_address=a
	def m2(self,a,b):
		try:
			c=json.loads(CertiMeshProgramRegistry(self.program_registry_address).view().get_program_snapshot(a,b));return ProgramRecord(creator=G16(c['creator']),program_id=c['program_id'],version=u256(int(c['version'])),criteria_json=c['criteria_json'],evidence_policy_json=c['evidence_policy_json'],primary_authority=G16(c['primary_authority']),corroborating_authority=G16(c['corroborating_authority']),challenge_window_seconds=u256(int(c['challenge_window_seconds'])),max_evidence_age_seconds=u256(int(c['max_evidence_age_seconds'])),certificate_validity_seconds=u256(int(c['certificate_validity_seconds'])),max_assessment_horizon_seconds=u256(int(c['max_assessment_horizon_seconds'])),retired=bool(c['retired']))
		except Exception:G17('Unknown program version')
	def m1(self,a):
		if a not in self.assessments:G17('Unknown assessment')
		return self.assessments[a]
	@gl.public.write
	def create_assessment(self,program_id:str,program_version:u256,subject_id:str,subject_digest:str,assessment_deadline:u256)->u256:
		b=self.m2(program_id,program_version)
		if b.retired:G17('Retired program versions cannot accept assessments')
		subject_id=G19(subject_id,'Subject id',G0)
		if not G14(subject_digest):G17('Subject digest must be 64 lowercase hexadecimal characters')
		d=G21()
		if int(assessment_deadline)<=int(d)+int(b.challenge_window_seconds):G17('Assessment deadline must leave the full challenge window')
		if int(assessment_deadline)-int(d)>int(b.max_assessment_horizon_seconds):G17('Assessment deadline exceeds the program horizon')
		c=G6(program_id,program_version,subject_digest)
		if c in self.assessment_commitment_seen:G17('Assessment commitment already exists')
		a=self.next_assessment_id;self.next_assessment_id=u256(int(a)+1);self.assessment_commitment_seen[c]=True;self.assessments[a]=AssessmentRecord(requester=G16(gl.message.sender_address),assessment_id=a,program_id=program_id,program_version=program_version,subject_id=subject_id,subject_digest=subject_digest,state=G9,generation=u256(1),evidence_set_hash='',provisional_decision='',challenge_hash='',challenge_deadline=u256(0),assessment_deadline=assessment_deadline,final_decision='',certificate_digest='',issued_at=u256(0),expires_at=u256(0),decision_nonce=u256(0),decision_recorded=False,challenged=False);return a
	@gl.public.view
	def get_assessment_context(self,assessment_id:u256)->str:
		b=self.m1(assessment_id);return json.dumps({'assessment_id':int(b.assessment_id),'requester':G20(b.requester),'program_id':b.program_id,'program_version':int(b.program_version),'subject_id':b.subject_id,'subject_digest':b.subject_digest,'state':b.state,'generation':int(b.generation),'assessment_deadline':int(b.assessment_deadline)},sort_keys=True,separators=(',',':'))
	@gl.public.write
	def open_repair_generation(self,assessment_id:u256)->u256:
		b=self.m1(assessment_id)
		if b.state not in(G1,G7):G17('Assessment is not eligible for a fresh generation')
		if int(G21())>=int(b.assessment_deadline):G17('Expired assessments cannot open a new generation')
		b.generation=u256(int(b.generation)+1);b.state=G9;b.evidence_set_hash='';b.provisional_decision='';b.challenge_deadline=u256(0);b.challenged=False;b.decision_recorded=False;return b.generation
	@gl.public.write
	def assess(self,assessment_id:u256)->None:
		e=self.m1(assessment_id)
		if e.state!=G9:G17('Assessment is not awaiting evidence')
		if G20(self.evidence_registry_address)==G20(G4):G17('Evidence Registry is not bound')
		d=G21()
		if int(d)>=int(e.assessment_deadline):G17('Assessment deadline has passed')
		try:c=json.loads(CertiMeshEvidenceRegistry(self.evidence_registry_address).view().get_bound_snapshot(assessment_id))
		except Exception:G17('Evidence binding is unavailable')
		if not c.get('bound')or int(c.get('generation',0))!=int(e.generation):G17('Evidence is not bound for the current generation')
		b=c.get('evidence_set_hash','')
		if not G14(b):G17('Evidence binding is invalid')
		if G20(self.adjudicator_address)==G20(G4):G17('Adjudicator is not bound')
		e.evidence_set_hash=b;e.state=G2;cast(Any,CertiMeshAdjudicator(self.adjudicator_address).emit)(on='finalized').assess(assessment_id,e.generation,b)
	@gl.public.view
	def get_review_context(self,assessment_id:u256)->str:
		c=self.m1(assessment_id);d=self.m2(c.program_id,c.program_version)
		if G20(self.evidence_registry_address)==G20(G4):G17('Evidence Registry is not bound')
		b=json.loads(CertiMeshEvidenceRegistry(self.evidence_registry_address).view().get_review_records(assessment_id,c.generation));return json.dumps({'assessment':{'assessment_id':int(c.assessment_id),'program_id':c.program_id,'program_version':int(c.program_version),'subject_id':c.subject_id,'subject_digest':c.subject_digest,'generation':int(c.generation),'evidence_set_hash':c.evidence_set_hash,'assessment_deadline':int(c.assessment_deadline)},'program':{'criteria_json':d.criteria_json,'evidence_policy_json':d.evidence_policy_json,'max_evidence_age_seconds':int(d.max_evidence_age_seconds),'challenge_window_seconds':int(d.challenge_window_seconds)},'evidence':b},sort_keys=True,separators=(',',':'))
	@gl.public.write
	def record_assessment_result(self,assessment_id:u256,generation:u256,evidence_set_hash:str,result_status:str,decision:str,failure_code:str,observed_sha256:str)->None:
		if G20(gl.message.sender_address)!=G20(self.adjudicator_address):G17('Only the bound adjudicator can record an assessment result')
		c=self.m1(assessment_id)
		if c.state!=G2 or generation!=c.generation or evidence_set_hash!=c.evidence_set_hash:G17('Assessment result does not match the bound generation')
		if result_status==G13:
			if decision!=G13:G17('Repair result must use the REPAIR decision')
			c.state=G1;c.provisional_decision=G13;return
		if result_status!='OK' or decision not in(G8,G10):G17('Unsupported assessment result')
		b=G21()
		if int(b)>=int(c.assessment_deadline):G17('Assessment deadline has passed')
		d=self.m2(c.program_id,c.program_version);c.state=G5;c.provisional_decision=decision;c.challenge_deadline=u256(min(int(b)+int(d.challenge_window_seconds),int(c.assessment_deadline)));c.challenged=False
	@gl.public.write
	def challenge_assessment(self,assessment_id:u256,challenge_material:str)->None:
		b=self.m1(assessment_id)
		if G20(gl.message.sender_address)!=G20(b.requester):G17('Only the assessment requester can challenge')
		if b.state!=G5:G17('Only provisional assessments can be challenged')
		if int(G21())>=int(b.challenge_deadline):G17('Challenge window has closed')
		b.challenge_hash=G18(G19(challenge_material,'Challenge material',G3));b.challenged=True;b.state=G7
	def m0(self,e,c,b,d):return G18(json.dumps({'domain':'CERTIMESH_CERTIFICATE_V1','assessment_id':int(e.assessment_id),'program_id':e.program_id,'program_version':int(e.program_version),'subject_digest':e.subject_digest,'evidence_set_hash':e.evidence_set_hash,'final_decision':e.provisional_decision,'issued_at':int(c),'expires_at':int(b),'decision_nonce':int(d)},sort_keys=True,separators=(',',':')))
	@gl.public.write
	def finalize_assessment(self,assessment_id:u256)->None:
		f=self.m1(assessment_id)
		if f.state!=G5 or f.challenged:G17('Only unchallenged provisional assessments can be finalized')
		e=G21()
		if int(e)<=int(f.challenge_deadline):G17('Challenge window has not closed')
		if int(e)>=int(f.assessment_deadline)or f.decision_recorded:G17('Assessment cannot be finalized')
		g=self.m2(f.program_id,f.program_version);d=self.next_decision_nonce;self.next_decision_nonce=u256(int(d)+1);f.decision_nonce=d;f.final_decision=f.provisional_decision;f.decision_recorded=True;f.state=G15
		if f.provisional_decision==G8:
			b=u256(int(e)+int(g.certificate_validity_seconds));c=self.m0(f,e,b,d)
			if c in self.used_decisions:G17('Certificate decision has already been used')
			self.used_decisions[c]=True;f.certificate_digest=c;f.issued_at=e;f.expires_at=b;self.certificates[assessment_id]=CertificateRecord(assessment_id=assessment_id,program_id=f.program_id,program_version=f.program_version,subject_id=f.subject_id,subject_digest=f.subject_digest,evidence_set_hash=f.evidence_set_hash,final_decision=G8,issued_at=e,expires_at=b,decision_nonce=d,certificate_digest=c)
	@gl.public.write
	def expire_assessment(self,assessment_id:u256)->None:
		b=self.m1(assessment_id)
		if b.state in(G15,G12)or int(G21())<int(b.assessment_deadline):G17('Assessment is not eligible for expiry')
		b.state=G12;b.final_decision=G12;b.decision_recorded=True;b.certificate_digest=''
	@gl.public.view
	def get_program(self,program_id:str,version:u256)->ProgramRecord:return self.m2(program_id,version)
	@gl.public.view
	def get_assessment(self,assessment_id:u256)->AssessmentRecord:return self.m1(assessment_id)
	@gl.public.view
	def get_certificate(self,assessment_id:u256)->CertificateRecord:
		if assessment_id not in self.certificates:G17('No certificate exists for this assessment')
		return self.certificates[assessment_id]
	@gl.public.view
	def get_assessment_count(self)->u256:return u256(int(self.next_assessment_id)-1)
