from dataclasses import replace
import numpy as np
import pandas as pd
from scipy.stats import qmc
from .model import Parameters, simulate, POLICIES,room_parameters
from .weather import forcing,forcing_for_parameters

SEED = 20261113
# Independent uniform scenario ranges, NOT fitted probability distributions.
BOUNDS = {
    'u_wall':(.8,3.2),'ach':(.2,1.5),'building_capacity':(1.e6,6.e6),
    'furniture_capacity':(200000.,1000000.),'azimuth':(0.,360.),'cop':(2.6,4.8),
    'capacity':(2600.,5000.),'weather_delta':(-1.,2.),'lunch_fraction':(0.,1.),
    'coil_temperature':(8.,15.),'airflow':(.13,.30),'startup_seconds':(15.,90.),
    'setpoint':(25.,28.),'topfloor':(0.,1.),'corner':(0.,1.),'shgc':(.35,.8),
    'width':(3.6,4.4),'length':(6.0,6.4),'height':(2.6,3.2),'window_area':(1.6,2.4),
    'evening_return_minutes':(0.,60.),'lunch_arrival_minutes':(0.,15.),
    'manual_delay_minutes':(0.,5.),'g_mass':(200.,800.),
    'u_metal':(3.,7.),'metal_absorptance':(.20,.70),
    'u_frame':(3.,7.),'frame_absorptance':(.15,.65)}
LABELS = ['墙体传热','换气','建筑内蓄热','四套家具蓄热','朝向','额定能效',
          '制冷能力','室外温度','午休返回概率','盘管温度','盘管风量','启动爬升',
          '设定温度','顶层情景','转角情景','玻璃太阳得热','净宽','净长','净高',
          '玻璃门窗面积','下班返回延迟','午休返回延迟','手动开机反应','室内热耦合','金属门传热','金属门太阳吸收','门窗框传热','门窗框太阳吸收']
ROOM_AREAS={'base':22.94,'tile80':26.66,'upper':29.76}


def sobol_indices(a,b,c):
    var=np.var(np.r_[a,b],ddof=1)
    s=np.mean((b-np.mean(np.r_[a,b]))*(c-a))/var
    st=.5*np.mean((a-c)**2)/var
    return s,st


def scenario_units(n):
    # Keep the original 24 unresolved-input draws paired across geometry changes.
    original=np.random.default_rng(SEED).random((n,24))
    extra=np.random.default_rng(SEED+2).random((n,len(BOUNDS)-24))
    return np.column_stack([original,extra])


def parameters_from_unit(row,room='base'):
    d={key:lo+(hi-lo)*float(x) for x,(key,(lo,hi)) in zip(row,BOUNDS.items())}
    if room=='upper':d.update(width=4.8,length=6.2)
    elif room=='tile80':d.update(width=4.3,length=6.2)
    d['corner']=float(d['corner']>=.5)
    d['topfloor']=float(d['topfloor']>=.5)
    return room_parameters(**d)


def recovery_times(a, p, dt=60., humidity=True):
    nday = len(a)//int(86400/dt)
    values, events = [], []
    for day in range(nday):
        if day%7>=5: continue
        begin = int((day*24+17.5+p.evening_return_minutes/60.)*3600/dt)
        end = min(len(a),begin+int(6*3600/dt))
        good = (a[begin:end,1]<=28.)
        if humidity: good &= (a[begin:end,5]<=65.)
        duration = int(1800/dt)
        found = False
        for j in range(max(0,len(good)-duration+1)):
            if good[j:j+duration].all():
                values.append(j*dt/60.)
                events.append(True)
                found=True
                break
        if not found:
            values.append((end-begin)*dt/60.)
            events.append(False)
    return np.asarray(values),np.asarray(events)


def metrics(a,p,dt=60.,recovery_data=None):
    step_h = dt/3600.
    days = np.arange(len(a))//int(86400/dt)
    weekend = days%7>=5
    hours=(np.arange(len(a))%int(86400/dt))*dt/3600
    cut_clock=((hours>=8)&(hours<10.5) | (hours>=10.+2./3.)&(hours<12)
               | (hours>=13.5)&(hours<15) | (hours>=15.+1./6.)&(hours<17.5))
    occupied = a[:,14]
    daily = np.bincount(days,weights=a[:,7]*step_h/1000.)
    wd = np.arange(len(daily))%7<5
    rec,event = recovery_times(a if recovery_data is None else recovery_data,p,dt)
    temp_rec,temp_event=recovery_times(a if recovery_data is None else recovery_data,p,dt,humidity=False)
    # Recovery quantiles include right-censored values (identified by flag).
    returns = [int((day*24+17.5+p.evening_return_minutes/60.)*3600/dt)-1 for day in range(len(daily)) if day%7<5]
    returns = np.asarray([i for i in returns if i<len(a)],dtype=int)
    restores=np.asarray([int((day*24+17.5)*3600/dt)-1 for day in range(len(daily)) if day%7<5],dtype=int)
    end = p.rho_air*p.area*p.height*p.cp_air*a[-1,1]+p.mass_capacity*a[-1,2]+p.wall_capacity*a[-1,3]
    latent_end = p.rho_air*p.area*p.height*p.latent_heat*a[-1,4]
    return dict(energy_kWh=float(daily.sum()),workday_kWh=float(daily[wd].mean()),
                restday_kWh=float(daily[~wd].mean()) if (~wd).any() else np.nan,
                occupied_degree_hours=float((np.maximum(a[:,1]-28.,0)*occupied).sum()*step_h),
                occupied_hot_hours=float(((a[:,1]>28)*occupied).sum()*step_h),
                occupied_humid_hours=float(((a[:,5]>65)*occupied).sum()*step_h),
                rest_hot_hours=float(((a[:,1]>28)*weekend).sum()*step_h),
                rest_humid_hours=float(((a[:,5]>65)*weekend).sum()*step_h),
                rest_cut_mean_C=float(a[weekend&cut_clock,1].mean()) if (weekend&cut_clock).any() else np.nan,
                rest_cut_mean_RH=float(a[weekend&cut_clock,5].mean()) if (weekend&cut_clock).any() else np.nan,
                rest_peak_C=float(a[weekend,1].max()) if weekend.any() else np.nan,
                return_C=float(np.mean(a[returns,1])) if len(returns) else np.nan,
                restore_C=float(np.mean(a[restores,1])) if len(restores) else np.nan,
                restore_RH=float(np.mean(a[restores,5])) if len(restores) else np.nan,
                return_RH=float(np.mean(a[returns,5])) if len(returns) else np.nan,
                return_HI=float(np.mean(a[returns,6])) if len(returns) else np.nan,
                peak_C=float(a[:,1].max()),peak_RH=float(a[:,5].max()),peak_HI=float(a[:,6].max()),
                temperature_recovery_median_min=float(np.median(temp_rec)) if len(temp_rec) else np.nan,
                temperature_recovery_unmet_fraction=float(1-temp_event.mean()) if len(temp_event) else np.nan,
                temperature_unmet_30min=float(np.mean((temp_rec>30)|(~temp_event))) if len(temp_rec) else np.nan,
                temperature_unmet_90min=float(np.mean((temp_rec>90)|(~temp_event))) if len(temp_rec) else np.nan,
                joint_unmet_90min=float(np.mean((rec>90)|(~event))) if len(rec) else np.nan,
                operating_shr_mean=float(np.mean(a[a[:,21]>0,16])) if (a[:,21]>0).any() else 1.,
                delivered_cop=float((a[:,8]+a[:,9]).sum()/max(a[:,7].sum(),1.e-12)),
                cycles_per_day=float(a[:,22].sum()/len(daily)),
                coil_water_residual_max_kgs=float(np.abs(a[:,20]).max()),
                recovery_median_min=float(np.median(rec)) if len(rec) else np.nan,
                recovery_unmet_fraction=float(1-event.mean()) if len(event) else np.nan,
                sensible_residual_max_W=float(np.abs(a[:,10]).max()),
                water_residual_max_kgs=float(np.abs(a[:,11]).max()),
                enthalpy_residual_max_W=float(np.abs(a[:,10]+p.latent_heat*a[:,11]).max()),
                terminal_sensible_kWh=float(end/3.6e6),
                terminal_latent_kWh=float(latent_end/3.6e6))


def monte_carlo(frames,metas,n=128,progress=print):
    rng=np.random.default_rng(SEED)
    unit=scenario_units(n)
    rows=[]
    for k,u in enumerate(unit):
        station='shenzhen' if k%2==0 else 'guangzhou'
        frame=frames[station]
        season=frame[frame.month.between(5,10)]
        season_steps=len(season)*60
        extended=frame.loc[season.index[0]:season.index[-1]+6]
        for room in ROOM_AREAS:
            p=parameters_from_unit(u,room)
            weather=forcing_for_parameters(extended,metas[station],p)
            for kind in ['fixed','inverter']:
                reference=None
                for policy in POLICIES:
                    full=simulate(weather,p,kind,policy)
                    a=full[:season_steps]
                    m=metrics(a,p,recovery_data=full)
                    m.update(summarize_windows(a))
                    if policy=='always': reference=m
                    m.update(sample=k,station=station,kind=kind,policy=policy,room=room)
                    m.update({'p_'+key:getattr(p,key) for key in BOUNDS})
                    m['saving_kWh']=reference['energy_kWh']-m['energy_kWh']
                    m['saving_pct']=100*m['saving_kWh']/max(reference['energy_kWh'],1.e-9)
                    m['terminal_extra_sensible_kWh']=m['terminal_sensible_kWh']-reference['terminal_sensible_kWh']
                    m['terminal_extra_latent_kWh']=m['terminal_latent_kWh']-reference['terminal_latent_kWh']
                    rows.append(m)
        if (k+1)%16==0: progress(f'Uncertainty: {k+1}/{n} paired room scenarios')
    return pd.DataFrame(rows)


def sobol_analysis(frame,meta,n=512,progress=print,*,bounds=None,labels=None,parameter_factory=None):
    """Saltelli first order + Jansen total order; paired bootstrap intervals.

    Independent Sobol base columns in 2D dimensions, no negative clipping.
    Outputs: weekly saved electricity and extra occupied degree-hours.
    """
    bounds=BOUNDS if bounds is None else bounds
    labels=LABELS if labels is None else labels
    parameter_factory=parameters_from_unit if parameter_factory is None else parameter_factory
    d=len(bounds)
    engine=qmc.Sobol(2*d,scramble=True,seed=SEED)
    unit=engine.random_base2(int(np.log2(n)))
    if len(unit)!=n: raise ValueError('n must be a power of two')
    aa,bb=unit[:,:d],unit[:,d:]
    blocks=[aa,bb]+[np.column_stack([bb[:,j] if j==i else aa[:,j] for j in range(d)]) for i in range(d)]
    all_y=[]
    balance=[]
    for ib,block in enumerate(blocks):
        ys=[]
        for u in block:
            p=parameter_factory(u)
            w=forcing_for_parameters(frame,meta,p)
            each=[]
            for kind in ['fixed','inverter']:
                a=metrics(simulate(w,p,kind,'always'),p)
                b=metrics(simulate(w,p,kind,'cut_all'),p)
                each.extend([a['energy_kWh']-b['energy_kWh'],
                             b['occupied_degree_hours']-a['occupied_degree_hours']])
                balance.append(max(a['enthalpy_residual_max_W'],b['enthalpy_residual_max_W']))
            ys.append(each)
        all_y.append(np.array(ys))
        progress(f'Sensitivity: block {ib+1}/{len(blocks)}')
    ya,yb=all_y[:2]
    rng=np.random.default_rng(SEED+1)
    indices=[np.arange(n)]+[rng.integers(0,n,n) for _ in range(256)]
    rows=[]
    for k,(kind,output) in enumerate([('fixed','saving_kWh'),('fixed','extra_degree_hours'),
                                     ('inverter','saving_kWh'),('inverter','extra_degree_hours')]):
        for i,key in enumerate(bounds):
            estim=[]
            for idx in indices:
                a,b,c=ya[idx,k],yb[idx,k],all_y[i+2][idx,k]
                # Center B for finite-sample stability; population estimator unchanged.
                s,st=sobol_indices(a,b,c)
                estim.append((s,st))
            estim=np.array(estim)
            rows.append(dict(kind=kind,output=output,parameter=key,label=labels[i],
                             S1=estim[0,0],ST=estim[0,1],
                             S1_low=np.quantile(estim[1:,0],.025),S1_high=np.quantile(estim[1:,0],.975),
                             ST_low=np.quantile(estim[1:,1],.025),ST_high=np.quantile(estim[1:,1],.975),
                             n=n,simulations=2*n*(d+2),
                             max_enthalpy_residual_W=max(balance)))
    return pd.DataFrame(rows),np.array(all_y)

WINDOWS = {'morning':(10.5,10.+2./3.),'noon':(12.,13.5),'afternoon':(15.,15.+1./6.)}

def window_records(a,dt=60.):
    """Exact start/end samples; RH and actual water concentration are distinct."""
    nsub=int(3600/dt);day_steps=24*nsub;records=[]
    for day in range(len(a)//day_steps):
        for slot,(start,end) in WINDOWS.items():
            i=day*day_steps+int(round(start*nsub));j=day*day_steps+int(round(end*nsub))
            before,after=a[i-1],a[j-1]
            interval=a[i:j]
            good=(interval[:,1]<=28)&(interval[:,5]<=65)
            records.append(dict(day=day,daytype='rest' if day%7>=5 else 'work',slot=slot,
                someone_present=float(a[i:j,14].max()>0),start_C=before[1],end_C=after[1],drop_C=before[1]-after[1],
                start_RH=before[5],end_RH=after[5],change_RH=after[5]-before[5],
                start_w_gkg=1000*before[4],end_w_gkg=1000*after[4],drop_w_gkg=1000*(before[4]-after[4]),
                joint_end=float(after[1]<=28 and after[5]<=65),good_minutes=good.sum()*dt/60,
                energy_kWh=interval[:,7].sum()*dt/3.6e6,
                gross_condensation_kg=interval[:,9].sum()*dt/2450000.,
                drained_water_kg=interval[:,19].sum()*dt,evaporated_water_kg=interval[:,18].sum()*dt,
                coil_water_start_kg=before[17],coil_water_end_kg=after[17]))
    return pd.DataFrame(records)


def summarize_windows(a,dt=60.):
    # Vectorized seasonal averages; each MC row retains paired-window endpoints.
    steps=int(86400/dt);arr=a[:len(a)//steps*steps].reshape(-1,steps,a.shape[1])
    result={};day=np.arange(len(arr));nsub=int(3600/dt)
    for dtype,mask in [('work',day%7<5),('rest',day%7>=5),('returned',(day%7<5)&(arr[:,12*nsub:int(13.5*nsub),14].max(axis=1)>0))]:
        if not mask.any():
            for slot in WINDOWS:
                for key in ['start_C','end_C','drop_C','start_RH','end_RH','drop_w_gkg','joint_end_fraction']:
                    result[dtype+'_'+slot+'_'+key]=np.nan
            continue
        for slot,(begin,end) in WINDOWS.items():
            i=int(round(begin*nsub));j=int(round(end*nsub))
            before=arr[mask,i-1];after=arr[mask,j-1]
            prefix=dtype+'_'+slot+'_'
            for key,values in [('start_C',before[:,1]),('end_C',after[:,1]),('drop_C',before[:,1]-after[:,1]),
                               ('start_RH',before[:,5]),('end_RH',after[:,5]),
                               ('drop_w_gkg',1000*(before[:,4]-after[:,4])),
                               ('joint_end_fraction',((after[:,1]<=28)&(after[:,5]<=65)).astype(float))]:
                result[prefix+key]=float(np.mean(values))
    return result
