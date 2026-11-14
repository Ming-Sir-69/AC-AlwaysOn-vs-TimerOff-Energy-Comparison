"""Recalculate west-facing baseline; preserve all earlier scientific outputs."""
from pathlib import Path
from dataclasses import asdict
import argparse,hashlib,json,sys,time
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from acstudy.model import Parameters,room_parameters,simulate,POLICIES,COLUMNS
from acstudy.analysis import BOUNDS,SEED,ROOM_AREAS,metrics,summarize_windows,sobol_analysis,scenario_units
from acstudy.weather import load_epw,forcing_for_parameters
from acstudy.confirmed import CASES,case_parameters,WEST_BOUNDS,WEST_LABELS,west_parameters


def input_signature(n,sobol_n):
    files=[ROOT/'src/acstudy'/n for n in ['model.py','weather.py','analysis.py','confirmed.py']]+list((ROOT/'data').glob('*.epw'))
    return dict(mc_n=n,sobol_n=sobol_n,seed=SEED,
        fingerprints={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})


def seasons(frames,metas,n,signature):
    checkpoint=ROOT/'.cache/west_checkpoint.csv';stamp=ROOT/'.cache/west_checkpoint_config.json'
    rows=[];done=0
    if checkpoint.exists() and stamp.exists() and json.loads(stamp.read_text())==signature:
        old=pd.read_csv(checkpoint)
        counts=old.groupby('sample').size()
        assert counts.eq(60).all()
        done=len(counts);assert set(counts.index)==set(range(done))
        rows=old.to_dict('records');print(f'Resume same-input completed samples: {done}/{n}',flush=True)
    else:stamp.write_text(json.dumps(signature,indent=2))
    unit=scenario_units(n)
    for k,u in enumerate(unit):
        if k<done:continue
        station='shenzhen' if k%2==0 else 'guangzhou'
        frame=frames[station];season=frame[frame.month.between(5,10)]
        extended=frame.loc[season.index[0]:season.index[-1]+6];steps=len(season)*60
        for case,label in CASES:
            for room in (ROOM_AREAS if case=='west' else ['base']):
                p=case_parameters(u,case,room);w=forcing_for_parameters(extended,metas[station],p)
                for kind in ['fixed','inverter']:
                    reference=None
                    for policy in (POLICIES if case=='west' else ['always','cut_all','manual']):
                        full=simulate(w,p,kind,policy);a=full[:steps]
                        m=metrics(a,p,recovery_data=full)
                        m.update(summarize_windows(a))
                        if policy=='always':reference=m.copy()
                        m.update(sample=k,station=station,building_case=case,case_label=label,room=room,kind=kind,policy=policy)
                        m.update({'p_'+key:getattr(p,key) for key in BOUNDS})
                        m.update(saving_kWh=reference['energy_kWh']-m['energy_kWh'],
                            saving_pct=100*(1-m['energy_kWh']/reference['energy_kWh']),
                            terminal_extra_sensible_kWh=m['terminal_sensible_kWh']-reference['terminal_sensible_kWh'],
                            terminal_extra_latent_kWh=m['terminal_latent_kWh']-reference['terminal_latent_kWh'])
                        rows.append(m)
        if (k+1)%4==0 or k+1==n:
            pd.DataFrame(rows).to_csv(checkpoint,index=False)
            print(f'West + matched controls: {k+1}/{n} samples, {len(rows)} seasonal trajectories',flush=True)
    result=pd.DataFrame(rows)
    assert len(result)==60*n
    result.to_csv(ROOT/'results/building_confirmed.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    return result


def supplemental(frame,meta,week):
    rows=[]
    for room,area in ROOM_AREAS.items():
        p=room_parameters(area,azimuth=270.)
        for kind in ['fixed','inverter']:
            for policy in POLICIES:
                a=simulate(forcing_for_parameters(week,meta,p),p,kind,policy)
                pd.DataFrame(a,columns=COLUMNS).to_csv(ROOT/f'results/west_trace_{room}_{kind}_{policy}.csv.gz',index=False,float_format='%.8g',compression={'method':'gzip','mtime':0})
                season=frame[frame.month.between(5,10)]
                ext=frame.loc[season.index[0]:season.index[-1]+6]
                full=simulate(forcing_for_parameters(ext,meta,p),p,kind,policy)
                rows.append(dict(room=room,kind=kind,policy=policy,azimuth=270.,**metrics(full[:len(season)*60],p,recovery_data=full)))
    pd.DataFrame(rows).to_csv(ROOT/'results/west_room_comparison.csv',index=False)
    phase=[]
    for u in np.linspace(.8,3.2,13):
        for area in [12.,15.,18.,21.,24.,27.,30.,33.,36.,40.,44.,48.]:
            p=room_parameters(area,u_wall=u,people=4.,azimuth=270.)
            w=forcing_for_parameters(week,meta,p)
            a=metrics(simulate(w,p,'fixed','always'),p);b=metrics(simulate(w,p,'fixed','cut_all'),p)
            phase.append(dict(kind='fixed',u_wall=u,area=area,people=4.,azimuth=270.,
                saving_pct=100*(1-b['energy_kWh']/a['energy_kWh']),
                extra_degree_hours=b['occupied_degree_hours']-a['occupied_degree_hours'],
                max_residual_W=max(a['enthalpy_residual_max_W'],b['enthalpy_residual_max_W'])))
    pd.DataFrame(phase).to_csv(ROOT/'results/west_phase.csv',index=False)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mc',type=int,default=128);parser.add_argument('--sobol',type=int,default=512)
    args=parser.parse_args();assert args.mc>=2 and args.mc%2==0
    assert args.sobol>=8 and not args.sobol&(args.sobol-1)
    (ROOT/'.cache').mkdir(exist_ok=True)
    signature=input_signature(args.mc,args.sobol)
    frames={};metas={}
    for station in ['shenzhen','guangzhou']:frames[station],metas[station]=load_epw(ROOT/'data',station)
    daily=frames['shenzhen'].groupby('doy')['T'].mean()
    end=int(daily.rolling(7).mean().loc[159:273].idxmax())
    cfg=dict(mc_n=args.mc,sobol_n=args.sobol,seed=SEED,hot_week_doy_start=end-6,
             hot_week_doy_end=end,dt_seconds=60,season_days=184,weather=metas,reused_rows=0)
    cfg.update(signature,baseline=asdict(room_parameters(azimuth=270.)),n_parameters=len(WEST_BOUNDS),
        mc_trajectories=60*args.mc,west_trajectories=42*args.mc,control_trajectories=18*args.mc,
        building_facts={'floor':2,'total_floors':None,'topfloor':False,'topfloor_status':'assumed non-topfloor because total floors unknown','corner':False,'exterior_wall':'balcony facade only','azimuth_baseline':270.,'azimuth_range':[240.,300.],'azimuth_status':'west confirmed by resident: direct sunset glare and shadow motion','east_control_range':[60.,120.]},
        geometry={'width':3.7,'length':6.2,'height':2.8,'glass_area':1.902075,'glass_range':[1.6,2.4],'metal_area':.945,'frame_area':.4638375},
        geometry_source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['scene/参数.json','data/openings_geometry.json']},
        west_bounds=WEST_BOUNDS,control_policies=['always','cut_all','manual'])
    mc=seasons(frames,metas,args.mc,signature)
    frame=frames['shenzhen'];week=frame[frame.doy.between(cfg['hot_week_doy_start'],cfg['hot_week_doy_end'])]
    supplemental(frame,metas['shenzhen'],week);print('West daily traces, fixed-size seasons and phase complete',flush=True)
    sobol,raw=sobol_analysis(week,metas['shenzhen'],args.sobol,lambda x:print('West '+x,flush=True),
        bounds=WEST_BOUNDS,labels=WEST_LABELS,parameter_factory=west_parameters)
    sobol.to_csv(ROOT/'results/west_sobol.csv',index=False)
    np.savez_compressed(ROOT/'results/west_sobol_raw.npz',outputs=raw)
    from acstudy.analysis import sobol_indices
    conv=[]
    for n in [args.sobol//2,args.sobol]:
        for k,(kind,output) in enumerate([('fixed','saving_kWh'),('fixed','extra_degree_hours'),('inverter','saving_kWh'),('inverter','extra_degree_hours')]):
            for i,key in enumerate(WEST_BOUNDS):
                s,st=sobol_indices(raw[0,:n,k],raw[1,:n,k],raw[i+2,:n,k])
                conv.append(dict(n=n,kind=kind,output=output,parameter=key,ST=st))
    pd.DataFrame(conv).to_csv(ROOT/'results/west_sobol_convergence.csv',index=False)
    (ROOT/'results/confirmed_config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
    from summarize_confirmed import summarize
    summarize()
    print('Confirmed-building numerical outputs complete. Render with render_figures.py --report',flush=True)

if __name__=='__main__':main()
