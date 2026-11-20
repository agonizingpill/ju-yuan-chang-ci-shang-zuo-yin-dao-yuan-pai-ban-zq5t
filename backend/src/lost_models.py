from sqlalchemy import String,Text,ForeignKey,CheckConstraint,Index,text
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
class LostItem(Base):
    __tablename__='lost_items'
    __table_args__=(CheckConstraint("state in ('stored','handed_over')"),)
    id:Mapped[int]=mapped_column(primary_key=True)
    performance_id:Mapped[int]=mapped_column(ForeignKey('performances.id'))
    code:Mapped[str]=mapped_column(String(50),unique=True)
    location:Mapped[str]=mapped_column(String(100))
    identifying_detail:Mapped[str]=mapped_column(Text)
    state:Mapped[str]=mapped_column(String(20),default='stored')
class ItemClaim(Base):
    __tablename__='item_claims'
    __table_args__=(CheckConstraint("state in ('pending','handed_over')"),Index('one_handover_per_item','item_id',unique=True,postgresql_where=text("state = 'handed_over'")))
    id:Mapped[int]=mapped_column(primary_key=True)
    item_id:Mapped[int]=mapped_column(ForeignKey('lost_items.id'))
    claimant:Mapped[str]=mapped_column(String(100))
    proof:Mapped[str]=mapped_column(Text)
    state:Mapped[str]=mapped_column(String(20),default='pending')
    handed_by:Mapped[str|None]=mapped_column(String(100),nullable=True)
