from datetime import date,timedelta,datetime,timezone
import random
from sqlalchemy import select,func
from src.db import Base,engine,Session
from src.models import User,Production,Performance,CrewCall
from src.staff_models import StaffMember,CrewAssignment
from src.debrief_models import ShowDebrief
from src.zone_models import EntranceZone,ZonePost
from src.incident_models import HouseIncident
from src.lost_models import LostItem,ItemClaim
from src.entry_models import EntrySegment,EntryRecommendation,SLOT_COUNT,PRE_SLOT_COUNT,SLOT_MINUTES,OTHER_SLOT_INDEX
from src.auth import hash_password

def seed_entry_segments(s,perf,curtain_dt,rng,finalized_at):
    """按“早到少、临门高峰、迟到兜底”的节奏把整场人数拆成 7 段并核齐。"""
    if s.scalar(select(EntrySegment.id).where(EntrySegment.performance_id==perf.id)):return
    total=perf.arrivals
    weights=[0.04,0.07,0.12,0.18,0.27,0.24,0.08]  # 60+..10 分钟六段 + 其余
    counts=[round(total*w) for w in weights]
    counts[max(range(PRE_SLOT_COUNT),key=lambda i:counts[i])] += total-sum(counts)
    now_iso=finalized_at  # 已转为 naive UTC
    for idx,head in enumerate(counts):
        if idx==OTHER_SLOT_INDEX:
            observed=(curtain_dt+timedelta(minutes=8)).isoformat()
        else:
            end_offset=(PRE_SLOT_COUNT-idx)*SLOT_MINUTES
            observed=(curtain_dt-timedelta(minutes=end_offset-3)).isoformat()
        s.add(EntrySegment(performance_id=perf.id,slot_index=idx,headcount=head,
                           observed_at=observed,recorded_at=now_iso.isoformat(),
                           recorded_by='steward@nanan.demo',is_final=True,
                           finalized_at=now_iso))

def seed():
    Base.metadata.create_all(engine)
    with Session() as s:
        for role in ('admin','steward','viewer'):
            email=role+'@nanan.demo'
            if not s.scalar(select(User).where(User.email==email)):s.add(User(email=email,role=role,password_hash=hash_password('Curtain2026!')))
        for code,title in [('NA-TIDE','潮汐独白'),('NA-GAP','排练厅缺口示例')]:
            if not s.scalar(select(Production).where(Production.code==code)):s.add(Production(code=code,title=title,seats=160,duration_minutes=95))
        s.flush();p=s.scalar(select(Production).where(Production.code=='NA-TIDE'));gap=s.scalar(select(Production).where(Production.code=='NA-GAP'))
        rng=random.Random(42);start=date(2026,9,22)
        for i in range(63):
            d=start+timedelta(days=i)
            if s.scalar(select(Performance).where(Performance.production_id==p.id,Performance.date==d)):continue
            n=round(75+i*.38+[0,-5,0,5,20,52,40][d.weekday()]+rng.uniform(-4,4)) if i<56 else None
            s.add(Performance(production_id=p.id,date=d,curtain='19:30',arrivals=n,status='observed' if n is not None else 'scheduled'))
        for i in range(29):
            if i==10:continue
            d=date(2026,10,19)+timedelta(days=i)
            if not s.scalar(select(Performance).where(Performance.production_id==gap.id,Performance.date==d)):s.add(Performance(production_id=gap.id,date=d,curtain='19:30',arrivals=80+i%7,status='observed'))
        # 分段验票：仅最近 10 场有 7 段核齐版本，更早历史场只有总数（不参与高峰估算）。
        observed_perfs=s.scalars(select(Performance).where(
            Performance.production_id==p.id,Performance.arrivals.is_not(None)
        ).order_by(Performance.date.desc()).limit(10)).all()
        for k,perf in enumerate(sorted(observed_perfs,key=lambda x:x.date)):
            curtain=datetime.fromisoformat(perf.date.isoformat()+'T'+perf.curtain)
            # 最近一场（k=9）刻意在 11-17 场开演后才核齐：回测 11-17 时它必须被排除
            if k==9:
                finalized=datetime(2026,11,17,20,0,tzinfo=timezone(timedelta(hours=8)))
            else:
                finalized=(curtain+timedelta(hours=2)).replace(tzinfo=timezone(timedelta(hours=8)))
            seed_entry_segments(s,perf,curtain,rng,finalized.astimezone(timezone.utc).replace(tzinfo=None))
        for i,name in enumerate(['林澈','周芮','许舟','陈言','方亭','江沅','沈青','唐禾','魏宁','宋乔','陆遥','朱青','李荷','钱霖','赵岳','顾川'],1):
            code=f'ST-{i:02d}'
            if not s.scalar(select(StaffMember).where(StaffMember.code==code)):s.add(StaffMember(code=code,name=name,active=True,max_daily_calls=1 if i==3 else 3))
        if not s.scalar(select(StaffMember).where(StaffMember.code=='ST-OFF')):s.add(StaffMember(code='ST-OFF',name='暂停排班示例',active=False,max_daily_calls=2))
        for code,title,dates,curtain in [('NA-FLOOR','交接演练 · 夜场',[date(2026,11,17),date(2026,11,18)],'19:30'),('NA-MATINEE','交接演练 · 午场',[date(2026,11,17)],'14:00')]:
            prod=s.scalar(select(Production).where(Production.code==code))
            if not prod:prod=Production(code=code,title=title,seats=160,duration_minutes=95,forecast_state='ready');s.add(prod);s.flush()
            for d in dates:
                perf=s.scalar(select(Performance).where(Performance.production_id==prod.id,Performance.date==d))
                if not perf:perf=Performance(production_id=prod.id,date=d,curtain=curtain,arrivals=None,forecast=80,raw_forecast=80,status='crew_confirmed');s.add(perf);s.flush()
                if not s.scalar(select(CrewCall).where(CrewCall.performance_id==perf.id)):
                    call=(datetime.fromisoformat(d.isoformat()+'T'+curtain)-timedelta(minutes=45)).isoformat()
                    s.add(CrewCall(performance_id=perf.id,ushers=2,call_time=call,leader='演练领班',status='confirmed'))
        s.flush()
        for prod in s.scalars(select(Production).where(Production.code.in_(['NA-FLOOR','NA-MATINEE']))):
            for code in ['EAST','WEST']:
                if not s.scalar(select(EntranceZone).where(EntranceZone.production_id==prod.id,EntranceZone.code==code)):s.add(EntranceZone(production_id=prod.id,code=code,capacity=80,required_staff=1,active=True))
        s.commit();print({t.__tablename__:s.scalar(select(func.count()).select_from(t)) for t in (User,Production,Performance,CrewCall,StaffMember,CrewAssignment,ShowDebrief,EntranceZone,ZonePost,HouseIncident,LostItem,ItemClaim,EntrySegment,EntryRecommendation)})
if __name__=='__main__':seed()
