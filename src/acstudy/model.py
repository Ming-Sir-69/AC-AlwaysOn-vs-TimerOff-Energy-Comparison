"""Three thermal stores and one dry-air humidity store; SI units throughout."""
from dataclasses import dataclass, asdict, replace
import numpy as np
from numba import njit

# Shared seeded return calendar across every policy, room and AC type.
LUNCH_CALENDAR = np.random.default_rng(20261113).random(366)


@dataclass(frozen=True)
class Parameters:
    area: float = 22.2
    height: float = 2.8
    wall_area: float = 6.56
    roof_area: float = 0.
    window_area: float = 3.8
    u_wall: float = 2.
    u_window: float = 5.7
    mass_capacity: float = 3390625.
    wall_capacity: float = 437333.3333333333
    g_mass: float = 578.125
    ach: float = .6
    shgc: float = .65
    absorptance: float = .65
    h_out: float = 18.
    people: float = 4.
    person_sensible: float = 70.
    person_latent: float = 55.
    equipment: float = 100.
    background: float = 20.
    capacity: float = 3500.
    cop: float = 3.5
    shr: float = .75
    min_fraction: float = .25
    partload_gain: float = .18
    temp_eir_slope: float = .025
    temp_capacity_slope: float = .012
    startup_seconds: float = 45.
    hysteresis: float = .5
    control_seconds: float = 600.
    fan_watts: float = 25.
    standby_watts: float = 1.
    setpoint: float = 26.
    cut_start: float = 8.
    cut_duration: float = 10.
    weather_delta: float = 0.
    azimuth: float = 180.
    ground_albedo: float = .2
    coil_temperature: float = 12.
    rho_air: float = 1.2
    cp_air: float = 1006.
    latent_heat: float = 2450000.
    moisture_ratio: float = .621945

    schedule_mode: float = 1.
    lunch_fraction: float = .5

    min_on_seconds: float = 300.
    min_off_seconds: float = 180.
    coil_storage_kg: float = .05
    evaporation_seconds: float = 1800.
    airflow: float = .18
    bypass_factor: float = .15

    corner: float = 0.
    width: float = 3.7
    length: float = 6.
    evening_return_minutes: float = 30.
    lunch_arrival_minutes: float = 5.
    manual_delay_minutes: float = 1.
    furniture_capacity: float = 500000.
    building_capacity: float = 2500000.
    topfloor: float = 0.

    def vector(self):
        return np.array(list(asdict(self).values()), dtype=float)


def room_parameters(area=22.2, **overrides):
    if abs(area-28.8)<1e-8: width,length=4.8,6.
    elif abs(area-25.8)<1e-8: width,length=4.3,6.
    else:
        width=np.sqrt(area*3.7/6.)
        length=area/width
    values=asdict(Parameters())
    values.update(width=width,length=length)
    values.update(overrides)
    area=values['width']*values['length']
    facade=values['width']*values['height']-values['window_area']
    if facade<=0:raise ValueError('Glazed openings exceed the facade area')
    wall=facade+(values['length']*values['height'] if values['corner']>.5 else 0.)
    roof=area if values['topfloor']>.5 else 0.
    values.update(area=area,wall_area=wall,roof_area=roof,
                  mass_capacity=values['building_capacity']*area/19.2+values['furniture_capacity'],
                  wall_capacity=2.e6*(wall+roof)/30.,g_mass=overrides.get('g_mass',500.)*area/19.2)
    return Parameters(**values)


@njit(cache=True)
def psat(t):
    # Magnus approximation, coefficients explicitly treated as approximations.
    return 610.94 * np.exp(17.625*t/(t+243.04))


@njit(cache=True)
def humidity_ratio(t, rh, pressure=101325.):
    pv = psat(t)*rh/100.
    return .621945*pv/(pressure-pv)


@njit(cache=True)
def relative_humidity(t, w, pressure):
    return 100.*pressure*w/(.621945+w)/psat(t)


@njit(cache=True)
def heat_index(t, rh):
    f = t*1.8+32.
    simple = .5*(f+61.+1.2*(f-68.)+.094*rh)
    hi = .5*(simple+f)
    if hi >= 80.:
        hi = (-42.379+2.04901523*f+10.14333127*rh-.22475541*f*rh
              -.00683783*f*f-.05481717*rh*rh+.00122874*f*f*rh
              +.00085282*f*rh*rh-.00000199*f*f*rh*rh)
        if rh < 13. and 80. <= f <= 112.:
            hi -= (13.-rh)/4.*np.sqrt((17.-abs(f-95.))/17.)
        elif rh > 85. and 80. <= f <= 87.:
            hi += (rh-85.)/10.*(87.-f)/5.
    return (hi-32.)/1.8


@njit(cache=True)
def schedule(hour, day, policy, p):
    weekend = day % 7 >= 5
    arrival=17.5+p[53]/60.
    lunch_arrival=12.+p[54]/60.
    lunch = lunch_arrival <= hour < 13.5 and LUNCH_CALENDAR[day%366] < p[43]
    presence = 1. if weekend or hour < 8. or hour >= arrival or lunch else 0.
    if p[42] == 1.:
        cut = (8. <= hour < 10.5 or 10.+2./3. <= hour < 12.
               or 13.5 <= hour < 15. or 15.+1./6. <= hour < 17.5)
    else:
        cut = p[32] <= hour < p[32]+p[33]
    allowed, target = True, p[31]
    if policy == 1 or policy == 6:
        allowed = not cut
    elif policy == 2:
        allowed = weekend or not cut
    elif policy == 3:
        allowed = weekend or not cut or 11. <= hour < 12. or 16.5 <= hour < 17.5
    elif policy == 4 and presence == 0.:
        target = max(30.,target)
    return allowed,presence,target


@njit(cache=True)
def manual_ready(hour,day,policy,p):
    if policy==0 or policy==4 or policy==6:return True
    weekend=day%7>=5
    delay=p[55]/60.
    if weekend:
        if policy!=1:return True
        if hour<8.:return True
        if 10.5<=hour<10.+2./3.:return hour>=10.5+delay
        if 12.<=hour<13.5:return hour>=12.+delay
        if 15.<=hour<15.+1./6.:return hour>=15.+delay
        if hour>=17.5:return hour>=17.5+delay
        return False
    if hour<8.:return True
    if 12.+p[54]/60.<=hour<13.5:
        return hour>=12.+(p[54]+p[55])/60. and LUNCH_CALENDAR[day%366]<p[43]
    return hour>=17.5+(p[53]+p[55])/60.


@njit(cache=True)
def simulate_core(weather, p, kind, policy, dt=60., warmup_hours=168,
                  initial=np.array([26.,26.,26.,.012]), day_offset=0,initial_coil_water=0.):
    """weather hourly [T,w,P,Iwall,Iroof,Iwindow]; output end-step states.

    Warmup repeats the first seven weather days under common always-on policy.
    Sensible residual and water residual are independent external budget checks.
    Natural condensation is booked as water sink + sensible latent-heat source.
    """
    nsub = int(3600./dt)
    n = len(weather)*nsub
    nwarm = warmup_hours*nsub
    out = np.empty((n, 25))
    ta, tm, tw, w = initial.copy()
    on, elapsed = False, 0.
    off_elapsed=p[45]
    coil_water=initial_coil_water
    air_mass = p[38]*p[0]*p[1]
    ca = air_mass*p[39]
    cm, cw = p[7], p[8]
    ua = p[5]*(p[2]+p[3])
    gext = 2.*ua
    gint = 2.*ua
    gw = p[6]*p[4]
    mdot = air_mass*p[10]/3600.
    hfg = p[40]
    for i in range(-nwarm, n):
        j = (i+nwarm) % min(len(weather)*nsub, 168*nsub) if i < 0 else i
        ih = j//nsub
        hour = (j*dt/3600.) % 24.
        day = int(j*dt/86400.)+day_offset
        active_policy = 0 if i < 0 else policy
        allowed, occupied, target = schedule(hour, day, active_policy, p)
        ac_allowed=allowed and manual_ready(hour,day,active_policy,p)
        to = weather[ih,0]+p[34]
        wo, pressure = weather[ih,1], weather[ih,2]
        solwall, solroof, solwin = weather[ih,3], weather[ih,4], weather[ih,5]
        # Exterior sol-air; roof and walls share one envelope node.
        solar_ext = p[12]/p[13]*(p[2]*solwall+p[3]*solroof)
        te = to + solar_ext/max(p[2]+p[3], 1.e-9)
        qsolar = p[4]*p[11]*solwin
        internal = p[14]*p[15]*occupied + ((p[18]+p[17]*occupied) if allowed else 0.)
        vapor = p[14]*p[16]*occupied/hfg
        # Split shortwave equally between air and mass as an explicit assumption.
        qa_ext = gw*(to-ta)+mdot*p[39]*(to-ta)+internal+.5*qsolar
        qm_ext = .5*qsolar
        qwa, qma = gint*(tw-ta), p[9]*(tm-ta)
        cap = p[19]*max(.55, 1.-p[25]*(to-35.))
        # ADP/bypass approximation: latent share grows with entering moisture.
        ws=humidity_ratio(p[37],100.,pressure)
        sensible_potential=p[39]*max(0.,ta-p[37])
        latent_potential=hfg*max(0.,w-ws)
        sensible_share=sensible_potential/max(sensible_potential+latent_potential,1.e-9)
        sensible_share=max(.05,min(1.,sensible_share))
        airside_limit=p[48]*(p[19]/3500.)*(1.-p[49])*(sensible_potential+latent_potential)
        cap=min(cap,airside_limit)
        frac = 0.
        active_time = dt
        was_on=on
        air_load = qa_ext+qwa+qma
        if ac_allowed and cap > 0.:
            if kind == 0:
                if not on and off_elapsed>=p[45] and ta >= target+p[27]: on = True
                elif on and elapsed>=p[44] and ta <= target-p[27]: on = False
                if not on and off_elapsed>=p[45] and ta < target+p[27] and air_load > 0.:
                    crossing = ca*(target+p[27]-ta)/air_load
                    if crossing < dt:
                        on = True
                        active_time = dt-max(0.,crossing)
                frac = 1. if on else 0.
            else:
                # Feed-forward load plus proportional pull-down.
                request = (qa_ext+qwa+qma+ca*(ta-target)/p[28])/sensible_share
                if on and elapsed>=p[44] and ta < target-p[27]: on = False
                elif not on and off_elapsed>=p[45] and (request > cap*p[22] or ta > target+p[27]): on = True
                frac = min(1.,max(p[22],request/cap)) if on else 0.
        else:
            on = False
        if on and not was_on: elapsed=0.
        previous = elapsed
        elapsed = elapsed+active_time if frac > 0. else 0.
        tau = max(p[26],1.e-9)
        before = previous*previous/(2*tau) if previous<tau else previous-tau/2.
        after = elapsed*elapsed/(2*tau) if elapsed<tau else elapsed-tau/2.
        ramp = (after-before)/dt if frac>0. else 0.
        qtotal = cap*frac*ramp
        qs = qtotal*sensible_share
        # Locate lower thermostat crossing within this Euler interval; average
        # compressor runtime rather than applying a whole interval of overcooling.
        runtime_scale = 1.
        needed = max(0.,air_load+ca*(ta-target+p[27])/dt)
        minimum_run=max(0.,p[44]-previous)
        if qs>needed and qs>0. and minimum_run<active_time:
            minimum_end=previous+minimum_run
            minimum_integral=minimum_end*minimum_end/(2*tau) if minimum_end<tau else minimum_end-tau/2.
            runtime_scale = max(needed/qs,(minimum_integral-before)/max(after-before,1.e-9))
            qs *= runtime_scale
            qtotal *= runtime_scale
        available_vapor = max(0., (w-humidity_ratio(p[37],100.,pressure))*air_mass/dt
                              +mdot*(wo-w)+vapor)
        ql = min(qtotal*(1.-sensible_share),available_vapor*hfg)
        # Unused latent capacity is not silently converted to sensible cooling.
        cop = p[20]/max(.5,1.+p[24]*(to-35.))
        if kind == 1:
            cop *= 1.+4.*p[23]*frac*(1.-frac)
        runtime_fraction = active_time/dt
        if runtime_scale<1.:
            integral_end = before+(after-before)*runtime_scale
            stop_time = np.sqrt(2*tau*integral_end) if integral_end<tau/2. else integral_end+tau/2.
            runtime_fraction = max(0.,stop_time-previous)/dt
        power = ((cap*frac/cop+p[29])*runtime_fraction+p[30]*(1-runtime_fraction)
                 if frac>0. else p[30]) if ac_allowed else (p[30] if allowed else 0.)
        # At zero capacity, no fan/compressor operation.
        if p[19] == 0.: power = p[30] if allowed else 0.
        if runtime_scale < 1.:
            on = False
            elapsed = 0.
        elif frac==0.:
            elapsed=0.
        if frac>0. and on: off_elapsed=0.
        elif frac>0.: off_elapsed=dt*(1.-runtime_fraction)
        else: off_elapsed=off_elapsed+dt if not was_on else dt
        old_coil_water=coil_water
        condensation=ql/hfg
        # Passive re-evaporation after the compressor stops, limited by saturation.
        evaporation=min(coil_water/max(p[47],dt),max(0.,humidity_ratio(ta,100.,pressure)-w)*air_mass/dt)*(1.-min(1.,runtime_fraction if frac>0. else 0.))
        coil_water=max(0.,coil_water+(condensation-evaporation)*dt)
        drain=max(0.,coil_water-p[46])/dt
        coil_water-=drain*dt
        coil_residual=(coil_water-old_coil_water)/dt-(condensation-evaporation-drain)
        dta = (qa_ext+qwa+qma-qs-hfg*evaporation)*dt/ca
        dtm = (qm_ext-qma)*dt/cm
        dtw = (gext*(te-tw)-qwa)*dt/cw
        dw = (mdot*(wo-w)+vapor-ql/hfg+evaporation)*dt/air_mass
        tan, tmn, twn, wn = ta+dta, tm+dtm, tw+dtw, w+dw
        # Rare supersaturation: solve local equilibrium with latent heat release.
        natural_cond = 0.
        if relative_humidity(tan,wn,pressure)>100.:
            lo, hi = 0., max(0.,wn)
            for _ in range(40):
                mid = (lo+hi)/2.
                tc = tan+mid*air_mass*hfg/ca
                if relative_humidity(tc,wn-mid,pressure)>100.: lo=mid
                else: hi=mid
            natural_cond = hi*air_mass/dt
            wn -= hi
            tan += natural_cond*hfg*dt/ca
        sensible_external = qa_ext+qm_ext+gext*(te-tw)-qs+natural_cond*hfg-hfg*evaporation
        stored = ca*(tan-ta)+cm*(tmn-tm)+cw*(twn-tw)
        residual = stored/dt-sensible_external
        water_residual = air_mass*(wn-w)/dt-(mdot*(wo-w)+vapor-ql/hfg+evaporation-natural_cond)
        ta, tm, tw, w = tan, tmn, twn, wn
        if i>=0:
            rh = relative_humidity(ta,w,pressure)
            out[i] = np.array([(i+1)*dt/3600.,ta,tm,tw,w,rh,heat_index(ta,rh),
                               power,qs,ql,residual,water_residual,
                               natural_cond,1.*allowed,1.*occupied,frac*runtime_fraction,
                               sensible_share,coil_water,evaporation,drain,coil_residual,
                               1.*(frac>0.),1.*(frac>0. and not was_on),frac,runtime_fraction if frac>0. else 0.])
    return out


COLUMNS = ['hour','air_C','mass_C','wall_C','humidity_kgkg','RH_pct',
           'heat_index_C','electric_W','sensible_cooling_W','latent_cooling_W',
           'sensible_residual_W','water_residual_kgs','natural_condensation_kgs',
           'power_available','occupied','compressor_fraction','dynamic_SHR',
           'coil_water_kg','coil_evaporation_kgs','coil_drain_kgs','coil_water_residual_kgs',
           'compressor_on','compressor_start','command_fraction','runtime_fraction']
POLICIES = ['always','cut_all','cut_workday','early60','setback30','manual','auto_restore']


def simulate(weather, parameters=Parameters(), kind='inverter', policy='always',
             dt=60., warmup_hours=168, initial=None, day_offset=0,initial_coil_water=0.):
    if dt <= 0 or dt > 300 or 3600 % dt != 0:
        raise ValueError('dt must divide an hour and be within (0,300] seconds')
    if parameters.cut_start+parameters.cut_duration > 24:
        raise ValueError('This schedule requires the cut to end within the same day')
    if kind not in ['fixed','inverter'] or policy not in POLICIES:
        raise ValueError('Unknown AC type or policy')
    # Explicit thermal-network stability: refuse a coarse step that would
    # turn numerical divergence into spurious low electricity or NaN states.
    p=parameters
    ca=p.rho_air*p.area*p.height*p.cp_air
    mass_flow_cp=p.rho_air*p.area*p.height*p.ach/3600*p.cp_air
    g=2*p.u_wall*(p.wall_area+p.roof_area)
    conductance=np.array([[p.u_window*p.window_area+mass_flow_cp+p.g_mass+g,-p.g_mass,-g],
                          [-p.g_mass,p.g_mass,0.],[-g,0.,2*g]])
    root_capacity=np.sqrt([ca,p.mass_capacity,p.wall_capacity])
    rate=np.linalg.eigvalsh(conductance/np.outer(root_capacity,root_capacity)).max()
    if dt*rate>=1.8:
        raise ValueError('Explicit timestep is unstable for this thermal network; use a shorter step')
    kw = {} if initial is None else {'initial': np.asarray(initial,dtype=float)}
    result=simulate_core(np.asarray(weather,dtype=float), parameters.vector(),
                         int(kind=='inverter'),POLICIES.index(policy),dt,warmup_hours,day_offset=day_offset,initial_coil_water=initial_coil_water,**kw)
    if not np.isfinite(result[-1]).all():
        raise FloatingPointError('Simulation produced non-finite states')
    return result
