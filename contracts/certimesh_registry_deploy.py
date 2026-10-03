# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib
import json
from typing import Any,NoReturn,cast
from genlayer import*
G5=Address('0x0000000000000000000000000000000000000000')
G10='REQUESTED'
G3='EVIDENCE_BOUND'
G6='PROVISIONAL'
G8='CHALLENGED'
G2='REPAIR_REQUIRED'
G16='FINAL'
G13='EXPIRED'
G9='CERTIFIED'
G11='REJECTED'
G14='REPAIR'
G1=256
G4=4000
G0=1800
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
def G18(a):raise gl.vm.UserError(a)
def G22():return u256(int(datetime.now(timezone.utc).timestamp()))
def G21(a):
	if hasattr(a,'as_hex'):return a.as_hex.lower()
	if isinstance(a,(bytes,bytearray,memoryview)):
		c=bytes(a)
		if len(c)!=20:G18('Invalid address')
		return '0x'+c.hex()
	b=str(a).lower()
	if b.startswith('0x')and len(b)==42:return b
	G18('Invalid address')
def G17(a):return a if hasattr(a,'as_hex')else Address(G21(a))
def G12(a,b):
	if G21(a)==G21(G5):G18(f'{b} cannot be the zero address')
def G20(c,b,a):
	if not isinstance(c,str):G18(f'{b} must be text')
	c=c.strip()
	if not c or len(c)>a:G18(f'{b} is empty or too long')
	return c
def G19(a):return hashlib.sha256(a.encode('utf-8')).hexdigest()
def G15(a):return isinstance(a,str)and len(a)==64 and all((b in '0123456789abcdef' for b in a))
def G7(b,c,a):return G19(json.dumps({'domain':'CERTIMESH_ASSESSMENT_COMMITMENT_V1','program_id':b,'program_version':int(c),'subject_digest':a},sort_keys=True,separators=(',',':')))
@allow_storage
@dataclass
class ProgramRecord:
	creator:Address;program_id:str;version:u256;criteria_json:str;evidence_policy_json:str;primary_authority:Address;corroborating_authority:Address;challenge_window_seconds:u256;max_evidence_age_seconds:u256;certificate_validity_seconds:u256;max_assessment_horizon_seconds:u256;retired:bool
@allow_storage
@dataclass
class AssessmentRecord:
	requester:Address;assessment_id:u256;program_id:str;program_version:u256;subject_id:str;subject_digest:str;state:str;generation:u256;evidence_set_hash:str;provisional_decision:str;challenge_hash:str;challenge_deadline:u256;assessment_deadline:u256;final_decision:str;certificate_digest:str;issued_at:u256;expires_at:u256;decision_nonce:u256;decision_recorded:bool;challenged:bool;last_retry_at:u256
@allow_storage
@dataclass
class CertificateRecord:
	assessment_id:u256;program_id:str;program_version:u256;subject_id:str;subject_digest:str;evidence_set_hash:str;final_decision:str;issued_at:u256;expires_at:u256;decision_nonce:u256;certificate_digest:str
class CertiMeshRegistry(gl.Contract):
	owner:Address;program_registry_address:Address;evidence_registry_address:Address;adjudicator_address:Address;assessments:TreeMap[u256,AssessmentRecord];assessment_commitment_seen:TreeMap[str,bool];certificates:TreeMap[u256,CertificateRecord];used_decisions:TreeMap[str,bool];next_assessment_id:u256;next_decision_nonce:u256
	def __init__(self,a:Address):
		a=G17(a);G12(a,'Program Registry');self.owner=gl.message.sender_address;self.program_registry_address=a;self.evidence_registry_address=G5;self.adjudicator_address=G5;self.next_assessment_id=u256(1);self.next_decision_nonce=u256(1)
	@gl.public.view
	def get_adjudicator_address(self)->Address:return self.adjudicator_address
	@gl.public.view
	def get_evidence_registry_address(self)->Address:return self.evidence_registry_address
	@gl.public.write
	def bind_evidence_registry(self,evidence_registry_address:Address)->None:
		if G21(gl.message.sender_address)!=G21(self.owner):G18('Only the registry owner can bind the evidence registry')
		if G21(self.evidence_registry_address)!=G21(G5):G18('Evidence Registry is already bound')
		a=G17(evidence_registry_address);G12(a,'Evidence Registry')
		try:b=CertiMeshEvidenceRegistry(a).view().registry_address()
		except Exception:G18('Evidence Registry reciprocal binding check failed')
		if G21(b)!=G21(gl.message.contract_address):G18('Evidence Registry is bound to a different registry')
		self.evidence_registry_address=a
	@gl.public.write
	def bind_adjudicator(self,adjudicator_address:Address)->None:
		if G21(gl.message.sender_address)!=G21(self.owner):G18('Only the registry owner can bind the adjudicator')
		if G21(self.adjudicator_address)!=G21(G5):G18('Adjudicator is already bound')
		a=G17(adjudicator_address);G12(a,'Adjudicator')
		try:b=CertiMeshAdjudicator(a).view().registry_address()
		except Exception:G18('Adjudicator reciprocal binding check failed')
		if G21(b)!=G21(gl.message.contract_address):G18('Adjudicator is bound to a different registry')
		self.adjudicator_address=a
	def m2(self,a,b):
		try:
			c=json.loads(CertiMeshProgramRegistry(self.program_registry_address).view().get_program_snapshot(a,b));return ProgramRecord(creator=G17(c['creator']),program_id=c['program_id'],version=u256(int(c['version'])),criteria_json=c['criteria_json'],evidence_policy_json=c['evidence_policy_json'],primary_authority=G17(c['primary_authority']),corroborating_authority=G17(c['corroborating_authority']),challenge_window_seconds=u256(int(c['challenge_window_seconds'])),max_evidence_age_seconds=u256(int(c['max_evidence_age_seconds'])),certificate_validity_seconds=u256(int(c['certificate_validity_seconds'])),max_assessment_horizon_seconds=u256(int(c['max_assessment_horizon_seconds'])),retired=bool(c['retired']))
		except Exception:G18('Unknown program version')
	def m1(self,a):
		if a not in self.assessments:G18('Unknown assessment')
		return self.assessments[a]
	@gl.public.write
	def create_assessment(self,program_id:str,program_version:u256,subject_id:str,subject_digest:str,assessment_deadline:u256)->u256:
		b=self.m2(program_id,program_version)
		if b.retired:G18('Retired program versions cannot accept assessments')
		subject_id=G20(subject_id,'Subject id',G1)
		if not G15(subject_digest):G18('Subject digest must be 64 lowercase hexadecimal characters')
		d=G22()
		if int(assessment_deadline)<=int(d)+int(b.challenge_window_seconds):G18('Assessment deadline must leave the full challenge window')
		if int(assessment_deadline)-int(d)>int(b.max_assessment_horizon_seconds):G18('Assessment deadline exceeds the program horizon')
		c=G7(program_id,program_version,subject_digest)
		if c in self.assessment_commitment_seen:G18('Assessment commitment already exists')
		a=self.next_assessment_id;self.next_assessment_id=u256(int(a)+1);self.assessment_commitment_seen[c]=True;self.assessments[a]=AssessmentRecord(requester=G17(gl.message.sender_address),assessment_id=a,program_id=program_id,program_version=program_version,subject_id=subject_id,subject_digest=subject_digest,state=G10,generation=u256(1),evidence_set_hash='',provisional_decision='',challenge_hash='',challenge_deadline=u256(0),assessment_deadline=assessment_deadline,final_decision='',certificate_digest='',issued_at=u256(0),expires_at=u256(0),decision_nonce=u256(0),decision_recorded=False,challenged=False,last_retry_at=u256(0));return a
	@gl.public.view
	def get_assessment_context(self,assessment_id:u256)->str:
		c=self.m1(assessment_id);b=int(c.last_retry_at)+G0 if int(c.last_retry_at)else 0;return json.dumps({'assessment_id':int(c.assessment_id),'requester':G21(c.requester),'program_id':c.program_id,'program_version':int(c.program_version),'subject_id':c.subject_id,'subject_digest':c.subject_digest,'state':c.state,'generation':int(c.generation),'assessment_deadline':int(c.assessment_deadline),'last_retry_at':int(c.last_retry_at),'retry_available_at':b},sort_keys=True,separators=(',',':'))
	@gl.public.write
	def open_repair_generation(self,assessment_id:u256)->u256:
		b=self.m1(assessment_id)
		if b.state not in(G2,G8):G18('Assessment is not eligible for a fresh generation')
		if int(G22())>=int(b.assessment_deadline):G18('Expired assessments cannot open a new generation')
		b.generation=u256(int(b.generation)+1);b.state=G10;b.evidence_set_hash='';b.provisional_decision='';b.challenge_deadline=u256(0);b.challenged=False;b.decision_recorded=False;b.last_retry_at=u256(0);return b.generation
	@gl.public.write
	def assess(self,assessment_id:u256)->None:
		e=self.m1(assessment_id)
		if e.state!=G10:G18('Assessment is not awaiting evidence')
		if G21(self.evidence_registry_address)==G21(G5):G18('Evidence Registry is not bound')
		d=G22()
		if int(d)>=int(e.assessment_deadline):G18('Assessment deadline has passed')
		try:c=json.loads(CertiMeshEvidenceRegistry(self.evidence_registry_address).view().get_bound_snapshot(assessment_id))
		except Exception:G18('Evidence binding is unavailable')
		if not c.get('bound')or int(c.get('generation',0))!=int(e.generation):G18('Evidence is not bound for the current generation')
		b=c.get('evidence_set_hash','')
		if not G15(b):G18('Evidence binding is invalid')
		if G21(self.adjudicator_address)==G21(G5):G18('Adjudicator is not bound')
		e.evidence_set_hash=b;e.state=G3;e.last_retry_at=d;cast(Any,CertiMeshAdjudicator(self.adjudicator_address).emit)(on='finalized').assess(assessment_id,e.generation,b)
	@gl.public.write
	def retry_assessment(self,assessment_id:u256)->None:
		c=self.m1(assessment_id)
		if G21(gl.message.sender_address)!=G21(c.requester):G18('Only the assessment requester can retry')
		if c.state!=G3:G18('Only evidence-bound assessments can be retried')
		if G21(self.adjudicator_address)==G21(G5):G18('Adjudicator is not bound')
		b=G22()
		if int(b)>=int(c.assessment_deadline):G18('Assessment deadline has passed')
		if int(c.last_retry_at)and int(b)<int(c.last_retry_at)+G0:G18('Retry cooldown has not elapsed')
		c.last_retry_at=b;cast(Any,CertiMeshAdjudicator(self.adjudicator_address).emit)(on='finalized').assess(assessment_id,c.generation,c.evidence_set_hash)
	@gl.public.view
	def get_review_context(self,assessment_id:u256)->str:
		c=self.m1(assessment_id);d=self.m2(c.program_id,c.program_version)
		if G21(self.evidence_registry_address)==G21(G5):G18('Evidence Registry is not bound')
		b=json.loads(CertiMeshEvidenceRegistry(self.evidence_registry_address).view().get_review_records(assessment_id,c.generation));return json.dumps({'assessment':{'assessment_id':int(c.assessment_id),'program_id':c.program_id,'program_version':int(c.program_version),'subject_id':c.subject_id,'subject_digest':c.subject_digest,'generation':int(c.generation),'evidence_set_hash':c.evidence_set_hash,'assessment_deadline':int(c.assessment_deadline)},'program':{'criteria_json':d.criteria_json,'evidence_policy_json':d.evidence_policy_json,'max_evidence_age_seconds':int(d.max_evidence_age_seconds),'challenge_window_seconds':int(d.challenge_window_seconds)},'evidence':b},sort_keys=True,separators=(',',':'))
	@gl.public.write
	def record_assessment_result(self,assessment_id:u256,generation:u256,evidence_set_hash:str,result_status:str,decision:str,failure_code:str,observed_sha256:str)->None:
		if G21(gl.message.sender_address)!=G21(self.adjudicator_address):G18('Only the bound adjudicator can record an assessment result')
		c=self.m1(assessment_id)
		if c.state!=G3 or generation!=c.generation or evidence_set_hash!=c.evidence_set_hash:G18('Assessment result does not match the bound generation')
		if result_status==G14:
			if decision!=G14:G18('Repair result must use the REPAIR decision')
			c.state=G2;c.provisional_decision=G14;return
		if result_status!='OK' or decision not in(G9,G11):G18('Unsupported assessment result')
		b=G22()
		if int(b)>=int(c.assessment_deadline):G18('Assessment deadline has passed')
		d=self.m2(c.program_id,c.program_version);c.state=G6;c.provisional_decision=decision;c.challenge_deadline=u256(min(int(b)+int(d.challenge_window_seconds),int(c.assessment_deadline)));c.challenged=False
	@gl.public.write
	def challenge_assessment(self,assessment_id:u256,challenge_material:str)->None:
		b=self.m1(assessment_id)
		if G21(gl.message.sender_address)!=G21(b.requester):G18('Only the assessment requester can challenge')
		if b.state!=G6:G18('Only provisional assessments can be challenged')
		if int(G22())>=int(b.challenge_deadline):G18('Challenge window has closed')
		b.challenge_hash=G19(G20(challenge_material,'Challenge material',G4));b.challenged=True;b.state=G8
	def m0(self,e,c,b,d):return G19(json.dumps({'domain':'CERTIMESH_CERTIFICATE_V1','assessment_id':int(e.assessment_id),'program_id':e.program_id,'program_version':int(e.program_version),'subject_digest':e.subject_digest,'evidence_set_hash':e.evidence_set_hash,'final_decision':e.provisional_decision,'issued_at':int(c),'expires_at':int(b),'decision_nonce':int(d)},sort_keys=True,separators=(',',':')))
	@gl.public.write
	def finalize_assessment(self,assessment_id:u256)->None:
		f=self.m1(assessment_id)
		if f.state!=G6 or f.challenged:G18('Only unchallenged provisional assessments can be finalized')
		e=G22()
		if int(e)<=int(f.challenge_deadline):G18('Challenge window has not closed')
		if int(e)>=int(f.assessment_deadline)or f.decision_recorded:G18('Assessment cannot be finalized')
		g=self.m2(f.program_id,f.program_version);d=self.next_decision_nonce;self.next_decision_nonce=u256(int(d)+1);f.decision_nonce=d;f.final_decision=f.provisional_decision;f.decision_recorded=True;f.state=G16
		if f.provisional_decision==G9:
			b=u256(int(e)+int(g.certificate_validity_seconds));c=self.m0(f,e,b,d)
			if c in self.used_decisions:G18('Certificate decision has already been used')
			self.used_decisions[c]=True;f.certificate_digest=c;f.issued_at=e;f.expires_at=b;self.certificates[assessment_id]=CertificateRecord(assessment_id=assessment_id,program_id=f.program_id,program_version=f.program_version,subject_id=f.subject_id,subject_digest=f.subject_digest,evidence_set_hash=f.evidence_set_hash,final_decision=G9,issued_at=e,expires_at=b,decision_nonce=d,certificate_digest=c)
	@gl.public.write
	def expire_assessment(self,assessment_id:u256)->None:
		b=self.m1(assessment_id)
		if b.state in(G16,G13)or int(G22())<int(b.assessment_deadline):G18('Assessment is not eligible for expiry')
		b.state=G13;b.final_decision=G13;b.decision_recorded=True;b.certificate_digest=''
	@gl.public.view
	def get_program(self,program_id:str,version:u256)->ProgramRecord:return self.m2(program_id,version)
	@gl.public.view
	def get_assessment(self,assessment_id:u256)->AssessmentRecord:return self.m1(assessment_id)
	@gl.public.view
	def get_certificate(self,assessment_id:u256)->CertificateRecord:
		if assessment_id not in self.certificates:G18('No certificate exists for this assessment')
		return self.certificates[assessment_id]
	@gl.public.view
	def get_assessment_count(self)->u256:return u256(int(self.next_assessment_id)-1)
