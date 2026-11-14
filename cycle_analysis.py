"""Seasonal minimum-cycle timer analysis."""
from pathlib import Path
from dataclasses import replace
import json,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from acstudy.model import Parameters,simulate
from acstudy.weather import load_epw,forcing_for_parameters
from acstudy.analysis import metrics

def scan(azimuth=180.,prefix=""):
 assert prefix in ["","west_"]
 rows=[]
 for station in ['shenzhen','guangzhou']:
  frame,meta=load_epw(ROOT/'data',station);season=frame[frame.month.between(5,10)]
  for on in [180.,300.,600.]:
   for off in [120.,180.,300.]:
    p=replace(Parameters(),azimuth=azimuth,min_on_seconds=on,min_off_seconds=off)
    w=forcing_for_parameters(season,meta,p);energies={}
    for policy in ['always','cut_all','manual']:
     a=simulate(w,p,'fixed',policy)
     m=metrics(a,p);energies[policy]=m['energy_kWh']
     running=a[:,24]>.5
     changes=np.diff(np.r_[False,running,False].astype(int));beg=np.flatnonzero(changes==1);end=np.flatnonzero(changes==-1)
     durations=(end-beg).astype(float) # one row per minute
     # Drop partial first/last runs; forced interruptions are retained and documented.
     durations=durations[(beg>0)&(end<len(a))]
     rows.append(dict(station=station,min_on_seconds=on,min_off_seconds=off,kind='fixed',policy=policy,
       **{k:m[k] for k in ['energy_kWh','workday_kWh','restday_kWh','cycles_per_day','delivered_cop','rest_peak_C']},
       run_minutes_p10=float(np.quantile(durations,.1)),run_minutes_p50=float(np.median(durations)),run_minutes_p90=float(np.quantile(durations,.9))))
    for row in rows[-3:]:
     row['saving_pct']=100*(1-row['energy_kWh']/energies['always'])
     row['manual_extra_kWh']=energies['manual']-energies['cut_all']
    print(f'Timer scan: {station}, on {on:.0f}s, off {off:.0f}s',flush=True)
 pd.DataFrame(rows).to_csv(ROOT/f'results/{prefix}cycle_timer_scan.csv',index=False)
 (ROOT/f'results/{prefix}cycle_timer_scan_config.json').write_text(json.dumps({'stations':['shenzhen','guangzhou'],'season_days':184,'dt_seconds':60,'min_on_seconds':[180,300,600],'min_off_seconds':[120,180,300],'building':'non-topfloor, one exterior wall','azimuth':azimuth,'parameters':'Parameters defaults except timer values','kind':'fixed','policies':['always','cut_all','manual'],'warmup_hours':168,'run_duration':'consecutive fan-running output at one-minute resolution; incomplete boundary runs omitted; forced power cuts retained','limitation':'deterministic parameter scan, not propagated MC uncertainty; performance curves remain assumptions'},indent=2))

if __name__=='__main__':scan()
