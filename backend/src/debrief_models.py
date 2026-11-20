from sqlalchemy import String,Integer,Float,Text,ForeignKey,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
class ShowDebrief(Base):
    __tablename__='show_debriefs'
    __table_args__=(CheckConstraint('actual_attendance >= 0 AND exit_minutes >= 0'),CheckConstraint("state in ('draft','archived')"),)
    id:Mapped[int]=mapped_column(primary_key=True)
    performance_id:Mapped[int]=mapped_column(ForeignKey('performances.id'),unique=True)
    actual_attendance:Mapped[int]=mapped_column(Integer)
    exit_minutes:Mapped[float]=mapped_column(Float)
    incident_note:Mapped[str]=mapped_column(Text,default='')
    forecast_snapshot:Mapped[int]=mapped_column(Integer)
    required_staff:Mapped[int]=mapped_column(Integer)
    checked_in_snapshot:Mapped[int]=mapped_column(Integer)
    variance_pct:Mapped[float]=mapped_column(Float)
    state:Mapped[str]=mapped_column(String(20),default='draft')
    archived_by:Mapped[str|None]=mapped_column(String(100),nullable=True)
    archived_at:Mapped[str|None]=mapped_column(String(40),nullable=True)
