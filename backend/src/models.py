from sqlalchemy import String,Integer,Float,ForeignKey,Date,JSON,CheckConstraint,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from datetime import date as DateValue
from .db import Base
class User(Base):
    __tablename__='users'
    id:Mapped[int]=mapped_column(primary_key=True)
    email:Mapped[str]=mapped_column(String(100),unique=True)
    password_hash:Mapped[str]=mapped_column(String(180))
    role:Mapped[str]=mapped_column(String(20))
class Production(Base):
    __tablename__='productions'
    __table_args__=(CheckConstraint('seats > 0 AND duration_minutes > 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(40),unique=True)
    title:Mapped[str]=mapped_column(String(100))
    seats:Mapped[int]=mapped_column(Integer)
    duration_minutes:Mapped[int]=mapped_column(Integer)
    forecast_state:Mapped[str]=mapped_column(String(20),default='idle')
    forecast_evidence:Mapped[dict|None]=mapped_column(JSON,nullable=True)
class Performance(Base):
    __tablename__='performances'
    __table_args__=(UniqueConstraint('production_id','date'),CheckConstraint('arrivals IS NULL OR arrivals >= 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    production_id:Mapped[int]=mapped_column(ForeignKey('productions.id'))
    date:Mapped[DateValue]=mapped_column(Date)
    curtain:Mapped[str]=mapped_column(String(5),default='19:30')
    arrivals:Mapped[int|None]=mapped_column(Integer,nullable=True)
    raw_forecast:Mapped[float|None]=mapped_column(Float,nullable=True)
    forecast:Mapped[int|None]=mapped_column(Integer,nullable=True)
    status:Mapped[str]=mapped_column(String(20),default='scheduled')
class CrewCall(Base):
    __tablename__='crew_calls'
    __table_args__=(CheckConstraint('ushers > 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    performance_id:Mapped[int]=mapped_column(ForeignKey('performances.id'),unique=True)
    ushers:Mapped[int]=mapped_column(Integer)
    call_time:Mapped[str]=mapped_column(String(30))
    leader:Mapped[str]=mapped_column(String(80))
    status:Mapped[str]=mapped_column(String(20),default='proposed')
class Audit(Base):
    __tablename__='audits'
    id:Mapped[int]=mapped_column(primary_key=True)
    actor:Mapped[str]=mapped_column(String(100))
    action:Mapped[str]=mapped_column(String(200))
    stamp:Mapped[str]=mapped_column(String(40))
