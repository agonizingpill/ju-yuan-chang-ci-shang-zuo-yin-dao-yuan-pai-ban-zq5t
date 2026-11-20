from fastapi import APIRouter,Depends
from sqlalchemy import select
from .db import db_session
from .auth import current,writers
from .models import Performance
from .entry_models import EntryRecommendation
from .entry_schemas import SegmentInput,SegmentBatchInput,FinalizeInput,GenerateInput
from . import entry_service as entry
from .services import pack,get

router=APIRouter()

@router.get('/entry-segments')
def segments(performance_id:int,s=Depends(db_session),u=Depends(current)):
    perf=get(s,Performance,performance_id)
    return {'segments':entry.list_segments(s,performance_id),
            'reconcile':entry.reconcile_status(s,perf)}

@router.post('/entry-segments')
def add_segment(d:SegmentInput,s=Depends(db_session),u=Depends(writers)):
    x=entry.record_segment(s,d.model_dump(),u);s.commit();return x

@router.post('/entry-segments/batch')
def add_batch(d:SegmentBatchInput,s=Depends(db_session),u=Depends(writers)):
    x=entry.record_batch(s,d.model_dump(),u);s.commit();return x

@router.post('/entry-segments/finalize')
def finalize(d:FinalizeInput,s=Depends(db_session),u=Depends(writers)):
    x=entry.finalize(s,d.performance_id,u);s.commit();return x

@router.get('/entry-recommendations')
def recommendations(performance_id:int|None=None,production_id:int|None=None,
                    s=Depends(db_session),u=Depends(current)):
    q=select(EntryRecommendation).where(EntryRecommendation.is_active==True)
    if performance_id:q=q.where(EntryRecommendation.performance_id==performance_id)
    if production_id:q=q.where(EntryRecommendation.production_id==production_id)
    return [entry.recommendation_view(x) for x in s.scalars(q.order_by(EntryRecommendation.id))]

@router.post('/entry-recommendations/generate')
def generate(d:GenerateInput,s=Depends(db_session),u=Depends(writers)):
    rec=entry.generate(s,d.performance_id,u);s.commit();return entry.recommendation_view(rec)
