"""分段验票与进门高峰加岗建议。

口径：
- 开场前一小时按每 10 分钟切成 6 段，其余时段（更早到场与开场后迟到）合并为 1 段，共 7 段。
- 迟到的补录按“实际验票时刻”归段，记录补录时刻与补录人便于追溯。
- 各段人数之和必须与整场验票总数（Performance.arrivals）完全相符，才允许核齐（finalize）。
- 只有核齐版本才能作为样本；旧场次只有总数、没有分段的，不参与估算。
- 回测/估算只取目标场开演之前已经核齐的样本，之后补录或改数不影响当时的样本集合。
- 新建议整体算齐后原子换版（旧版失活、新版激活），任一步失败保留旧版。
"""
from datetime import datetime,timedelta,timezone
from math import ceil
from fastapi import HTTPException
from sqlalchemy import select
from .models import Production,Performance
from .entry_models import (
    EntrySegment,EntryRecommendation,
    PRE_SLOT_COUNT,SLOT_MINUTES,OTHER_SLOT_INDEX,SLOT_COUNT,utcnow,
)
from .services import get,pack,audit

MIN_SAMPLE_SHOWS=5
# 系统统一使用剧场本地时间（Asia/Shanghai）的 naive datetime，比较绝对时刻时按 +08:00 解释
LOCAL_TZ=timezone(timedelta(hours=8))

def curtain_dt(perf):
    return datetime.fromisoformat(perf.date.isoformat()+'T'+perf.curtain)

def slot_for_time(perf,observed_at):
    """按实际验票时刻归段。observed_at 为本地 naive datetime。"""
    observed_at=observed_at.replace(tzinfo=None)
    curtain=curtain_dt(perf)
    delta_min=(curtain-observed_at).total_seconds()/60
    # 开场前 60 分钟（含）到开场时刻之间：6 个 10 分钟段，段为左闭右开；
    # 距开场越近段号越大：[51,60)分钟 -> S0 ... [1,10)分钟 -> S5
    if 0 < delta_min <= PRE_SLOT_COUNT*SLOT_MINUTES:
        idx=(PRE_SLOT_COUNT-1)-int((delta_min-1)//SLOT_MINUTES)
        return min(PRE_SLOT_COUNT-1,max(0,idx))
    return OTHER_SLOT_INDEX

def slot_window(perf,slot_index):
    """返回该段的本地时间窗口（起,止）字符串，用于页面展示。"""
    curtain=curtain_dt(perf)
    if slot_index==OTHER_SLOT_INDEX:
        start=curtain-timedelta(minutes=PRE_SLOT_COUNT*SLOT_MINUTES)
        return f'{start:%H:%M} 以前 / 开场后迟到'
    end_offset=(PRE_SLOT_COUNT-slot_index)*SLOT_MINUTES
    start=curtain-timedelta(minutes=end_offset)
    end=curtain-timedelta(minutes=end_offset-SLOT_MINUTES)
    return f'{start:%H:%M}–{end:%H:%M}'

def segment_view(s,row,perf=None):
    perf=perf or get(s,Performance,row.performance_id)
    return pack(row)|{'window':slot_window(perf,row.slot_index)}

def list_segments(s,performance_id):
    perf=get(s,Performance,performance_id)
    # 已核齐则展示核齐版本，否则展示草稿
    finalized=s.scalar(select(EntrySegment.id).where(
        EntrySegment.performance_id==performance_id,EntrySegment.is_final==True))
    rows=s.scalars(select(EntrySegment).where(
        EntrySegment.performance_id==performance_id,
        EntrySegment.is_final==bool(finalized)).order_by(EntrySegment.slot_index)).all()
    return [segment_view(s,x,perf) for x in rows]

def _writable_performance(s,performance_id):
    perf=get(s,Performance,performance_id)
    prod=get(s,Production,perf.production_id)
    if perf.arrivals is None:
        raise HTTPException(409,'未来场次尚无整场验票总数，不能补录分段验票')
    if perf.status=='crew_confirmed' or s.scalar(select(Performance.id).where(
            Performance.production_id==prod.id,Performance.status=='crew_confirmed')):
        raise HTTPException(409,'该剧目已有确认点名，验票与分段证据已冻结')
    if s.scalar(select(EntrySegment.id).where(
            EntrySegment.performance_id==perf.id,EntrySegment.is_final==True)):
        raise HTTPException(409,'本场分段验票已核齐冻结；如需修订请先由经理核对流程后重新登记')
    return perf,prod

def _draft_rows(s,performance_id):
    return s.scalars(select(EntrySegment).where(
        EntrySegment.performance_id==performance_id,EntrySegment.is_final==False
    ).order_by(EntrySegment.slot_index)).all()

def record_segment(s,d,u):
    """补录一段验票；按实际验票时刻自动归段，同段重复补录覆盖该段草稿。"""
    perf,prod=_writable_performance(s,d['performance_id'])
    idx=slot_for_time(perf,d['observed_at'])
    if d['headcount']>prod.seats:
        raise HTTPException(409,'分段人数超过本场座位容量')
    row=s.scalar(select(EntrySegment).where(
        EntrySegment.performance_id==perf.id,EntrySegment.slot_index==idx,EntrySegment.is_final==False))
    now=utcnow().isoformat()
    if row:
        row.headcount=d['headcount'];row.observed_at=d['observed_at'].replace(tzinfo=None).isoformat()
        row.recorded_at=now;row.recorded_by=u.email
    else:
        row=EntrySegment(performance_id=perf.id,slot_index=idx,headcount=d['headcount'],
                         observed_at=d['observed_at'].replace(tzinfo=None).isoformat(),
                         recorded_at=now,recorded_by=u.email,is_final=False)
        s.add(row)
    s.flush();audit(s,u,f'补录分段验票 场次#{perf.id} 段{idx} {d["headcount"]}人')
    return segment_view(s,row,perf)

def record_batch(s,d,u):
    """一次性补录多段（直接指定段号），用于场务按段登记表。"""
    perf,prod=_writable_performance(s,d['performance_id'])
    items=d['segments']
    if items and sum(x['headcount'] for x in items)>prod.seats:
        raise HTTPException(409,'分段人数合计超过本场座位容量')
    seen=set()
    now=utcnow().isoformat()
    out=[]
    for item in items:
        if item['slot_index'] in seen:raise HTTPException(409,f"段 {item['slot_index']} 重复提交")
        seen.add(item['slot_index'])
        row=s.scalar(select(EntrySegment).where(
            EntrySegment.performance_id==perf.id,EntrySegment.slot_index==item['slot_index'],EntrySegment.is_final==False))
        if row:
            row.headcount=item['headcount'];row.observed_at=d['observed_at'].replace(tzinfo=None).isoformat()
            row.recorded_at=now;row.recorded_by=u.email
        else:
            row=EntrySegment(performance_id=perf.id,slot_index=item['slot_index'],headcount=item['headcount'],
                             observed_at=d['observed_at'].replace(tzinfo=None).isoformat(),
                             recorded_at=now,recorded_by=u.email,is_final=False)
            s.add(row)
        s.flush();out.append(row)
    audit(s,u,f'批量补录分段验票 场次#{perf.id} {len(seen)}段')
    return [segment_view(s,x,perf) for x in sorted(out,key=lambda x:x.slot_index)]

def reconcile_status(s,perf):
    finalized=s.scalar(select(EntrySegment).where(
        EntrySegment.performance_id==perf.id,EntrySegment.is_final==True))
    if finalized:
        rows=s.scalars(select(EntrySegment).where(
            EntrySegment.performance_id==perf.id,EntrySegment.is_final==True)).all()
        total=sum(x.headcount for x in rows)
        return {'segment_total':total,'arrivals':perf.arrivals,'is_final':True,
                'matches':total==perf.arrivals,
                'missing_slots':[i for i in range(SLOT_COUNT) if not any(x.slot_index==i for x in rows)]}
    rows=_draft_rows(s,perf.id)
    total=sum(x.headcount for x in rows)
    return {'segment_total':total,'arrivals':perf.arrivals,'is_final':False,
            'matches':bool(rows) and total==perf.arrivals,
            'missing_slots':[i for i in range(SLOT_COUNT) if not any(x.slot_index==i for x in rows)]}

def finalize(s,performance_id,u):
    """核齐：分段合计必须与整场验票完全相符。核齐后分段冻结，成为可引用样本。"""
    perf,_=_writable_performance(s,performance_id)
    rows=_draft_rows(s,perf.id)
    if not rows:raise HTTPException(409,'尚无分段验票记录，不能核齐')
    total=sum(x.headcount for x in rows)
    if total!=perf.arrivals:
        raise HTTPException(409,f'分段合计 {total} 人与整场验票 {perf.arrivals} 人不符，请先校正再核齐')
    now=utcnow().astimezone(timezone.utc).replace(tzinfo=None)
    for row in rows:
        row.is_final=True;row.finalized_at=now
    s.flush();audit(s,u,f'核齐分段验票 场次#{perf.id} 共{total}人')
    return list_segments(s,perf.id)

def eligible_sample_segments(s,prod,target_perf):
    """只取目标场开演前已核齐的同剧目分段样本。

    目标场开演之后才核齐（或之后补录/改数再核齐）的历史场一律排除，
    保证当时回测所见样本不被后来的补录改写。
    """
    # 目标场开演的绝对时刻（本地 naive → +08:00 → naive UTC），
    # 与 finalized_at 的 naive UTC 存储口径一致，只保留开演前已核齐的样本
    target_curtain_utc=curtain_dt(target_perf).replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc).replace(tzinfo=None)
    rows=s.scalars(select(EntrySegment).join(
        Performance,Performance.id==EntrySegment.performance_id
    ).where(
        Performance.production_id==prod.id,
        EntrySegment.is_final==True,
        EntrySegment.performance_id!=target_perf.id,
        EntrySegment.finalized_at.is_not(None),
        EntrySegment.finalized_at < target_curtain_utc,
    ).order_by(EntrySegment.performance_id,EntrySegment.slot_index)).all()
    by_perf={}
    for row in rows:by_perf.setdefault(row.performance_id,[]).append(row)
    # 核齐时已保证分段合计等于整场验票；这里再防御性过滤掉不完整的 7 段记录
    return {pid:items for pid,items in by_perf.items() if len(items)==SLOT_COUNT}

def build_recommendation(s,target_perf):
    """基于核齐样本估算进门高峰与加岗时段。返回 (status, detail, reason)。"""
    prod=get(s,Production,target_perf.production_id)
    samples=eligible_sample_segments(s,prod,target_perf)
    sample_size=len(samples)
    base={
        'production_id':prod.id,'performance_id':target_perf.id,
        'curtain':target_perf.curtain,
        'sample_size':sample_size,'min_sample_size':MIN_SAMPLE_SHOWS,
        'slots':[{'slot_index':i,'window':slot_window(target_perf,i)} for i in range(SLOT_COUNT)],
        'generated_at':utcnow().isoformat(),
    }
    if target_perf.forecast is None:
        return 'insufficient',base|{'sample_shows':[]},'本场尚未完成上座预测，无法把进门节奏换算为分段人数，请先预测上座'
    if sample_size==0:
        return 'insufficient',base|{'sample_shows':[]},'还没有核齐的分段验票样本；旧场次只有总人数，不参与进门高峰估算'
    # 每场各段占比（按该场分段合计归一），再对样本求平均，得到进场节奏曲线
    sample_shows=[]
    share_sums=[0.0]*SLOT_COUNT
    forecast_total=target_perf.forecast
    for pid,items in sorted(samples.items()):
        perf=get(s,Performance,pid)
        seg_total=sum(x.headcount for x in items)
        shares=[(next(x.headcount for x in items if x.slot_index==i)/seg_total) if seg_total else 0.0
                for i in range(SLOT_COUNT)]
        for i,val in enumerate(shares):share_sums[i]+=val
        sample_shows.append({'performance_id':pid,'date':perf.date.isoformat(),
                             'arrivals':perf.arrivals,'segment_total':seg_total,
                             'finalized_at':next(x.finalized_at for x in items).isoformat(),
                             'shares':[round(v,4) for v in shares]})
    avg_shares=[v/sample_size for v in share_sums]
    scale=1.0
    if forecast_total:
        hist_avg=sum(get(s,Performance,pid).arrivals for pid in samples)/sample_size
        if hist_avg>0:scale=forecast_total/hist_avg
    # 各段平均每分钟进场人数（历史人头均值 × 规模系数），用于衡量门口压力
    per_minute=[]
    for i in range(SLOT_COUNT):
        hist_avg_heads=sum(next(x.headcount for x in samples[pid] if x.slot_index==i)
                           for pid in samples)/sample_size
        window_min=SLOT_MINUTES if i<OTHER_SLOT_INDEX else 60  # “其余”段跨度大，按 60 分钟折算
        per_minute.append(hist_avg_heads*scale/window_min)
    peak_idx=max(range(SLOT_COUNT),key=lambda i:per_minute[i])
    expected_seg=[round(forecast_total*avg_shares[i]) if forecast_total else None for i in range(SLOT_COUNT)]
    # 加岗：高峰段及与其相邻的开场前 10 分钟段（压力连续）；其余段不加岗
    surge_slots=sorted({i for i in (peak_idx-1,peak_idx,peak_idx+1) if 0<=i<PRE_SLOT_COUNT})
    base_ushers=max(1,ceil((forecast_total or 0)/40))
    # 高峰段预计进场人数按每 40 人 1 名引导员折算，相对基础班底追加人手（至少加 1 名）
    peak_segment_need=max(1,ceil((expected_seg[peak_idx] or 0)/40))
    peak_ushers=base_ushers+peak_segment_need
    detail=base|{
        'sample_shows':sample_shows,
        'avg_shares':[round(v,4) for v in avg_shares],
        'expected_per_slot':expected_seg,
        'per_minute_pressure':[round(v,2) for v in per_minute],
        'peak_slot_index':peak_idx,
        'peak_window':slot_window(target_perf,peak_idx),
        'surge_slots':[{'slot_index':i,'window':slot_window(target_perf,i)} for i in surge_slots],
        'base_ushers':base_ushers,'peak_ushers':peak_ushers,
        'extra_ushers':peak_segment_need,
        'forecast_total':forecast_total,
    }
    if sample_size<MIN_SAMPLE_SHOWS:
        return 'insufficient',detail,f'核齐分段样本仅 {sample_size} 场，少于最低 {MIN_SAMPLE_SHOWS} 场，暂不出具加岗建议'
    return 'ready',detail,None

def generate(s,performance_id,u):
    """算齐后原子换版：新版本整体写入成功才停用旧版；失败保留旧版。"""
    perf=get(s,Performance,performance_id)
    prod=get(s,Production,perf.production_id)
    if perf.arrivals is not None:
        raise HTTPException(409,'进门高峰建议只针对未开演的未来场次')
    active=s.scalar(select(EntryRecommendation).where(
        EntryRecommendation.performance_id==perf.id,EntryRecommendation.is_active==True))
    status,detail,reason=build_recommendation(s,perf)
    next_version=(active.version+1) if active else 1
    new_rec=EntryRecommendation(performance_id=perf.id,production_id=prod.id,
                                version=next_version,is_active=True,status=status,
                                sample_size=detail['sample_size'],detail=detail,reason=reason)
    s.add(new_rec);s.flush()  # 先写入新版，确认无异常
    if active:active.is_active=False
    audit(s,u,f'换版进门高峰建议 场次#{perf.id} v{next_version} {status}')
    return new_rec

def recommendation_view(rec):
    if rec is None:return None
    return pack(rec)|{'detail':rec.detail}

def active_for_performances(s,performance_ids):
    if not performance_ids:return {}
    rows=s.scalars(select(EntryRecommendation).where(
        EntryRecommendation.performance_id.in_(performance_ids),
        EntryRecommendation.is_active==True)).all()
    return {r.performance_id:recommendation_view(r) for r in rows}
