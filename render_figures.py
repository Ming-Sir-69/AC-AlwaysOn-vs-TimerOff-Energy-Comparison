"""Render the saved results without running or modifying the numerical study."""
from pathlib import Path
import argparse,hashlib,json,sys
import pandas as pd
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from acstudy.plots import make_plots,TYPES
from acstudy.model import POLICIES
from acstudy.analysis import ROOM_AREAS

def main():
    p=argparse.ArgumentParser();p.add_argument('--only',nargs='+');p.add_argument('--report',action='store_true');args=p.parse_args()
    protected=list((ROOT/'results').glob('*.csv'))+list((ROOT/'results').glob('*.csv.gz'))+list((ROOT/'results').glob('*.npz'))+[ROOT/'results/confirmed_config.json']+list((ROOT/'data').glob('*.epw'))
    fingerprints={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in protected}
    mc=pd.read_csv(ROOT/'results/building_confirmed.csv.gz');sobol=pd.read_csv(ROOT/'results/west_sobol.csv');phase=pd.read_csv(ROOT/'results/west_phase.csv')
    traces={(room,kind,policy):pd.read_csv(ROOT/f'results/west_trace_{room}_{kind}_{policy}.csv.gz').to_numpy() for room in ROOM_AREAS for kind in TYPES for policy in POLICIES}
    manifest=make_plots(mc,sobol,phase,traces,ROOT/'figures',only=args.only)
    for path,digest in fingerprints.items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,'Calculation file changed: '+path
    if args.report:
        from acstudy.report import write_report
        write_report(ROOT,mc,sobol,json.loads((ROOT/'results/confirmed_config.json').read_text()))
    print('Calculation files unchanged:',len(fingerprints),flush=True)

if __name__=='__main__':main()
