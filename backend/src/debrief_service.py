from datetime import datetime,timezone
from sqlalchemy import select
from fastapi import HTTPException
from .models import CrewCall
from .staff_models import CrewAssignment
from .debrief_models import ShowDebrief
from .staff_service import call_context,locked
from .services import pack,audit

def evidence(s,d):
    c=s.scalar(select(CrewCall).where(CrewCall.performance_id==d.performance_id))
    if not c:raise HTTPException(409,'请先完成本场点名确认与实名到岗')
    c,p,prod=call_context(s,c.id)
    if d.actual_attendance>prod.seats:raise HTTPException(409,'实际观众超过剧场座位容量')
    rows=s.scalars(select(CrewAssignment).where(CrewAssignment.crew_call_id==c.id).with_for_update()).all()
    checked=sum(x.checked_in for x in rows);need=c.ushers
    if checked<need:raise HTTPException(409,f'实名到岗不足：实到{checked}名，交接至少需{need}名')
    if p.forecast is None:raise HTTPException(409,'缺少原点名预测依据')
    variance=round(abs(d.actual_attendance-p.forecast)/max(1,p.forecast)*100,2)
    if (d.exit_minutes>15 or variance>30) and len(d.incident_note.strip())<8:raise HTTPException(409,'散场超过15分钟或上座偏差超过30%，须填写至少8字处置原因')
    from .zones_service import coverage
    coverage(s,p.id)
    return p.forecast,need,checked,variance

def save(s,d,u):
    forecast,need,checked,variance=evidence(s,d)
    if s.scalar(select(ShowDebrief.id).where(ShowDebrief.performance_id==d.performance_id)):raise HTTPException(409,'本场已有交接单，请修订原草稿')
    x=ShowDebrief(**d.model_dump(),forecast_snapshot=forecast,required_staff=need,checked_in_snapshot=checked,variance_pct=variance,state='draft');s.add(x);s.flush();audit(s,u,f'填写散场交接 场次#{d.performance_id}');return pack(x)

def revise(s,id,d,u):
    # Lock call before the debrief to preserve the assignment/checkin lock order.
    preview=s.get(ShowDebrief,id)
    if not preview:raise HTTPException(404,'交接单不存在')
    if d.performance_id!=preview.performance_id:raise HTTPException(409,'不能将交接单移到其他场次')
    forecast,need,checked,variance=evidence(s,d);x=locked(s,ShowDebrief,id)
    if x.state!='draft':raise HTTPException(409,'已归档交接不可改写')
    for k,v in d.model_dump().items():setattr(x,k,v)
    x.required_staff=need;x.checked_in_snapshot=checked;x.variance_pct=variance;audit(s,u,f'修订散场交接 #{id}');return pack(x)

def archive(s,id,u):
    from .frontdesk_schemas import DebriefInput
    preview=s.get(ShowDebrief,id)
    if not preview:raise HTTPException(404,'交接单不存在')
    call=s.scalar(select(CrewCall).where(CrewCall.performance_id==preview.performance_id))
    if not call:raise HTTPException(409,'原点名单缺失')
    call_context(s,call.id);x=locked(s,ShowDebrief,id)
    data=DebriefInput(**{k:getattr(x,k) for k in DebriefInput.model_fields})
    evidence(s,data)
    from .incidents_service import ensure_clear
    ensure_clear(s,x.performance_id)
    if x.state!='draft':raise HTTPException(409,'交接已经归档，不能重复签署')
    x.state='archived';x.archived_by=u.email;x.archived_at=datetime.now(timezone.utc).isoformat();audit(s,u,f'经理归档散场交接 #{id}');return pack(x)
