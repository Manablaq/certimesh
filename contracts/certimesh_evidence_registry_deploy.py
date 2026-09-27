# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib
import json
from typing import NoReturn
from genlayer import*
G1=Address('0x0000000000000000000000000000000000000000')
G3='REQUESTED'
G6=1
G0=2
G5=1024
G2=192
G4=1024
@gl.contract_interface
class CertiMeshRegistry:
	class View:
		def get_assessment_context(self,a:u256,/)->str:...
@gl.contract_interface
class CertiMeshProgramRegistry:
	class View:
		def get_program_snapshot(self,a:str,b:u256,/)->str:...
def G9(a):raise gl.vm.UserError(a)
def G12(a):
	if hasattr(a,'as_hex'):return a.as_hex.lower()
	if isinstance(a,(bytes,bytearray,memoryview)):
		c=bytes(a)
		if len(c)!=20:G9('Invalid address')
		return '0x'+c.hex()
	b=str(a).lower()
	if b.startswith('0x')and len(b)==42:return b
	G9('Invalid address')
def G8(a):return a if hasattr(a,'as_hex')else Address(G12(a))
def G11(c,b,a):
	if not isinstance(c,str):G9(f'{b} must be text')
	c=c.strip()
	if not c or len(c)>a:G9(f'{b} is empty or too long')
	return c
def G10(a):return hashlib.sha256(a.encode('utf-8')).hexdigest()
def G7(a):return isinstance(a,str)and len(a)==64 and all((b in '0123456789abcdef' for b in a))
def G13():return u256(int(datetime.now(timezone.utc).timestamp()))
@allow_storage
@dataclass
class EvidenceRecord:
	assessment_id:u256;generation:u256;role:u256;authority:Address;evidence_record_id:str;evidence_record_version:u256;source_url:str;immutable_source_ref:str;evidence_payload_hash:str;source_content_hash:str;published_at:u256;observed_at:u256;expires_at:u256
class CertiMeshEvidenceRegistry(gl.Contract):
	registry_address_value:Address;program_registry_address:Address;evidence:TreeMap[str,EvidenceRecord];present:TreeMap[str,bool];record_seen:TreeMap[str,bool];source_seen:TreeMap[str,bool];bound:TreeMap[u256,bool];bound_generation:TreeMap[u256,u256];bound_hash:TreeMap[u256,str]
	def __init__(self,b:Address,a:Address):
		self.registry_address_value=G8(b);self.program_registry_address=G8(a)
		if G12(self.registry_address_value)==G12(G1)or G12(self.program_registry_address)==G12(G1):G9('Registry addresses cannot be zero')
	@gl.public.view
	def registry_address(self)->Address:return self.registry_address_value
	def m2(self,a):
		try:b=json.loads(CertiMeshRegistry(self.registry_address_value).view().get_assessment_context(a))
		except Exception:G9('Assessment context is unavailable')
		if b.get('state')!=G3:G9('Evidence can only be attested for a requested assessment')
		return b
	def m3(self,a):
		try:return json.loads(CertiMeshProgramRegistry(self.program_registry_address).view().get_program_snapshot(a['program_id'],u256(int(a['program_version']))))
		except Exception:G9('Program is unavailable')
	def m0(self,a,b,c):return f'{int(a)}:{int(b)}:{int(c)}'
	@gl.public.write
	def attest_evidence(self,assessment_id:u256,generation:u256,role:u256,evidence_record_id:str,evidence_record_version:u256,source_url:str,immutable_source_ref:str,evidence_payload_hash:str,source_content_hash:str,published_at:u256,observed_at:u256,expires_at:u256)->None:
		d=self.m2(assessment_id)
		if int(generation)!=int(d['generation']):G9('Wrong evidence generation')
		if int(role)not in(G6,G0):G9('Unsupported evidence role')
		e=self.m3(d);c=e['primary_authority']if int(role)==G6 else e['corroborating_authority']
		if G12(gl.message.sender_address)!=G12(c):G9('Sender is not bound to the evidence role')
		evidence_record_id=G11(evidence_record_id,'Evidence record id',G2);source_url=G11(source_url,'Source URL',G5)
		if not source_url.startswith('https://'):G9('Source URL must use HTTPS')
		immutable_source_ref=G11(immutable_source_ref,'Immutable source reference',G4)
		if not(immutable_source_ref.startswith('https://')or immutable_source_ref.startswith('ipfs://')):G9('Immutable source reference must use HTTPS or IPFS')
		if int(evidence_record_version)<=0 or not G7(evidence_payload_hash)or(not G7(source_content_hash)):G9('Evidence version and hashes are invalid')
		if evidence_payload_hash!=source_content_hash:G9('Evidence payload hash must match source content hash')
		g=G13()
		if int(published_at)>int(observed_at)or int(observed_at)>int(g):G9('Evidence timestamps are invalid')
		if int(g)-int(observed_at)>int(e['max_evidence_age_seconds']):G9('Evidence is stale')
		if int(expires_at)<=int(g)or int(expires_at)<=int(d['assessment_deadline']):G9('Evidence must remain valid through the assessment deadline')
		f=self.m0(assessment_id,generation,role)
		if f in self.present:G9('Evidence role is already attested')
		a=f'{int(assessment_id)}:{int(generation)}:record:{evidence_record_id}';b=f'{int(assessment_id)}:{int(generation)}:source:{immutable_source_ref}'
		if a in self.record_seen or b in self.source_seen:G9('Evidence identity is duplicated')
		self.evidence[f]=EvidenceRecord(assessment_id=assessment_id,generation=generation,role=role,authority=G8(gl.message.sender_address),evidence_record_id=evidence_record_id,evidence_record_version=evidence_record_version,source_url=source_url,immutable_source_ref=immutable_source_ref,evidence_payload_hash=evidence_payload_hash,source_content_hash=source_content_hash,published_at=published_at,observed_at=observed_at,expires_at=expires_at);self.present[f]=True;self.record_seen[a]=True;self.source_seen[b]=True
	def m1(self,a,b):
		e=[]
		for d in(G6,G0):
			f=self.m0(a,b,u256(d))
			if f not in self.present:G9('Exactly two independent evidence records are required')
			c=self.evidence[f];e.append({'role':int(c.role),'authority':G12(c.authority),'record_id':c.evidence_record_id,'record_version':int(c.evidence_record_version),'source_url':c.source_url,'immutable_source_ref':c.immutable_source_ref,'evidence_payload_hash':c.evidence_payload_hash,'source_content_hash':c.source_content_hash,'published_at':int(c.published_at),'observed_at':int(c.observed_at),'expires_at':int(c.expires_at)})
		if e[0]['authority']==e[1]['authority']or e[0]['record_id']==e[1]['record_id']or e[0]['immutable_source_ref']==e[1]['immutable_source_ref']:G9('Evidence sources and authorities must be distinct')
		return G10(json.dumps({'domain':'CERTIMESH_EVIDENCE_SET_V1','assessment_id':int(a),'generation':int(b),'records':e},sort_keys=True,separators=(',',':')))
	@gl.public.write
	def bind_evidence(self,assessment_id:u256)->None:
		b=self.m2(assessment_id)
		if G12(gl.message.sender_address)!=b['requester']:G9('Only the assessment requester can bind evidence')
		a=u256(int(b['generation']));f=G13();c=self.m3(b)
		for e in(G6,G0):
			d=self.evidence[self.m0(assessment_id,a,u256(e))]
			if int(f)-int(d.observed_at)>int(c['max_evidence_age_seconds'])or int(d.expires_at)<=int(f)or int(d.expires_at)<=int(b['assessment_deadline']):G9('Evidence is stale or expires too soon')
		self.bound_hash[assessment_id]=self.m1(assessment_id,a);self.bound_generation[assessment_id]=a;self.bound[assessment_id]=True
	@gl.public.view
	def get_bound_snapshot(self,assessment_id:u256)->str:return json.dumps({'bound':assessment_id in self.bound,'generation':int(self.bound_generation[assessment_id])if assessment_id in self.bound_generation else 0,'evidence_set_hash':self.bound_hash[assessment_id]if assessment_id in self.bound_hash else ''},sort_keys=True,separators=(',',':'))
	@gl.public.view
	def get_review_records(self,assessment_id:u256,generation:u256)->str:
		c=[]
		for b in(G6,G0):
			d=self.m0(assessment_id,generation,u256(b))
			if d not in self.present:G9('Required evidence is unavailable')
			a=self.evidence[d];c.append({'role':int(a.role),'authority':G12(a.authority),'evidence_record_id':a.evidence_record_id,'evidence_record_version':int(a.evidence_record_version),'source_url':a.source_url,'immutable_source_ref':a.immutable_source_ref,'evidence_payload_hash':a.evidence_payload_hash,'source_content_hash':a.source_content_hash,'published_at':int(a.published_at),'observed_at':int(a.observed_at),'expires_at':int(a.expires_at)})
		return json.dumps(c,sort_keys=True,separators=(',',':'))
	@gl.public.view
	def get_evidence(self,assessment_id:u256,generation:u256,role:u256)->EvidenceRecord:
		a=self.m0(assessment_id,generation,role)
		if a not in self.present:G9('Unknown evidence')
		return self.evidence[a]
