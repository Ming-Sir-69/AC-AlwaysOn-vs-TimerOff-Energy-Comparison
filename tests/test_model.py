from dataclasses import replace
import numpy as np
from scipy.linalg import expm
from acstudy.model import Parameters,simulate,humidity_ratio,schedule,heat_index


def constant(t=32.,hours=24,w=.009):
    return np.tile([t,w,101325.,0.,0.,0.],(hours,1))


def passive():
    return replace(Parameters(),capacity=0,people=0,equipment=0,background=0,
                   ach=0,shgc=0,absorptance=0)


def test_energy_and_moisture_conservation():
    for kind in ['fixed','inverter']:
        a=simulate(constant(w=.021),kind=kind,policy='cut_all')
        assert np.max(np.abs(a[:,10]))<1.e-7
        assert np.max(np.abs(a[:,11]))<1.e-12
        assert np.max(np.abs(a[:,10]+2450000*a[:,11]))<1.e-7
        assert np.min(a[:,4])>=0 and np.max(a[:,5])<=100.00001


def test_equilibrium_and_zero_capacity():
    p=passive()
    a=simulate(constant(26.),p,warmup_hours=0,initial=[26,26,26,.009])
    np.testing.assert_allclose(a[:,1:4],26.,atol=1.e-12)
    assert np.max(a[:,8:10])==0


def test_single_node_analytic():
    p=replace(passive(),wall_area=0,roof_area=0,g_mass=0)
    a=simulate(constant(),p,dt=60,warmup_hours=0,initial=[26,26,26,.009])
    ca=p.rho_air*p.area*p.height*p.cp_air
    exact=32.-6.*np.exp(-p.u_window*p.window_area*a[:,0]*3600/ca)
    error60=np.max(abs(a[:,1]-exact))
    coarse=simulate(constant(),p,dt=120,warmup_hours=0,initial=[26,26,26,.009])
    exact_coarse=32.-6.*np.exp(-p.u_window*p.window_area*coarse[:,0]*3600/ca)
    assert error60<.025
    assert error60<.55*np.max(abs(coarse[:,1]-exact_coarse))


def test_three_node_matrix_exponential():
    p=passive()
    ca=p.rho_air*p.area*p.height*p.cp_air
    g=p.u_wall*p.wall_area*2
    gw=p.u_window*p.window_area
    matrix=np.array([[-gw-p.g_mass-g,p.g_mass,g],
                     [p.g_mass,-p.g_mass,0],[g,0,-2*g]])/np.array([ca,p.mass_capacity,p.wall_capacity])[:,None]
    a=simulate(constant(),p,dt=60,warmup_hours=0,initial=[26,26,26,.009])
    exact=32+expm(matrix*86400)@np.full(3,-6.)
    np.testing.assert_allclose(a[-1,1:4],exact,atol=.003)


def test_linear_temperature_symmetry():
    p=passive()
    a=simulate(constant(30.),p,warmup_hours=0,initial=[28,28,28,.009])
    b=simulate(constant(22.),p,warmup_hours=0,initial=[24,24,24,.009])
    np.testing.assert_allclose(a[:,1:4]+b[:,1:4],52.,atol=1.e-10)


def test_fully_isolated_total_energy():
    p=replace(passive(),wall_area=0,window_area=0)
    a=simulate(constant(),p,warmup_hours=0,initial=[30,24,26,.009])
    ca=p.rho_air*p.area*p.height*p.cp_air
    energy=ca*a[:,1]+p.mass_capacity*a[:,2]+p.wall_capacity*a[:,3]
    np.testing.assert_allclose(energy,energy[0],atol=1.e-6)


def test_no_power_during_cut_and_capacity_limit():
    p=Parameters()
    for kind in ['fixed','inverter']:
        a=simulate(constant(40.,w=.023),p,kind,'cut_all')
        assert (a[a[:,13]==0,7:10]==0).all()
        assert (a[:,8]+a[:,9] <= p.capacity*(1-p.temp_capacity_slope*5)+1.e-9).all()


def test_common_policy_start_and_reproducibility():
    a=simulate(constant(),policy='always')
    b=simulate(constant(),policy='cut_all')
    np.testing.assert_array_equal(a[:8*60],b[:8*60])
    np.testing.assert_array_equal(b,simulate(constant(),policy='cut_all'))


def test_schedules_weekend_and_early():
    p=Parameters().vector()
    assert schedule(12,5,1,p)==(True,1.,26.)
    assert schedule(12,5,2,p)==(True,True,26.)
    assert schedule(17,0,3,p)[0]
    assert schedule(11,0,4,p)[2]==30.


def test_humidity_conversion_and_heat_index():
    from acstudy.model import relative_humidity
    assert abs(relative_humidity(30.,humidity_ratio(30.,60.),101325.)-60.)<1.e-10
    assert abs(heat_index((90-32)/1.8,70.)-(105.9220206-32)/1.8)<.01


def test_supersaturation_has_explicit_water_and_heat_budget():
    p=replace(passive(),wall_area=0,window_area=0,g_mass=0)
    a=simulate(constant(),p,warmup_hours=0,initial=[20,20,20,.025])
    assert a[0,12]>0
    assert a[0,5]<=100.00001
    assert abs(a[0,10])<1.e-7 and abs(a[0,11])<1.e-12


def test_actual_four_segment_schedule_boundaries():
    p=replace(Parameters(),lunch_fraction=1.,lunch_arrival_minutes=0).vector()
    cuts=[(8.,10.5),(10.+2./3.,12.),(13.5,15.),(15.+1./6.,17.5)]
    for start,end in cuts:
        assert not schedule(start,0,1,p)[0]
        assert not schedule(end-1/60,6,1,p)[0]
        assert schedule(end,0,1,p)[0]
    assert schedule(12,0,1,p)[1]==1.
    assert schedule(10.5,0,1,p)[1]==0.
    assert schedule(8,6,1,p)[1]==1.
    assert schedule(8,6,2,p)[0]
    assert schedule(11,0,3,p)[0] and schedule(16.5,0,3,p)[0]


def test_coil_water_balance_and_state_dependent_latent_split():
    wet=simulate(constant(w=.022),policy='always')
    dry=simulate(constant(w=.009),policy='always')
    assert np.max(abs(wet[:,20]))<1.e-12
    assert wet[:,17].min()>=0 and wet[:,17].max()<=Parameters().coil_storage_kg+1.e-10
    assert wet[:,9].mean()>dry[:,9].mean()
    stopped=simulate(constant(w=.022),policy='cut_all')
    assert stopped[:,18].max()>0.


def test_minimum_on_off_and_manual_power_retained():
    a=simulate(constant(),kind='fixed')
    run=a[:,21]>0
    changes=np.r_[0,np.flatnonzero(run[1:]!=run[:-1])+1,len(run)]
    for begin,end in zip(changes[1:-2],changes[2:-1]):
        minimum=Parameters().min_on_seconds if run[begin] else Parameters().min_off_seconds
        assert (end-begin)*60>=minimum-60
    a=simulate(constant(),policy='manual')
    assert (a[:,13]==1).all()
    assert (a[a[:,14]==0,8:10]==0).all()


def test_humidity_node_against_infiltration_analytic_solution():
    p=replace(passive(),ach=.6)
    a=simulate(constant(26.,w=.015),p,dt=60,warmup_hours=0,initial=[26,26,26,.010])
    exact=.015+(.010-.015)*np.exp(-.6*a[:,0])
    assert np.max(abs(a[:,4]-exact))<1.e-5


def test_manual_restart_matches_actual_presence_and_reaction():
    from acstudy.model import manual_ready
    p=replace(Parameters(),lunch_fraction=1.)
    w=constant()
    a=simulate(w,p,policy='cut_all')
    automatic=simulate(w,p,policy='auto_restore')
    assert a[630:640,8:10].sum()==0 and a[900:910,8:10].sum()==0
    assert automatic[630:640,8:10].sum()>0
    assert a[720:726,8:10].sum()==0
    assert a[1050:1081,8:10].sum()==0
    assert not manual_ready(18.,0,1,p.vector())
    assert manual_ready(18.+1/60,0,1,p.vector())
    rest=simulate(w,p,policy='cut_all',day_offset=5)
    assert rest[630,8:10].sum()==0
    assert rest[631:640,8:10].sum()>0


def test_unstable_coarse_step_is_rejected_instead_of_saving_nans():
    import pytest
    with pytest.raises(ValueError,match='unstable'):
        simulate(constant(),dt=300)
    assert np.isfinite(simulate(constant(),dt=120)).all()
