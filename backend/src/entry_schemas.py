from pydantic import BaseModel,Field
from datetime import datetime
from typing import Literal

class SegmentInput(BaseModel):
    performance_id:int
    # 实际验票时刻（剧场本地时间，不带时区）；迟到补录也按此时刻归入实际时段
    observed_at:datetime
    headcount:int=Field(ge=0,le=3000)

class SegmentBatchItem(BaseModel):
    slot_index:int=Field(ge=0,le=6)
    headcount:int=Field(ge=0,le=3000)

class SegmentBatchInput(BaseModel):
    performance_id:int
    observed_at:datetime
    segments:list[SegmentBatchItem]=Field(min_length=1)

class FinalizeInput(BaseModel):
    performance_id:int

class GenerateInput(BaseModel):
    performance_id:int
