from datetime import datetime
from pydantic import BaseModel,Field,field_validator
class StaffInput(BaseModel):
    code:str=Field(min_length=2,max_length=40)
    name:str=Field(min_length=1,max_length=80)
    active:bool=True
    max_daily_calls:int=Field(default=2,ge=1,le=8)
    @field_validator('code','name')
    @classmethod
    def nonblank(cls,v):
        if not v.strip():raise ValueError('人员编号与姓名不能为空')
        return v.strip()
class AssignmentInput(BaseModel):
    crew_call_id:int
    staff_id:int
class CheckinInput(BaseModel):
    observed_at:datetime
    @field_validator('observed_at')
    @classmethod
    def local_only(cls,v):
        if v.tzinfo is not None:raise ValueError('使用剧场当地时间，不附时区')
        return v
class DebriefInput(BaseModel):
    performance_id:int
    actual_attendance:int=Field(ge=0,le=3000)
    exit_minutes:float=Field(ge=0,le=240,allow_inf_nan=False)
    incident_note:str=Field(default='',max_length=2000)
