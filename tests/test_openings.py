from dataclasses import replace
import numpy as np
from acstudy.model import Parameters,room_parameters,simulate
from acstudy.audit import reconstruct_budgets
from acstudy.analysis import scenario_units,SEED


def test_facade_partition_has_no_glass_metal_frame_overlap():
 p=room_parameters()
 assert np.isclose(p.area,22.94) and p.length==6.2
 assert np.isclose(p.window_area,2*.495*1.085+.830*.9975)
 assert np.isclose(p.metal_area,.9*1.05)
 assert np.isclose(p.wall_area+p.window_area+p.metal_area+p.frame_area,p.width*p.height)
 assert np.isclose(p.frame_area,2*(.565*1.155-.495*1.085)+.945*2.1225-.9*1.05-.830*.9975)


def test_metal_branch_is_opaque_and_energy_is_accounted():
 p=replace(room_parameters(),capacity=0,window_area=0,wall_area=0,roof_area=0,
           people=0,equipment=0,background=0,ach=0,g_mass=0,frame_area=0)
 weather=np.tile([30.,.012,101325.,0.,0.,600.],(24,1))
 hot=simulate(weather,p,warmup_hours=0,initial=[26,26,26,.012])
 dark=simulate(weather,replace(p,metal_absorptance=0),warmup_hours=0,initial=[26,26,26,.012])
 none=simulate(weather,replace(p,metal_area=0),warmup_hours=0,initial=[26,26,26,.012])
 assert hot[-1,1]>dark[-1,1]>none[-1,1]
 assert abs(reconstruct_budgets(weather,p,hot,[26,26,26,.012])['thermal_difference_J'])<.001
 assert hot[:,8:10].sum()==0


def test_first_24_uncertain_inputs_keep_the_published_random_pairing():
 np.testing.assert_array_equal(scenario_units(128)[:,:24],np.random.default_rng(SEED).random((128,24)))
 assert scenario_units(128).shape==(128,28)


def test_corner_solar_weights_exclude_glass_metal_and_frames():
 import pandas as pd
 from acstudy.weather import forcing,forcing_for_parameters
 p=room_parameters(corner=1.,azimuth=270.)
 frame=pd.DataFrame(dict(hour=[8,16],doy=[180,180],DNI=[800,800],DHI=[100,100],GHI=[500,500],T=[32,32],w=[.015,.015],P=[101325,101325]))
 meta=dict(latitude=23.,longitude=114.,timezone=8.)
 front=forcing(frame,meta,p.azimuth,p.ground_albedo)
 side=forcing(frame,meta,(p.azimuth+90)%360,p.ground_albedo)
 af=p.width*p.height-p.window_area-p.metal_area-p.frame_area
 actual=forcing_for_parameters(frame,meta,p)
 np.testing.assert_allclose(actual[:,3],(af*front[:,3]+p.length*p.height*side[:,3])/p.wall_area)
 np.testing.assert_allclose(actual[:,5],front[:,5])


def test_scene_parameters_and_thermal_geometry_agree():
 import json
 from pathlib import Path
 scene=json.loads((Path(__file__).resolve().parents[1]/'scene/参数.json').read_text())
 p=room_parameters();o=scene['openings']
 assert (p.width,p.length,p.height)==tuple(scene['room'][k] for k in ['width','length','height'])
 assert np.isclose(p.length,2*(scene['desk']['width']+scene['wardrobe']['width'])+scene['bed']['length'])
 glass=2*(o['window_width']-o['window_frame'])*(o['window_height']-o['window_frame'])
 glass+=(o['balcony_width']-2*o['leaf_frame'])*(o['balcony_height']-o['leaf_frame']-o['balcony_height']*o['balcony_split_fraction']-o['balcony_crossbar']/2)
 assert np.isclose(p.window_area,glass)
