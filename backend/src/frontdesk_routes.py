from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from .db import db_session
from .auth import current,writers,admin
from .staff_models import StaffMember,CrewAssignment
from .debrief_models import ShowDebrief
from .frontdesk_schemas import StaffInput,AssignmentInput,CheckinInput,DebriefInput
from .services import pack,audit
from . import staff_service as staff,debrief_service as debrief
router=APIRouter()
@router.get('/staff')
def members(s=Depends(db_session),u=Depends(current)):return [pack(x) for x in s.scalars(select(StaffMember).order_by(StaffMember.id))]
@router.post('/staff')
def add(d:StaffInput,s=Depends(db_session),u=Depends(admin)):
    x=StaffMember(**d.model_dump());s.add(x);audit(s,u,'登记实名人员 '+d.code);s.commit();return pack(x)
@router.put('/staff/{id}')
def edit(id:int,d:StaffInput,s=Depends(db_session),u=Depends(admin)):
    x=staff.locked(s,StaffMember,id)
    if d.code!=x.code:raise HTTPException(409,'人员编号不可变更，保留排班身份')
    for k,v in d.model_dump().items():setattr(x,k,v)
    audit(s,u,'修订人员可用性 '+d.code);s.commit();return pack(x)
@router.get('/crew-assignments')
def assignments(s=Depends(db_session),u=Depends(current)):return [staff.assignment_view(s,x) for x in s.scalars(select(CrewAssignment).order_by(CrewAssignment.id))]
@router.post('/crew-assignments')
def assign(d:AssignmentInput,s=Depends(db_session),u=Depends(writers)):
    x=staff.assign(s,d,u);s.commit();return x
@router.post('/crew-assignments/{id}/check-in')
def checkin(id:int,d:CheckinInput,s=Depends(db_session),u=Depends(writers)):
    x=staff.checkin(s,id,d,u);s.commit();return x
@router.get('/show-debriefs')
def debriefs(s=Depends(db_session),u=Depends(current)):return [pack(x) for x in s.scalars(select(ShowDebrief).order_by(ShowDebrief.id.desc()))]
@router.post('/show-debriefs')
def create(d:DebriefInput,s=Depends(db_session),u=Depends(writers)):
    x=debrief.save(s,d,u);s.commit();return x
@router.put('/show-debriefs/{id}')
def revise(id:int,d:DebriefInput,s=Depends(db_session),u=Depends(writers)):
    x=debrief.revise(s,id,d,u);s.commit();return x
@router.post('/show-debriefs/{id}/archive')
def archive(id:int,s=Depends(db_session),u=Depends(admin)):
    x=debrief.archive(s,id,u);s.commit();return x
