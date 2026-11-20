from pydantic import BaseModel,Field
from typing import Literal
class ZoneInput(BaseModel):
    production_id:int
    code:str=Field(min_length=2,max_length=40,pattern=r'\S')
    capacity:int=Field(gt=0,le=3000)
    required_staff:int=Field(gt=0,le=80)
    active:bool=True
class PostInput(BaseModel):
    assignment_id:int
    zone_id:int
class IncidentInput(BaseModel):
    performance_id:int
    zone_id:int
    severity:Literal['normal','high']
    description:str=Field(min_length=8,max_length=2000)
class DispatchInput(BaseModel):
    assignment_id:int
class ResolutionInput(BaseModel):
    resolution:str=Field(min_length=8,max_length=2000,pattern=r'\S')
class LostInput(BaseModel):
    performance_id:int
    code:str=Field(min_length=3,max_length=50,pattern=r'\S')
    location:str=Field(min_length=2,max_length=100,pattern=r'\S')
    identifying_detail:str=Field(min_length=4,max_length=1000,pattern=r'\S')
class ClaimInput(BaseModel):
    item_id:int
    claimant:str=Field(min_length=2,max_length=100,pattern=r'\S')
    proof:str=Field(min_length=4,max_length=1000,pattern=r'\S')
