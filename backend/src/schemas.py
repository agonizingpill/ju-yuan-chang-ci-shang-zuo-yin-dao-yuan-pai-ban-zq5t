from pydantic import BaseModel,Field
from datetime import date,datetime
class Login(BaseModel):
    email:str
    password:str
class ProductionInput(BaseModel):
    code:str=Field(min_length=1,max_length=40)
    title:str=Field(min_length=1,max_length=100)
    seats:int=Field(ge=20,le=3000)
    duration_minutes:int=Field(ge=15,le=300)
class PerformanceInput(BaseModel):
    production_id:int
    date:date
    curtain:str=Field(default='19:30',pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    arrivals:int|None=Field(default=None,ge=0,le=3000)
class ArrivalInput(BaseModel):
    arrivals:int=Field(ge=0,le=3000)
class CrewInput(BaseModel):
    performance_id:int
    ushers:int=Field(ge=1,le=80)
    call_time:datetime
    leader:str=Field(min_length=1,max_length=80)
