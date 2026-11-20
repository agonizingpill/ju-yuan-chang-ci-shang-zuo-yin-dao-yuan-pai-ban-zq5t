from sqlalchemy import String,Integer,Boolean,ForeignKey,UniqueConstraint,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
class EntranceZone(Base):
    __tablename__='entrance_zones'
    __table_args__=(UniqueConstraint('production_id','code'),CheckConstraint('capacity > 0 AND required_staff > 0'))
    id:Mapped[int]=mapped_column(primary_key=True)
    production_id:Mapped[int]=mapped_column(ForeignKey('productions.id'))
    code:Mapped[str]=mapped_column(String(40))
    capacity:Mapped[int]=mapped_column(Integer)
    required_staff:Mapped[int]=mapped_column(Integer)
    active:Mapped[bool]=mapped_column(Boolean,default=True)
class ZonePost(Base):
    __tablename__='zone_posts'
    id:Mapped[int]=mapped_column(primary_key=True)
    assignment_id:Mapped[int]=mapped_column(ForeignKey('crew_assignments.id'),unique=True)
    zone_id:Mapped[int]=mapped_column(ForeignKey('entrance_zones.id'))
