from sqlalchemy import String,Integer,Boolean,ForeignKey,UniqueConstraint,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
class StaffMember(Base):
    __tablename__='staff_members'
    __table_args__=(CheckConstraint('max_daily_calls BETWEEN 1 AND 8'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(40),unique=True)
    name:Mapped[str]=mapped_column(String(80))
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    max_daily_calls:Mapped[int]=mapped_column(Integer,default=2)
class CrewAssignment(Base):
    __tablename__='crew_assignments'
    __table_args__=(UniqueConstraint('crew_call_id','staff_id'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    crew_call_id:Mapped[int]=mapped_column(ForeignKey('crew_calls.id'))
    staff_id:Mapped[int]=mapped_column(ForeignKey('staff_members.id'))
    staff_code:Mapped[str]=mapped_column(String(40))
    staff_name:Mapped[str]=mapped_column(String(80))
    checked_in:Mapped[bool]=mapped_column(Boolean,default=False)
    observed_at:Mapped[str|None]=mapped_column(String(30),nullable=True)
    recorded_at:Mapped[str|None]=mapped_column(String(40),nullable=True)
    recorded_by:Mapped[str|None]=mapped_column(String(100),nullable=True)
