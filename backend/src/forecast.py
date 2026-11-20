from datetime import timedelta
from math import ceil
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sqlalchemy import select
from .services import history,validate_history
from .models import Performance

def fit(values):return ExponentialSmoothing(np.array(values,dtype=float),trend='add',seasonal='add',seasonal_periods=7,initialization_method='estimated').fit(optimized=True)
def forecast_week(s,production):
    rows=history(s,production.id);validate_history(rows)
    y=[r.arrivals for r in rows];train=y[:-7];test=y[-7:]
    back=fit(train).forecast(7);mae=float(np.mean(np.abs(np.array(test)-back)))
    pred=fit(y).forecast(7)
    output=[]
    for i,value in enumerate(pred):
        day=rows[-1].date+timedelta(days=i+1)
        perf=s.scalar(select(Performance).where(Performance.production_id==production.id,Performance.date==day))
        if not perf:perf=Performance(production_id=production.id,date=day,curtain='19:30',status='scheduled');s.add(perf)
        if perf.arrivals is not None or perf.status=='crew_confirmed':raise ValueError('未来场次已有验票或确认点名，不得覆盖')
        raw=max(0,float(value));perf.raw_forecast=round(raw,2);perf.forecast=min(production.seats,ceil(raw));perf.status='forecasted'
        output.append({'date':day.isoformat(),'raw':round(raw,2),'capped':perf.forecast,'required_ushers':max(1,ceil(perf.forecast/40))})
    return {'backtest_mae':round(mae,3),'train_days':len(train),'holdout_days':7,'history_days':len(y),'holdout_start':rows[-7].date.isoformat(),'history_end':rows[-1].date.isoformat(),'backtest':[{'date':r.date.isoformat(),'actual':r.arrivals,'predicted':round(float(v),2)} for r,v in zip(rows[-7:],back)],'future':output,'method':'Holt-Winters additive trend + additive weekly seasonality (7)','seat_capacity':production.seats}
