import numpy as np
from scipy.stats import qmc
from acstudy.analysis import recovery_times,sobol_indices,metrics
from acstudy.model import Parameters,simulate


def test_thermostat_event_prevents_whole_step_overcooling():
    w=np.tile([32.,.015,101325.,0.,0.,0.],(24,1))
    from dataclasses import replace
    a=simulate(w,replace(Parameters(),min_on_seconds=0,min_off_seconds=0,coil_storage_kg=0),kind='fixed')
    assert a[:,1].min()>=25.5-1.e-10


def test_recovery_retains_censored_events():
    a=np.zeros((1440,16))
    a[:,1]=26.;a[:,5]=80.
    times,events=recovery_times(a,Parameters())
    assert len(times)==1 and times[0]==360. and not events[0]
    a[:,5]=60.
    times,events=recovery_times(a,Parameters())
    assert times[0]==0. and events[0]


def test_sobol_estimators_against_known_additive_function():
    # Analytic variance contributions of x + 2y with independent U(0,1).
    base=qmc.Sobol(4,scramble=True,seed=17).random_base2(12)
    a,b=base[:,:2],base[:,2:]
    ya,yb=a[:,0]+2*a[:,1],b[:,0]+2*b[:,1]
    for i,expected in enumerate([.2,.8]):
        ab=a.copy();ab[:,i]=b[:,i]
        yc=ab[:,0]+2*ab[:,1]
        s,total=sobol_indices(ya,yb,yc)
        assert abs(s-expected)<.003 and abs(total-expected)<.003


def test_reporting_keeps_sensible_and_latent_stores_separate():
    from dataclasses import replace
    p=replace(Parameters(),capacity=0,people=0,equipment=0,background=0,ach=0)
    w=np.tile([26.,.009,101325.,0.,0.,0.],(24,1))
    a=simulate(w,p,warmup_hours=0,initial=[26,26,26,.009])
    m=metrics(a,p)
    ca=p.rho_air*p.area*p.height*p.cp_air
    assert abs(m['terminal_sensible_kWh']-(ca+p.mass_capacity+p.wall_capacity)*26/3.6e6)<1.e-9
    assert abs(m['terminal_latent_kWh']-p.rho_air*p.area*p.height*p.latent_heat*.009/3.6e6)<1.e-9
    assert abs(m['energy_kWh']-.024)<1.e-9


def test_short_window_endpoints_with_extended_coil_state():
    from acstudy.analysis import summarize_windows,window_records
    w=np.tile([32.,.015,101325.,0.,0.,0.],(24,1))
    a=simulate(w,policy='cut_all')
    stats=summarize_windows(a)
    rows=window_records(a)
    assert len(rows)==3
    assert abs(stats['work_morning_start_C']-a[629,1])<1e-12
    assert abs(stats['work_morning_end_C']-a[639,1])<1e-12
    assert abs(stats['work_noon_start_C']-a[719,1])<1e-12
    assert abs(stats['work_noon_end_C']-a[809,1])<1e-12
