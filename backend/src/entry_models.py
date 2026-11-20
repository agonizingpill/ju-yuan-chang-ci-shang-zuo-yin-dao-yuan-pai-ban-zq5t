from sqlalchemy import String,Integer,ForeignKey,UniqueConstraint,CheckConstraint,Boolean,JSON,DateTime
from sqlalchemy.orm import Mapped,mapped_column
from datetime import datetime,timezone
from .db import Base

# 开场前一小时每 10 分钟一段，共 6 段；开场前更早与开场后迟到入场合并为“其余”一段。
# slot_index 0..5 = 开场前 60..51、50..41、40..31、30..21、20..11、10..0 分钟；
# slot_index 6 = 其余（开场 60 分钟以前，或开场以后迟到验票）。
PRE_SLOT_COUNT=6
SLOT_MINUTES=10
OTHER_SLOT_INDEX=6
SLOT_COUNT=7

def utcnow():
    # 统一存 naive UTC，便于跨库（SQLite/PostgreSQL）做绝对时刻比较
    return datetime.now(timezone.utc).replace(tzinfo=None)

class EntrySegment(Base):
    __tablename__='entry_segments'
    __table_args__=(
        UniqueConstraint('performance_id','slot_index'),
        CheckConstraint(f'slot_index >= 0 AND slot_index < {SLOT_COUNT}'),
        CheckConstraint('headcount >= 0'),
    )
    id:Mapped[int]=mapped_column(primary_key=True)
    performance_id:Mapped[int]=mapped_column(ForeignKey('performances.id'))
    slot_index:Mapped[int]=mapped_column(Integer)
    headcount:Mapped[int]=mapped_column(Integer)
    # 该段验票实际发生时刻（迟到补录也归到实际验票时段，而不是补录时刻）
    observed_at:Mapped[str]=mapped_column(String(30))
    recorded_at:Mapped[str]=mapped_column(String(40))
    recorded_by:Mapped[str]=mapped_column(String(100))
    is_final:Mapped[bool]=mapped_column(Boolean,default=False)
    finalized_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)

class EntryRecommendation(Base):
    __tablename__='entry_recommendations'
    __table_args__=(
        CheckConstraint('sample_size >= 0'),
    )
    id:Mapped[int]=mapped_column(primary_key=True)
    performance_id:Mapped[int]=mapped_column(ForeignKey('performances.id'))
    production_id:Mapped[int]=mapped_column(ForeignKey('productions.id'))
    version:Mapped[int]=mapped_column(Integer,default=1)
    is_active:Mapped[bool]=mapped_column(Boolean,default=True)
    status:Mapped[str]=mapped_column(String(20),default='ready')  # ready / insufficient
    sample_size:Mapped[int]=mapped_column(Integer,default=0)
    # 分段均值、高峰段与加岗时段的完整快照
    detail:Mapped[dict]=mapped_column(JSON)
    reason:Mapped[str|None]=mapped_column(String(500),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
