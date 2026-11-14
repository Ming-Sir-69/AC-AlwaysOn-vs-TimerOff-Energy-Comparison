"""Generate the optional broad-orientation example trajectories."""
from pathlib import Path
import json,sys
import pandas as pd
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from acstudy.model import room_parameters,simulate,COLUMNS,POLICIES
from acstudy.analysis import ROOM_AREAS
from acstudy.weather import load_epw,forcing_for_parameters

def generate():
    frame,meta=load_epw(ROOT/'data','shenzhen')
    cfg=json.loads((ROOT/'results/confirmed_config.json').read_text())
    week=frame[frame.doy.between(cfg['hot_week_doy_start'],cfg['hot_week_doy_end'])]
    for room,area in ROOM_AREAS.items():
        p=room_parameters(area)
        w=forcing_for_parameters(week,meta,p)
        for kind in ['fixed','inverter']:
            for policy in POLICIES:
                a=simulate(w,p,kind,policy)
                table=pd.DataFrame(a,columns=COLUMNS)
                table.to_csv(ROOT/f'results/trace_{room}_{kind}_{policy}.csv.gz',index=False,float_format='%.8g',compression={'method':'gzip','mtime':0})
                if room=='base':table.to_csv(ROOT/f'results/trace_{kind}_{policy}.csv.gz',index=False,float_format='%.8g',compression={'method':'gzip','mtime':0})
    print('Optional broad-orientation trajectories generated as CSV gzip files.')
if __name__=='__main__':generate()
