"""Reproduce data, verification, uncertainty, sensitivity, figures and draft."""
import argparse
from dataclasses import asdict,replace
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from acstudy.model import Parameters,simulate,COLUMNS,POLICIES,room_parameters
from acstudy.weather import load_epw,forcing,forcing_for_parameters
from acstudy.analysis import monte_carlo,sobol_analysis,metrics,BOUNDS,SEED,ROOM_AREAS
from acstudy.plots import make_plots,NAMES,TYPES
N_POLICY=len(POLICIES)


def interval(x,digits=1):
    lo,med,hi=np.quantile(x,[.05,.5,.95])
    return f'{med:.{digits}f}（{lo:.{digits}f}–{hi:.{digits}f}）'


def save_quantiles(mc):
    rows=[]
    for room in ROOM_AREAS:
      for kind in TYPES:
        for policy in POLICIES:
            s=mc[(mc.room==room)&(mc.kind==kind)&(mc.policy==policy)]
            for col in ['workday_kWh','energy_kWh','saving_pct','return_C','return_RH',
                        'return_HI','recovery_median_min','recovery_unmet_fraction',
                        'rest_peak_C','terminal_extra_sensible_kWh']:
                q=np.quantile(s[col],[.05,.5,.95])
                rows.append(dict(room=room,kind=kind,policy=policy,metric=col,p05=q[0],p50=q[1],p95=q[2]))
    pd.DataFrame(rows).to_csv(ROOT/'results/quantile_summary.csv',index=False)


def parameter_register():
    known={
      'people':('固定4','居住者确认四人间、实际4人；4–8人仅作附加人数扫描'),
      'width':('3.6–4.4','照片尺寸估计：床长约占3.3格，地砖更可能0.6m（中低把握）；过道三块砖，工作值3.7m'),
      'length':('5.8–6.4','家具贴墙关系与照片尺寸估计；基准6.0m'),
      'height':('2.6–3.2','假设；基准2.8m'),
      'window_area':('2.6–5.2','假设：阳台玻璃门及左侧两扇玻璃窗合计等效面积；基准3.8m²，不是实测'),
      'furniture_capacity':('200000–1000000','假设：两高架床、两落地床、四张L桌与四只铁柜的全室有效热容；材料质量未测，未采用未经测量的精确数值'),
      'building_capacity':('1000000–6000000','假设：19.2m²下内墙地顶有效蓄热；与家具分开'),
      'mass_capacity':('建筑有效热容*面积/19.2+四套家具热容','派生假设，家具不再乘四，不随地面积重复放大'),
      'wall_area':('width*height-window_area；转角另加length*height','派生：一面窗端外墙与转角情景择一，未把四面墙全算外墙'),
      'wall_capacity':('2e6*(wall_area+roof_area)/30','假设有效厚度；材料量级来自已存档EnergyPlus示例混凝土密度2242.585、比热836.8'),
      'roof_area':('0或实际地面积','非顶层/顶层替代情景；与地面积绑定，不独立抽样面积'),
      'area':('20.88–28.16；基准22.2，0.8m砖对照25.8，口述上限28.8','净宽乘净长，均非实测；对照长6m，宽分别4.3/4.8m'),
      'corner':('0或1','假设：单面窗端外墙/转角两面外墙，各半情景不是现实概率'),
      'topfloor':('0或1','假设：非顶层/顶层，各半情景不是现实概率'),
      'absorptance':('0.4–0.8','EnergyPlus示例混凝土太阳吸收率0.65，实际表面待核'),
      'moisture_ratio':('固定','PsychroLib公开湿空气实现0.621945，链接见方法说明'),
      'shr':('未使用','兼容字段；主模型显热比由进风温湿度与盘管露点决定'),
      'schedule_mode':('固定1','本人提供的四段固定断电，工作日与休息日均执行'),
      'cut_start':('未用于主分析','兼容的单段模式接口'),
      'cut_duration':('未用于主分析','兼容的单段模式接口'),
      'lunch_fraction':('0–1','假设：工作日午休返回概率，基准0.5；固定随机日历共享'),
      'evening_return_minutes':('0–60','假设：17:30下班至返回宿舍延迟，基准30分钟'),
      'lunch_arrival_minutes':('0–15','假设：午休返回日12:00后抵达延迟，基准5分钟'),
      'manual_delay_minutes':('0–5','假设：在场者来电或抵达后开机反应，基准1分钟；无人不自动开'),
    }
    ranges={'u_wall':'.8–3.2','u_window':'4.5–6.5','g_mass':'200–800，按实际面积/19.2缩放',
      'ach':'.2–1.5','shgc':'.35–.8','h_out':'10–25','person_sensible':'55–90',
      'person_latent':'35–75','equipment':'40–200','background':'0–40',
      'capacity':'2600–5000','cop':'2.6–4.8','min_fraction':'.15–.4','partload_gain':'0–.3',
      'temp_eir_slope':'.01–.04','temp_capacity_slope':'.005–.025','startup_seconds':'15–90',
      'hysteresis':'.3–1.0','control_seconds':'300–1200','fan_watts':'15–50','standby_watts':'0–3',
      'setpoint':'25–28','weather_delta':'-1–2','azimuth':'0–360','ground_albedo':'.1–.3',
      'coil_temperature':'8–15','rho_air':'1.1–1.3','cp_air':'1000–1020','latent_heat':'2400000–2500000',
      'min_on_seconds':'180–600','min_off_seconds':'120–300','coil_storage_kg':'0–.15',
      'evaporation_seconds':'600–3600','airflow':'.13–.30','bypass_factor':'.05–.30'}
    derived={'area','wall_area','roof_area','mass_capacity','wall_capacity'}
    rows=[]
    for key,value in asdict(Parameters()).items():
        span,source=known.get(key,(ranges.get(key,''),'假设：缺少实测或机组型号'))
        if key in BOUNDS and key not in known:span='–'.join(str(x) for x in BOUNDS[key])
        treatment=('基准输入独立均匀，按面积缩放后用于模型' if key=='g_mass'
                   else '等权离散替代情景' if key in ['corner','topfloor']
                   else '独立均匀情景输入' if key in BOUNDS
                   else '由几何/材料输入派生，已传播' if key in derived
                   else '固定；给范围供核对，未全局传播')
        rows.append(dict(parameter=key,baseline=value,range=span,source=source,
                         sampled=key in BOUNDS or key in derived,treatment=treatment))
    pd.DataFrame(rows).to_csv(ROOT/'data/parameters.csv',index=False)


def verification(frames,metas,week):
    records=[]
    w=forcing(week,metas['shenzhen'])
    for kind in TYPES:
        ref=None
        for dt in [60.,120.,300.]:
            try:
                a=simulate(w,kind=kind,policy='cut_all',dt=dt)
            except ValueError as error:
                records.append(dict(kind=kind,dt_s=dt,status='rejected_unstable',reason=str(error)))
                continue
            m=metrics(a,Parameters(),dt)
            if ref is None: ref=m
            records.append(dict(kind=kind,dt_s=dt,status='valid',**m,
                               energy_difference_vs_60_pct=100*(m['energy_kWh']/ref['energy_kWh']-1)))
    pd.DataFrame(records).to_csv(ROOT/'results/timestep_check.csv',index=False)
    from scipy.linalg import expm
    passive=replace(Parameters(),capacity=0,people=0,equipment=0,background=0,ach=0,shgc=0,absorptance=0)
    weather=np.tile([32.,.009,101325.,0.,0.,0.],(24,1))
    pp=replace(passive,wall_area=0,g_mass=0)
    a=simulate(weather,pp,dt=60,warmup_hours=0,initial=[26,26,26,.009])
    ca=pp.rho_air*pp.area*pp.height*pp.cp_air
    exact=32.-6.*np.exp(-pp.u_window*pp.window_area*a[:,0]*3600/ca)
    single=float(np.max(abs(a[:,1]-exact)))
    pp=passive;g=2*pp.u_wall*pp.wall_area;gw=pp.u_window*pp.window_area
    mat=np.array([[-gw-pp.g_mass-g,pp.g_mass,g],[pp.g_mass,-pp.g_mass,0],[g,0,-2*g]])/np.array([ca,pp.mass_capacity,pp.wall_capacity])[:,None]
    a=simulate(weather,pp,dt=60,warmup_hours=0,initial=[26,26,26,.009])
    exact=32+expm(mat*86400)@np.full(3,-6.)
    validation=dict(single_node_max_error_C=single,three_node_end_error_C=float(np.max(abs(a[-1,1:4]-exact))),
                    dt_seconds=60,EnergyPlus='not run',field_data='not available')
    (ROOT/'results/validation.json').write_text(json.dumps(validation,indent=2))

    # Full common cooldown: compare one cut day followed by 72h always-on.
    records=[]
    hot=forcing(week,metas['shenzhen'])[:24]
    tail=np.tile(hot,(3,1))
    p=Parameters()
    for kind in TYPES:
        for policy in ['always','cut_all']:
            a=simulate(hot,p,kind,policy)
            b=simulate(tail,p,kind,'always',warmup_hours=0,initial=a[-1,[1,2,3,4]],initial_coil_water=a[-1,17])
            m=metrics(a,p)
            records.append(dict(kind=kind,policy=policy,first_day_kWh=m['energy_kWh'],
                                 next_72h_kWh=metrics(b,p)['energy_kWh'],
                                 combined_kWh=m['energy_kWh']+metrics(b,p)['energy_kWh'],
                                 terminal_air_C=b[-1,1],terminal_mass_C=b[-1,2],
                                 terminal_wall_C=b[-1,3],terminal_w=b[-1,4],
                                 max_residual_W=max(m['enthalpy_residual_max_W'],metrics(b,p)['enthalpy_residual_max_W'])))
    pd.DataFrame(records).to_csv(ROOT/'results/settlement_check.csv',index=False)
    # Warmup sensitivity using same weather sequence repeated, always-on.
    records=[]
    for kind in TYPES:
        for hours in [168,336,672]:
            a=simulate(w,kind=kind,policy='cut_all',warmup_hours=hours)
            records.append(dict(kind=kind,warmup_hours=hours,**metrics(a,p)))
    pd.DataFrame(records).to_csv(ROOT/'results/warmup_check.csv',index=False)
    # Same baseline parameters, alternate station, full season.
    records=[]
    for station in frames:
        f=frames[station];season=f[f.month.between(5,10)]
        extended=f.loc[season.index[0]:season.index[-1]+6]
        for kind in TYPES:
            for policy in POLICIES:
                full=simulate(forcing(extended,metas[station]),kind=kind,policy=policy)
                a=full[:len(season)*60]
                records.append(dict(station=station,kind=kind,policy=policy,**metrics(a,p,recovery_data=full)))
    pd.DataFrame(records).to_csv(ROOT/'results/station_check.csv',index=False)
    from acstudy.audit import reconstruct_budgets,electric_reconstruction
    audits=[]
    for kind in TYPES:
        for policy in POLICIES:
            aa=simulate(w,p,kind,policy,warmup_hours=0)
            audits.append(dict(kind=kind,policy=policy,
                **reconstruct_budgets(w,p,aa,[26,26,26,.012]),
                **electric_reconstruction(w,p,aa,kind)))
    pd.DataFrame(audits).to_csv(ROOT/'results/independent_budgets.csv',index=False)
    coils=[]
    for adp in [8.,10.,12.,14.]:
      for airflow in [.13,.18,.30]:
       for storage in [0.,.05,.15]:
        pp=replace(p,coil_temperature=adp,airflow=airflow,coil_storage_kg=storage)
        for kind in TYPES:
         for policy in ['always','cut_all']:
            aa=simulate(w,pp,kind,policy)
            coils.append(dict(adp_C=adp,airflow=airflow,storage_kg=storage,kind=kind,policy=policy,**metrics(aa,pp)))
    pd.DataFrame(coils).to_csv(ROOT/'results/coil_sensitivity.csv',index=False)
    people_rows=[]
    for count in [4.,6.,8.]:
      pp=replace(p,people=count)
      for kind in TYPES:
       for policy in ['always','cut_all','manual']:
        aa=simulate(w,pp,kind,policy)
        people_rows.append(dict(people=count,kind=kind,policy=policy,**metrics(aa,pp)))
    pd.DataFrame(people_rows).to_csv(ROOT/'results/people_sensitivity.csv',index=False)




def write_readme(mc,sobol,config):
    from acstudy.report import write_report
    write_report(ROOT,mc,sobol,config)


def phase_analysis(week,metas):
    phase=[]
    for kind in TYPES:
        for u in np.linspace(.8,3.2,13):
            for area in [12.,15.,18.,21.,24.,27.,30.,33.,36.,40.,44.,48.]:
                pp=room_parameters(area,u_wall=u,people=4.)
                w=forcing_for_parameters(week,metas['shenzhen'],pp)
                a=metrics(simulate(w,pp,kind,'always'),pp)
                b=metrics(simulate(w,pp,kind,'cut_all'),pp)
                phase.append(dict(kind=kind,u_wall=u,area=area,people=4.,
                                  saving_pct=100*(a['energy_kWh']-b['energy_kWh'])/a['energy_kWh'],
                                  extra_degree_hours=b['occupied_degree_hours']-a['occupied_degree_hours'],
                                  max_residual_W=max(a['enthalpy_residual_max_W'],b['enthalpy_residual_max_W'])))
    phase=pd.DataFrame(phase)
    phase.to_csv(ROOT/'results/phase.csv',index=False)
    return phase


def baseline_details(frame,metas):
    from acstudy.analysis import recovery_times,window_records
    records=[];windows=[];comparison=[]
    season=frame[frame.month.between(5,10)]
    f=frame.loc[season.index[0]:season.index[-1]+6]
    for room,area in ROOM_AREAS.items():
      pp=room_parameters(area)
      for kind in TYPES:
        for policy in POLICIES:
            full=simulate(forcing_for_parameters(f,metas['shenzhen'],pp),pp,kind,policy)
            a=full[:len(season)*60]
            comparison.append(dict(room=room,kind=kind,policy=policy,**metrics(a,pp,recovery_data=full)))
            win=window_records(a);win['room']=room;win['kind']=kind;win['policy']=policy;windows.append(win)
            rec,event=recovery_times(full,pp)
            tr,te=recovery_times(full,pp,humidity=False)
            for i,(r,e) in enumerate(zip(rec,event)):
                records.append(dict(room=room,kind=kind,policy=policy,workday_index=i,
                    temperature_minutes=tr[i],temperature_recovered=bool(te[i]),
                    joint_minutes=r,joint_recovered=bool(e),minutes=r,recovered=bool(e)))
    pd.DataFrame(records).to_csv(ROOT/'results/recovery_daily.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    pd.concat(windows,ignore_index=True).to_csv(ROOT/'results/window_daily.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    pd.DataFrame(comparison).to_csv(ROOT/'results/room_comparison.csv',index=False)


def save_summary(mc,sobol,phase,n):
    summary={'max_mc_enthalpy_residual_W':float(mc.enthalpy_residual_max_W.max()),
             'max_sobol_enthalpy_residual_W':float(sobol.max_enthalpy_residual_W.max()),
             'max_phase_enthalpy_residual_W':float(phase.max_residual_W.max()),
             'all_mc_samples':n,'room_classes':len(ROOM_AREAS),'mc_trajectories':n*len(ROOM_AREAS)*2*len(POLICIES),'distributions':'independent uniform continuous scenarios; equal-weight corner/topfloor alternatives; alternating stations',
             'EnergyPlus_validation':'not performed','field_validation':'not performed'}
    (ROOT/'results/summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mc',type=int,default=128)
    parser.add_argument('--sobol',type=int,default=512)
    parser.add_argument('--traces-only',action='store_true')
    args=parser.parse_args()
    if args.traces_only:
        from generate_traces import generate
        generate()
        return
    if args.mc<2 or args.mc%2 or args.sobol<8 or args.sobol&(args.sobol-1):
        parser.error('--mc must be positive even (>=2); --sobol must be a power of two (>=8)')
    for name in ['data','results','figures']: (ROOT/name).mkdir(exist_ok=True)
    proc=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=ROOT,capture_output=True,text=True)
    (ROOT/'results/test_report.txt').write_text(proc.stdout+proc.stderr)
    print(proc.stdout,flush=True)
    if proc.returncode: raise SystemExit(proc.returncode)
    frames,metas={},{}
    for station in ['shenzhen','guangzhou']:
        frames[station],metas[station]=load_epw(ROOT/'data',station)
    p=Parameters()
    parameter_register()
    frame=frames['shenzhen']
    # Hottest seven-day rolling mean within June–September, aligned to midnight.
    daily=frame.groupby('doy')['T'].mean()
    candidates=daily.rolling(7).mean().loc[159:273]
    end=int(candidates.idxmax())
    week=frame[frame.doy.between(end-6,end)]
    config=dict(mc_n=args.mc,sobol_n=args.sobol,seed=SEED,
                hot_week_doy_start=end-6,hot_week_doy_end=end,dt_seconds=60,
                season_days=184,n_parameters=len(BOUNDS),reused_rows=0,weather=metas,baseline=asdict(p))
    (ROOT/'results/config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2))
    verification(frames,metas,week)
    traces={}
    for room,area in ROOM_AREAS.items():
      for kind in TYPES:
        for policy in POLICIES:
            a=simulate(forcing_for_parameters(week,metas['shenzhen'],room_parameters(area)),room_parameters(area),kind=kind,policy=policy)
            traces[(room,kind,policy)]=a
            pd.DataFrame(a,columns=COLUMNS).to_csv(ROOT/f'results/trace_{room}_{kind}_{policy}.csv.gz',index=False,float_format='%.8g',compression={'method':'gzip','mtime':0})
            if room=='base':
                pd.DataFrame(a,columns=COLUMNS).to_csv(ROOT/f'results/trace_{kind}_{policy}.csv.gz',index=False,float_format='%.8g',compression={'method':'gzip','mtime':0})
    mc=monte_carlo(frames,metas,args.mc,lambda x:print(x,flush=True))
    mc.to_csv(ROOT/'results/monte_carlo.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    save_quantiles(mc)
    sobol,raw=sobol_analysis(week,metas['shenzhen'],args.sobol,lambda x:print(x,flush=True))
    sobol.to_csv(ROOT/'results/sobol.csv',index=False)
    np.savez_compressed(ROOT/'results/sobol_raw.npz',outputs=raw)
    conv=[]
    for n in [args.sobol//2,args.sobol]:
        for k,(kind,output) in enumerate([('fixed','saving_kWh'),('fixed','extra_degree_hours'),('inverter','saving_kWh'),('inverter','extra_degree_hours')]):
            ya,yb=raw[:2,:n,k]
            var=np.var(np.r_[ya,yb],ddof=1)
            for i,key in enumerate(BOUNDS):
                conv.append(dict(n=n,kind=kind,output=output,parameter=key,ST=.5*np.mean((ya-raw[i+2,:n,k])**2)/var))
    pd.DataFrame(conv).to_csv(ROOT/'results/sobol_convergence.csv',index=False)
    phase=phase_analysis(week,metas)
    baseline_details(frame,metas)
    from cycle_analysis import scan
    scan()
    save_summary(mc,sobol,phase,args.mc)
    # The broad building/azimuth study is supplemental. The public report
    # must always use the confirmed west-facing building, never its mixture.
    subprocess.run([sys.executable,str(ROOT/'run_confirmed.py'),'--mc',str(args.mc),'--sobol',str(args.sobol)],check=True)
    subprocess.run([sys.executable,str(ROOT/'verify_confirmed.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'render_figures.py'),'--report'],check=True)
    print('All calculations, figures and draft are saved.',flush=True)


if __name__=='__main__': main()
