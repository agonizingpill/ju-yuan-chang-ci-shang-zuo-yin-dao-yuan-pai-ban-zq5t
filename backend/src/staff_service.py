from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from fastapi import HTTPException
from .models import CrewCall,Performance,Production
from .staff_models import StaffMember,CrewAssignment
from .debrief_models import ShowDebrief
from .services import get,pack,audit

def locked(s,cls,id):
    x=s.scalar(select(cls).where(cls.id==id).with_for_update().execution_options(populate_existing=True))
    if not x:raise HTTPException(404,'人员、点名单或场次不存在')
    return x

def call_context(s,id):
    c=locked(s,CrewCall,id);p=locked(s,Performance,c.performance_id)
    if c.status!='confirmed' or p.status!='crew_confirmed':raise HTTPException(409,'仅经理已确认的点名单可以实名排班与到岗')
    return c,p,get(s,Production,p.production_id)

def occupied(s,c):
    p=get(s,Performance,c.performance_id);prod=get(s,Production,p.production_id)
    return datetime.fromisoformat(c.call_time),datetime.fromisoformat(p.date.isoformat()+'T'+p.curtain)+timedelta(minutes=prod.duration_minutes+30)

def assignment_view(s,x):
    c=s.get(CrewCall,x.crew_call_id);p=s.get(Performance,c.performance_id)
    return pack(x)|{'performance_id':p.id,'date':p.date.isoformat(),'call_time':c.call_time,'production_id':p.production_id}

def assign(s,d,u):
    staff=locked(s,StaffMember,d.staff_id);c,p,prod=call_context(s,d.crew_call_id)
    if not staff.active:raise HTTPException(409,'人员已停用，不能排入当班')
    if s.scalar(select(ShowDebrief.id).where(ShowDebrief.performance_id==p.id)):raise HTTPException(409,'已有散场交接，实名班表冻结')
    existing=s.scalars(select(CrewAssignment).where(CrewAssignment.crew_call_id==c.id)).all()
    if any(x.staff_id==staff.id for x in existing):raise HTTPException(409,'同一人员不能重复排入本场')
    if len(existing)>=c.ushers:raise HTTPException(409,'实名人员已达到点名单配置人数')
    others=s.scalars(select(CrewAssignment).where(CrewAssignment.staff_id==staff.id)).all();start,end=occupied(s,c);daily=0
    for x in others:
        other=get(s,CrewCall,x.crew_call_id)
        a,b=occupied(s,other)
        if a.date()==start.date():daily+=1
        if start<b and a<end:raise HTTPException(409,'该人员已在另一场值班，含散场30分钟的时段重叠')
    if daily>=staff.max_daily_calls:raise HTTPException(409,'已达到该人员当日可用场次数上限')
    x=CrewAssignment(**d.model_dump(),staff_code=staff.code,staff_name=staff.name);s.add(x);s.flush();audit(s,u,f'实名排班 {staff.code}→点名#{c.id}');return assignment_view(s,x)

def checkin(s,id,d,u):
    preview=get(s,CrewAssignment,id);staff=locked(s,StaffMember,preview.staff_id);c,p,prod=call_context(s,preview.crew_call_id);x=locked(s,CrewAssignment,id)
    if x.checked_in:raise HTTPException(409,'人员已经签到，不能重复登记或改写时间')
    if not staff.active:raise HTTPException(409,'人员已停用，请经理核对当班人员')
    if s.scalar(select(ShowDebrief.id).where(ShowDebrief.performance_id==p.id)):raise HTTPException(409,'已有散场交接，签到证据冻结')
    call_time=datetime.fromisoformat(c.call_time)
    if not call_time-timedelta(minutes=15)<=d.observed_at<=call_time+timedelta(minutes=15):raise HTTPException(409,'到岗时间须在点名时刻前后15分钟内')
    x.checked_in=True;x.observed_at=d.observed_at.isoformat();x.recorded_at=datetime.now(timezone.utc).isoformat();x.recorded_by=u.email;audit(s,u,f'实名到岗 {x.staff_code} #{c.id}');return assignment_view(s,x)
