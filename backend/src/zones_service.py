from fastapi import HTTPException
from sqlalchemy import select
from .models import Production,Performance,CrewCall
from .staff_models import CrewAssignment
from .debrief_models import ShowDebrief
from .zone_models import EntranceZone,ZonePost
from .staff_service import locked,call_context
from .services import pack,audit

def production_lock(s,id):return locked(s,Production,id)
def performance_context(s,id):
    p=s.get(Performance,id)
    if not p:raise HTTPException(404,'演出场次不存在')
    c=s.scalar(select(CrewCall).where(CrewCall.performance_id==id))
    if not c:raise HTTPException(409,'请先确认本场点名')
    return call_context(s,c.id)
def mutable(s,id):
    if s.scalar(select(ShowDebrief.id).where(ShowDebrief.performance_id==id)):raise HTTPException(409,'已填写散场交接，本场岗位与现场事件登记冻结')
def create(s,d,u):
    prod=production_lock(s,d.production_id)
    if s.scalar(select(ShowDebrief.id).join(Performance,Performance.id==ShowDebrief.performance_id).where(Performance.production_id==prod.id,ShowDebrief.state=='draft')):raise HTTPException(409,'该剧目有待归档交接，暂不能增加分区')
    zones=s.scalars(select(EntranceZone).where(EntranceZone.production_id==prod.id)).all()
    if sum(x.capacity for x in zones)+d.capacity>prod.seats:raise HTTPException(409,'入口分区容量合计超过剧目座位')
    x=EntranceZone(**d.model_dump());s.add(x);s.flush();audit(s,u,'配置入口分区 '+d.code);return pack(x)
def post_view(s,x):
    a=s.get(CrewAssignment,x.assignment_id);c=s.get(CrewCall,a.crew_call_id);p=s.get(Performance,c.performance_id);z=s.get(EntranceZone,x.zone_id)
    return pack(x)|{'staff_name':a.staff_name,'performance_id':p.id,'production_id':p.production_id,'date':p.date.isoformat(),'zone_code':z.code}
def post(s,d,u):
    a=s.get(CrewAssignment,d.assignment_id)
    if not a:raise HTTPException(404,'实名班表不存在')
    c,p,prod=performance_context(s,s.get(CrewCall,a.crew_call_id).performance_id);production_lock(s,prod.id);mutable(s,p.id);a=locked(s,CrewAssignment,d.assignment_id);z=locked(s,EntranceZone,d.zone_id)
    if not a.checked_in:raise HTTPException(409,'只有实名已到岗人员才可安排入口岗位')
    if z.production_id!=p.production_id or not z.active:raise HTTPException(409,'分区不属于本剧目或未启用')
    if s.scalar(select(ZonePost.id).where(ZonePost.assignment_id==a.id)):raise HTTPException(409,'该人员本场已有入口岗位，不得重复')
    x=ZonePost(**d.model_dump());s.add(x);s.flush();audit(s,u,f'入口岗位 {a.staff_code}→{z.code}');return post_view(s,x)
def coverage(s,performance_id):
    p=s.get(Performance,performance_id);production_lock(s,p.production_id)
    zones=s.scalars(select(EntranceZone).where(EntranceZone.production_id==p.production_id,EntranceZone.active==True)).all()
    if not zones:raise HTTPException(409,'新交接须先配置启用入口分区并安排实名岗位')
    rows=s.execute(select(ZonePost.zone_id,CrewAssignment.id).join(CrewAssignment,CrewAssignment.id==ZonePost.assignment_id).join(CrewCall,CrewCall.id==CrewAssignment.crew_call_id).where(CrewCall.performance_id==p.id,CrewAssignment.checked_in==True)).all()
    for z in zones:
        if sum(zone==z.id for zone,_ in rows)<z.required_staff:raise HTTPException(409,f'入口{z.code}岗位不足，至少需{z.required_staff}名实名到岗人员')
