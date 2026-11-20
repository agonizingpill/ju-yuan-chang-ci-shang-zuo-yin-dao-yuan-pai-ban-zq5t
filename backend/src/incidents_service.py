from fastapi import HTTPException
from sqlalchemy import select
from .incident_models import HouseIncident
from .zone_models import EntranceZone
from .staff_models import CrewAssignment
from .models import CrewCall
from .debrief_models import ShowDebrief
from .zones_service import performance_context
from .staff_service import locked
from .services import pack,audit

def view(s,x):return pack(x)|{'zone_code':s.get(EntranceZone,x.zone_id).code}
def create(s,d,u):
    c,p,prod=performance_context(s,d.performance_id)
    if s.scalar(select(ShowDebrief.id).where(ShowDebrief.performance_id==p.id,ShowDebrief.state=='archived')):raise HTTPException(409,'本场交接已归档，不能追加现场事件')
    z=locked(s,EntranceZone,d.zone_id)
    if z.production_id!=p.production_id or not z.active:raise HTTPException(409,'事件分区不属于本场或未启用')
    x=HouseIncident(**d.model_dump());s.add(x);s.flush();audit(s,u,'登记现场事件 '+str(x.id));return view(s,x)
def context(s,id):
    x=s.get(HouseIncident,id)
    if not x:raise HTTPException(404,'事件不存在')
    performance_context(s,x.performance_id);return locked(s,HouseIncident,id)
def dispatch(s,id,d,u):
    x=context(s,id)
    if x.state!='open':raise HTTPException(409,'仅新事件可以分派，已分派不能重复')
    a=locked(s,CrewAssignment,d.assignment_id);c=s.get(CrewCall,a.crew_call_id)
    if c.performance_id!=x.performance_id or not a.checked_in:raise HTTPException(409,'处置人须是同一场已实名到岗人员')
    x.assignee_id=a.id;x.state='assigned';audit(s,u,f'分派事件 #{id}→{a.staff_code}');return view(s,x)
def resolve(s,id,d,u):
    x=context(s,id)
    if x.state!='assigned':raise HTTPException(409,'须先由经理分派处置人，且不能重复处理')
    if len(d.resolution.strip())<8:raise HTTPException(409,'处置说明至少8字')
    x.resolution=d.resolution.strip();x.state='resolved';audit(s,u,f'登记事件处置 #{id}');return view(s,x)
def close(s,id,u):
    x=context(s,id)
    if x.state!='resolved':raise HTTPException(409,'须先分派并填写处置说明，已关闭不能重复')
    x.state='closed';x.closed_by=u.email;audit(s,u,f'经理关闭事件 #{id}');return view(s,x)
def ensure_clear(s,performance_id):
    if s.scalar(select(HouseIncident.id).where(HouseIncident.performance_id==performance_id,HouseIncident.severity=='high',HouseIncident.state!='closed')):raise HTTPException(409,'高风险现场事件尚未经理关闭，不能归档交接')
