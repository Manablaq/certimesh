# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib
import json
from typing import NoReturn
from genlayer import*
G4=Address('0x0000000000000000000000000000000000000000')
G2=128
G3=24000
G1=60
G0=30*24*60*60
def G8(a):raise gl.vm.UserError(a)
def G5(a):
	if hasattr(a,'as_hex'):return a.as_hex.lower()
	if isinstance(a,(bytes,bytearray,memoryview)):
		b=bytes(a)
		if len(b)!=20:G8('Invalid address')
		return '0x'+b.hex()
	b=str(a).lower()
	if b.startswith('0x')and len(b)==42:return b
	G8('Invalid address')
def G6(a):return a if hasattr(a,'as_hex')else Address(G5(a))
def G7(c,b,a):
	if not isinstance(c,str):G8(f'{b} must be text')
	c=c.strip()
	if not c or len(c)>a:G8(f'{b} is empty or too long')
	return c
def G9(c,b):
	c=G7(c,b,G3)
	try:a=json.loads(c)
	except Exception:G8(f'{b} must be valid JSON')
	if not isinstance(a,(dict,list))or not a:G8(f'{b} must be a non-empty JSON object or array')
	return c
def G11(a):return hashlib.sha256(a.encode('utf-8')).hexdigest()
def G10(a,b):return f'{a}:{int(b)}'
@allow_storage
@dataclass
class ProgramRecord:
	creator:Address;program_id:str;version:u256;criteria_json:str;evidence_policy_json:str;criteria_hash:str;evidence_policy_hash:str;authority_set_hash:str;primary_authority:Address;corroborating_authority:Address;challenge_window_seconds:u256;max_evidence_age_seconds:u256;certificate_validity_seconds:u256;max_assessment_horizon_seconds:u256;retired:bool;created_at:str
class CertiMeshProgramRegistry(gl.Contract):
	programs:TreeMap[str,ProgramRecord];latest_program_version:TreeMap[str,u256]
	def __init__(self):pass
	def m2(self,a,b):
		c=G10(a,b)
		if c not in self.programs:G8('Unknown program version')
		return self.programs[c]
	def m0(self,f,e,c,d,b,a):
		f=G6(f);e=G6(e)
		if G5(f)==G5(G4)or G5(e)==G5(G4):G8('Authorities cannot be zero addresses')
		if G5(f)==G5(e):G8('Authorities must be distinct')
		if not G1<=int(c)<=G0:G8('Challenge window is outside the supported range')
		if int(d)<=0 or int(b)<=0:G8('Program durations must be positive')
		if int(a)<=int(c):G8('Assessment horizon must exceed challenge window')
	def m3(self,i,j,h,f,g,e,c,d,b,a):
		i=G7(i,'Program id',G2);h=G9(h,'Criteria');f=G9(f,'Evidence policy');self.m0(g,e,c,d,b,a);k=G10(i,j)
		if k in self.programs:G8('Program version already exists')
		g=G6(g);e=G6(e);self.programs[k]=ProgramRecord(creator=G6(gl.message.sender_address),program_id=i,version=j,criteria_json=h,evidence_policy_json=f,criteria_hash=G11(h),evidence_policy_hash=G11(f),authority_set_hash=G11(json.dumps({'primary':G5(g),'corroborating':G5(e)},sort_keys=True,separators=(',',':'))),primary_authority=g,corroborating_authority=e,challenge_window_seconds=c,max_evidence_age_seconds=d,certificate_validity_seconds=b,max_assessment_horizon_seconds=a,retired=False,created_at=str(datetime.now(timezone.utc).isoformat()));self.latest_program_version[i]=j;return j
	@gl.public.write
	def create_program(self,program_id:str,criteria_json:str,evidence_policy_json:str,primary_authority:Address,corroborating_authority:Address,challenge_window_seconds:u256,max_evidence_age_seconds:u256,certificate_validity_seconds:u256,max_assessment_horizon_seconds:u256)->u256:
		program_id=G7(program_id,'Program id',G2)
		if program_id in self.latest_program_version:G8('Program already exists')
		return self.m3(program_id,u256(1),criteria_json,evidence_policy_json,primary_authority,corroborating_authority,challenge_window_seconds,max_evidence_age_seconds,certificate_validity_seconds,max_assessment_horizon_seconds)
	@gl.public.write
	def create_program_version(self,program_id:str,criteria_json:str,evidence_policy_json:str,primary_authority:Address,corroborating_authority:Address,challenge_window_seconds:u256,max_evidence_age_seconds:u256,certificate_validity_seconds:u256,max_assessment_horizon_seconds:u256)->u256:
		program_id=G7(program_id,'Program id',G2)
		if program_id not in self.latest_program_version:G8('Unknown program')
		a=self.m2(program_id,self.latest_program_version[program_id])
		if G5(gl.message.sender_address)!=G5(a.creator):G8('Only the program creator can create a version')
		return self.m3(program_id,u256(int(self.latest_program_version[program_id])+1),criteria_json,evidence_policy_json,primary_authority,corroborating_authority,challenge_window_seconds,max_evidence_age_seconds,certificate_validity_seconds,max_assessment_horizon_seconds)
	@gl.public.write
	def retire_program_version(self,program_id:str,version:u256)->None:
		a=self.m2(program_id,version)
		if G5(gl.message.sender_address)!=G5(a.creator):G8('Only the program creator can retire a version')
		if a.retired:G8('Program version is already retired')
		a.retired=True
	def m1(self,a):return json.dumps({'creator':G5(a.creator),'program_id':a.program_id,'version':int(a.version),'criteria_json':a.criteria_json,'evidence_policy_json':a.evidence_policy_json,'criteria_hash':a.criteria_hash,'evidence_policy_hash':a.evidence_policy_hash,'authority_set_hash':a.authority_set_hash,'primary_authority':G5(a.primary_authority),'corroborating_authority':G5(a.corroborating_authority),'challenge_window_seconds':int(a.challenge_window_seconds),'max_evidence_age_seconds':int(a.max_evidence_age_seconds),'certificate_validity_seconds':int(a.certificate_validity_seconds),'max_assessment_horizon_seconds':int(a.max_assessment_horizon_seconds),'retired':a.retired,'created_at':a.created_at},sort_keys=True,separators=(',',':'))
	@gl.public.view
	def get_program(self,program_id:str,version:u256)->ProgramRecord:return self.m2(program_id,version)
	@gl.public.view
	def get_program_snapshot(self,program_id:str,version:u256)->str:return self.m1(self.m2(program_id,version))
	@gl.public.view
	def get_latest_program_version(self,program_id:str)->u256:
		if program_id not in self.latest_program_version:G8('Unknown program')
		return self.latest_program_version[program_id]
