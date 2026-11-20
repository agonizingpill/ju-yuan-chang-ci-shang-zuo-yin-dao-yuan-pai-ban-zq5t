from fastapi import APIRouter,Depends
from sqlalchemy import select
from .db import db_session
from .auth import current,writers,admin
from .zone_models import EntranceZone,ZonePost
from .incident_models import HouseIncident
from .lost_models import LostItem,ItemClaim
from .house_schemas import ZoneInput,PostInput,IncidentInput,DispatchInput,ResolutionInput,LostInput,ClaimInput
from .services import pack
from . import zones_service as zones,incidents_service as incidents,lost_service as lost
router=APIRouter()
@router.get('/entrance-zones')
def list_zones(s=Depends(db_session),u=Depends(current)):return [pack(x) for x in s.scalars(select(EntranceZone).order_by(EntranceZone.id))]
@router.post('/entrance-zones')
def create_zone(d:ZoneInput,s=Depends(db_session),u=Depends(admin)):
    x=zones.create(s,d,u);s.commit();return x
@router.get('/zone-posts')
def list_posts(s=Depends(db_session),u=Depends(current)):return [zones.post_view(s,x) for x in s.scalars(select(ZonePost).order_by(ZonePost.id))]
@router.post('/zone-posts')
def post(d:PostInput,s=Depends(db_session),u=Depends(writers)):
    x=zones.post(s,d,u);s.commit();return x
@router.get('/house-incidents')
def list_incidents(s=Depends(db_session),u=Depends(current)):return [incidents.view(s,x) for x in s.scalars(select(HouseIncident).order_by(HouseIncident.id.desc()))]
@router.post('/house-incidents')
def add_incident(d:IncidentInput,s=Depends(db_session),u=Depends(writers)):
    x=incidents.create(s,d,u);s.commit();return x
@router.post('/house-incidents/{id}/dispatch')
def dispatch(id:int,d:DispatchInput,s=Depends(db_session),u=Depends(admin)):
    x=incidents.dispatch(s,id,d,u);s.commit();return x
@router.post('/house-incidents/{id}/resolve')
def resolve(id:int,d:ResolutionInput,s=Depends(db_session),u=Depends(writers)):
    x=incidents.resolve(s,id,d,u);s.commit();return x
@router.post('/house-incidents/{id}/close')
def close(id:int,s=Depends(db_session),u=Depends(admin)):
    x=incidents.close(s,id,u);s.commit();return x
@router.get('/lost-items')
def items(s=Depends(db_session),u=Depends(current)):return [lost.view(x,u) for x in s.scalars(select(LostItem).order_by(LostItem.id.desc()))]
@router.post('/lost-items')
def add_item(d:LostInput,s=Depends(db_session),u=Depends(writers)):
    x=lost.create(s,d,u);s.commit();return x
@router.get('/item-claims')
def claims(s=Depends(db_session),u=Depends(current)):return [pack(x) for x in s.scalars(select(ItemClaim).order_by(ItemClaim.id.desc()))]
@router.post('/item-claims')
def claim(d:ClaimInput,s=Depends(db_session),u=Depends(writers)):
    x=lost.claim(s,d,u);s.commit();return x
@router.put('/item-claims/{id}')
def revise(id:int,d:ClaimInput,s=Depends(db_session),u=Depends(writers)):
    x=lost.revise(s,id,d,u);s.commit();return x
@router.post('/item-claims/{id}/handover')
def handover(id:int,s=Depends(db_session),u=Depends(admin)):
    x=lost.handover(s,id,u);s.commit();return x
