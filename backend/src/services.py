from datetime import datetime,timedelta,timezone,date
from math import ceil
from fastapi import HTTPException
from sqlalchemy import select
from .models import Production,Performance,CrewCall,Audit

def get(s,cls,id):
    obj=s.get(cls,id)
    if not obj:raise HTTPException(404,'记录不存在')
    return obj
def pack(v):
    return {c.name:(getattr(v,c.name).isoformat() if isinstance(getattr(v,c.name),date) else getattr(v,c.name)) for c in v.__table__.columns}
def audit(s,u,action):s.add(Audit(actor=u.email,action=action,stamp=datetime.now(timezone.utc).isoformat()))
def history(s,pid):return s.scalars(select(Performance).where(Performance.production_id==pid,Performance.arrivals.is_not(None)).order_by(Performance.date)).all()
def validate_history(rows):
    if len(rows)<28:raise HTTPException(409,'至少需要 28 天完整验票记录')
    for a,b in zip(rows,rows[1:]):
        if b.date-a.date!=timedelta(days=1):raise HTTPException(409,f'验票日历缺口：{(a.date+timedelta(days=1)).isoformat()}；请先补齐')

def invalidate(s,production):
    if production.forecast_state=='calculating':raise HTTPException(409,'预测进行中，请稍后修改验票输入')
    perfs=s.scalars(select(Performance).where(Performance.production_id==production.id,Performance.arrivals.is_(None))).all()
    if any(p.status=='crew_confirmed' for p in perfs):raise HTTPException(409,'已有确认点名，历史与剧目输入已冻结')
    for p in perfs:
        p.forecast=None;p.raw_forecast=None;p.status='scheduled'
        call=s.scalar(select(CrewCall).where(CrewCall.performance_id==p.id))
        if call:call.status='invalidated'
    production.forecast_state='idle';production.forecast_evidence=None

def save_crew(s,data):
    perf=get(s,Performance,data['performance_id'])
    production=get(s,Production,perf.production_id)
    if production.forecast_state=='calculating':raise HTTPException(409,'预测更新中，暂不能编制点名')
    if perf.status!='forecasted' or perf.forecast is None:raise HTTPException(409,'请先为本场完成上座预测；已确认场次不能改班')
    curtain=datetime.fromisoformat(perf.date.isoformat()+'T'+perf.curtain)
    call=data['call_time'].replace(tzinfo=None)
    if call>curtain-timedelta(minutes=30) or call<curtain-timedelta(hours=6):raise HTTPException(409,'点名须在开场前 30 分钟至 6 小时内')
    v=s.scalar(select(CrewCall).where(CrewCall.performance_id==perf.id))
    if v and v.status=='confirmed':raise HTTPException(409,'已确认点名不可修改')
    if not v:v=CrewCall(performance_id=perf.id,ushers=data['ushers'],call_time=call.isoformat(),leader=data['leader']);s.add(v)
    else:v.ushers=data['ushers'];v.call_time=call.isoformat();v.leader=data['leader'];v.status='proposed'
    return v

def confirm(s,cid):
    call=s.query(CrewCall).filter_by(id=cid).with_for_update().one_or_none()
    if not call:raise HTTPException(404,'点名单不存在')
    perf=s.query(Performance).filter_by(id=call.performance_id).with_for_update().one()
    prod=get(s,Production,perf.production_id)
    if call.status!='proposed' or perf.status!='forecasted' or prod.forecast_state!='ready':raise HTTPException(409,'点名或预测证据已失效，请重新编排')
    need=max(1,ceil(perf.forecast/40))
    if call.ushers<need:raise HTTPException(409,f'引导员不足：预计 {perf.forecast} 人，至少需 {need} 名')
    if perf.forecast>prod.seats:raise HTTPException(409,'本场预测超过座位数，请重新核对容量')
    call.status='confirmed';perf.status='crew_confirmed'
    return call
