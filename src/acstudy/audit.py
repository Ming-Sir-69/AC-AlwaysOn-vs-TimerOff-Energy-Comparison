"""Independent postprocessing: reconstruct budgets from inputs + saved states.

This module does not import simulator thermal-flow or electric-power functions.
It checks a prescribed no-warmup run with known initial stores.
"""
import numpy as np


def reconstruct_budgets(weather,p,a,initial,dt=60.):
    nsub=int(3600/dt)
    w=np.repeat(weather,nsub,axis=0)
    old=np.vstack([initial,np.column_stack([a[:-1,1],a[:-1,2],a[:-1,3],a[:-1,4]])])
    air_mass=p.rho_air*p.area*p.height
    ca=air_mass*p.cp_air
    mdot=air_mass*p.ach/3600
    outdoor=w[:,0]+p.weather_delta
    area=p.wall_area+p.roof_area
    ext=2*p.u_wall*area
    solair=outdoor+p.absorptance*(p.wall_area*w[:,3]+p.roof_area*w[:,4])/max(p.h_out*area,1e-9)
    solar=p.window_area*p.shgc*w[:,5]
    people=p.people*p.person_sensible*a[:,14]
    equipment=(p.background+p.equipment*a[:,14])*a[:,13]
    opaque=p.u_metal*p.metal_area*(outdoor-old[:,0]+p.metal_absorptance*w[:,5]/p.h_out)+p.u_frame*p.frame_area*(outdoor-old[:,0]+p.frame_absorptance*w[:,5]/p.h_out)
    ext_heat=(p.u_window*p.window_area*(outdoor-old[:,0])+opaque
              +mdot*p.cp_air*(outdoor-old[:,0])+ext*(solair-old[:,2])
              +solar+people+equipment-a[:,8]+p.latent_heat*(a[:,12]-a[:,18]))
    stored=(ca*(a[-1,1]-initial[0])+p.mass_capacity*(a[-1,2]-initial[1])
            +p.wall_capacity*(a[-1,3]-initial[2]))
    outside_water=mdot*(w[:,1]-old[:,3])+p.people*p.person_latent*a[:,14]/p.latent_heat
    water_out=a[:,19]+a[:,12]
    combined_water_change=air_mass*(a[-1,4]-initial[3])+a[-1,17]
    return dict(thermal_storage_J=float(stored),thermal_external_J=float(ext_heat.sum()*dt),
                thermal_difference_J=float(stored-ext_heat.sum()*dt),
                water_storage_kg=float(combined_water_change),
                water_external_kg=float(((outside_water-water_out)*dt).sum()),
                water_difference_kg=float(combined_water_change-((outside_water-water_out)*dt).sum()))


def electric_reconstruction(weather,p,a,kind,dt=60.,initial=(26.,26.,26.,.012)):
    outdoor=np.repeat(weather[:,0],int(3600/dt))+p.weather_delta
    cap=p.capacity*np.maximum(.55,1-p.temp_capacity_slope*(outdoor-35))
    previous_T=np.r_[initial[0],a[:-1,1]]
    previous_w=np.r_[initial[3],a[:-1,4]]
    pressure=np.repeat(weather[:,2],int(3600/dt))
    pv=610.94*np.exp(17.625*p.coil_temperature/(p.coil_temperature+243.04))
    saturated_w=.621945*pv/(pressure-pv)
    airside=p.airflow*(p.capacity/3500.)*(1-p.bypass_factor)*(p.cp_air*np.maximum(previous_T-p.coil_temperature,0)+p.latent_heat*np.maximum(previous_w-saturated_w,0))
    cap=np.minimum(cap,airside)
    cop=p.cop/np.maximum(.5,1+p.temp_eir_slope*(outdoor-35))
    if kind=='inverter':cop*=1+4*p.partload_gain*a[:,23]*(1-a[:,23])
    compressor=cap*a[:,15]/cop
    fan=p.fan_watts*a[:,24]
    standby=p.standby_watts*(a[:,13]-a[:,24])
    reported=a[:,7].sum()*dt/3.6e6
    rebuilt=(compressor+fan+standby).sum()*dt/3.6e6
    return dict(reported_kWh=float(reported),reconstructed_kWh=float(rebuilt),
                electric_difference_kWh=float(reported-rebuilt),
                compressor_kWh=float(compressor.sum()*dt/3.6e6),
                fan_kWh=float(fan.sum()*dt/3.6e6),standby_kWh=float(standby.sum()*dt/3.6e6),
                delivered_cop=float((a[:,8]+a[:,9]).sum()/max(a[:,7].sum(),1e-9)))
