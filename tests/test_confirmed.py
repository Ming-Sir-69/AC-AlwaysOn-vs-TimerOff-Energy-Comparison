import numpy as np
import pandas as pd
from acstudy.analysis import BOUNDS
from acstudy.confirmed import case_parameters,WEST_BOUNDS,west_parameters
from acstudy.presentation import baseline
from acstudy.weather import forcing_for_parameters


def test_building_controls_share_all_unresolved_inputs():
    u=np.linspace(.01,.99,len(BOUNDS))
    west=case_parameters(u)
    east=case_parameters(u,'east')
    roof=case_parameters(u,'west_top')
    corner=case_parameters(u,'west_corner')
    assert 240<=west.azimuth<=300 and np.isclose(east.azimuth,west.azimuth-180,atol=1e-12)
    for key in BOUNDS:
        if key not in ['azimuth','topfloor','corner']:
            assert getattr(west,key)==getattr(east,key)==getattr(roof,key)==getattr(corner,key)
    assert west.topfloor==0 and west.corner==0 and west.roof_area==0
    assert roof.roof_area==roof.area and roof.wall_area==west.wall_area
    assert corner.wall_area==west.wall_area+west.length*west.height
    assert east.wall_capacity==west.wall_capacity and corner.wall_capacity>west.wall_capacity


def test_west_sensitivity_removes_building_switches():
    assert 'topfloor' not in WEST_BOUNDS and 'corner' not in WEST_BOUNDS
    assert len(WEST_BOUNDS)==27
    for level,azimuth in [(0.,240.),(1.,300.)]:
        p=west_parameters(np.full(len(WEST_BOUNDS),level))
        assert p.azimuth==azimuth and p.roof_area==0 and p.corner==0


def test_report_does_not_mix_east_control_into_west_baseline():
    frame=pd.DataFrame([dict(building_case='west',p_topfloor=0,p_corner=0),
                        dict(building_case='east',p_topfloor=0,p_corner=0)])
    assert baseline(frame).building_case.tolist()==['west']


def test_west_facade_receives_afternoon_direct_sun_not_morning():
    # Equinox, near the timezone's standard meridian. Equal beam irradiation
    # isolates orientation and solar geometry rather than actual weather.
    frame=pd.DataFrame(dict(hour=[8,16],doy=[80,80],DNI=[800,800],DHI=[0,0],GHI=[0,0],T=[30,30],w=[.015,.015],P=[101325,101325]))
    meta=dict(latitude=23.,longitude=120.,timezone=8.)
    west=forcing_for_parameters(frame,meta,case_parameters(np.full(len(BOUNDS),.5)))
    east=forcing_for_parameters(frame,meta,case_parameters(np.full(len(BOUNDS),.5),'east'))
    assert west[1,5]>500 and west[0,5]==0
    assert east[0,5]>500 and east[1,5]==0
