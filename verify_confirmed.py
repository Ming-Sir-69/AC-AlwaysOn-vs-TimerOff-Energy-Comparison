"""West-facing checks and timer scan, separate from original saved outputs."""
from dataclasses import replace
from pathlib import Path
import argparse,json,sys
import pandas as pd
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'))
from acstudy.model import room_parameters,simulate,POLICIES
from acstudy.weather import load_epw,forcing_for_parameters
from acstudy.analysis import metrics,recovery_times,window_records,ROOM_AREAS
from acstudy.audit import reconstruct_budgets,electric_reconstruction
from cycle_analysis import scan

def daily_details():
 rows=[];windows=[]
 frame,meta=load_epw(ROOT/'data','shenzhen');season=frame[frame.month.between(5,10)]
 extended=frame.loc[season.index[0]:season.index[-1]+6]
 for room,area in ROOM_AREAS.items():
  p=room_parameters(area,azimuth=270.);w=forcing_for_parameters(extended,meta,p)
  for kind in ['fixed','inverter']:
   for policy in POLICIES:
    full=simulate(w,p,kind,policy)
    a=full[:len(season)*60]
    wins=window_records(a);wins['room']=room;wins['kind']=kind;wins['policy']=policy;windows.append(wins)
    rec,event=recovery_times(full,p);temp,te=recovery_times(full,p,humidity=False)
    for day,(r,e) in enumerate(zip(rec,event)):
     rows.append(dict(room=room,kind=kind,policy=policy,workday_index=day,
      temperature_minutes=temp[day],temperature_recovered=bool(te[day]),joint_minutes=r,joint_recovered=bool(e),minutes=r,recovered=bool(e)))
 pd.concat(windows,ignore_index=True).to_csv(ROOT/'results/west_window_daily.csv.gz',index=False,compression={'method':'gzip','mtime':0})
 pd.DataFrame(rows).to_csv(ROOT/'results/west_recovery_daily.csv.gz',index=False,compression={'method':'gzip','mtime':0})
 print('West fixed-geometry window and recovery events complete',flush=True)


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--details-only',action='store_true');args=parser.parse_args()
 daily_details()
 if args.details_only:return
 f,meta=load_epw(ROOT/'data','shenzhen');cfg=json.loads((ROOT/'results/config.json').read_text())
 week=f[f.doy.between(cfg['hot_week_doy_start'],cfg['hot_week_doy_end'])]
 p=room_parameters(azimuth=270.);w=forcing_for_parameters(week,meta,p)
 checks=[];budgets=[]
 for kind in ['fixed','inverter']:
  reference=None
  for dt in [60.,120.,300.]:
   try:a=simulate(w,p,kind,'cut_all',dt=dt)
   except ValueError as error:
    checks.append(dict(kind=kind,dt_s=dt,status='rejected_unstable',reason=str(error)));continue
   m=metrics(a,p,dt)
   if reference is None:reference=m
   checks.append(dict(kind=kind,dt_s=dt,status='valid',energy_kWh=m['energy_kWh'],energy_difference_vs_60_pct=100*(m['energy_kWh']/reference['energy_kWh']-1)))
  for policy in POLICIES:
   a=simulate(w,p,kind,policy,warmup_hours=0)
   budgets.append(dict(kind=kind,policy=policy,azimuth=270.,**reconstruct_budgets(w,p,a,[26,26,26,.012]),**electric_reconstruction(w,p,a,kind)))
 pd.DataFrame(checks).to_csv(ROOT/'results/west_timestep_check.csv',index=False)
 pd.DataFrame(budgets).to_csv(ROOT/'results/west_independent_budgets.csv',index=False)
 print('West timestep and output-budget checks complete',flush=True)
 scan(azimuth=270.,prefix='west_')

if __name__=='__main__':main()
