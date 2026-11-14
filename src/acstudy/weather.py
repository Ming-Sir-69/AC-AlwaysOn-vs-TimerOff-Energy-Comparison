"""Strict EPW import; local standard hourly means, no invented missing data."""
from pathlib import Path
import hashlib
import json
import urllib.request
import numpy as np
import pandas as pd
from .model import humidity_ratio

STATIONS = {'shenzhen':'CHN_Guangdong.Shenzhen.594930_SWERA',
            'guangzhou':'CHN_Guangdong.Guangzhou.592870_CSWD'}
BASE = 'https://energyplus-weather.s3.amazonaws.com/asia_wmo_region_2/CHN/'


def load_epw(data_dir, station='shenzhen'):
    name = STATIONS[station]
    path = Path(data_dir)/(name+'.epw')
    url = BASE+name+'/'+name+'.epw'
    if not path.exists():
        path.write_bytes(urllib.request.urlopen(url,timeout=90).read())
    header = path.read_text().splitlines()[0].split(',')
    raw = pd.read_csv(path,skiprows=8,header=None)
    if len(raw)!=8760:
        raise ValueError('Expected a non-leap 8760-hour typical weather year')
    frame = pd.DataFrame({
        'month':raw[1], 'day':raw[2], 'hour':raw[3]-1,
        'T':raw[6], 'dewpoint':raw[7], 'RH':raw[8], 'P':raw[9],
        'GHI':raw[13], 'DNI':raw[14], 'DHI':raw[15]})
    if not (frame.T.loc['T'].between(-30,55).all()
            and frame.RH.between(0,110).all()
            and frame.P.between(80000,110000).all()
            and frame[['GHI','DNI','DHI']].apply(lambda x:x.between(0,1500)).all().all()):
        raise ValueError('EPW missing/out-of-range values: refuse silent substitution')
    frame['doy'] = np.repeat(np.arange(1,366),24)
    # CSWD contains RH=101%; retain original field, explicitly cap only the
    # humidity conversion input at saturation. Never replace missing fields.
    frame['RH_used'] = frame.RH.clip(upper=100.)
    frame['w'] = [humidity_ratio(t,r,p) for t,r,p in zip(frame['T'],frame.RH_used,frame.P)]
    humidity_adjustments=frame[frame.RH>100.][['month','day','hour','T','RH','RH_used']]
    humidity_adjustments.to_csv(Path(data_dir)/(station+'_humidity_adjustments.csv'),index=False)
    meta = {'station':name,'url':url,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'latitude':float(header[6]),'longitude':float(header[7]),
            'timezone':float(header[8]),'hours':len(raw),
            'missing_policy':'fail on invalid required fields; no fill; RH 100–110 capped at 100 for humidity conversion only, audited separately',
            'humidity_capped_hours':len(humidity_adjustments),
            'interval':'EPW hour 1 = 00:00–01:00, solar position at midpoint'}
    (Path(data_dir)/(station+'_manifest.json')).write_text(json.dumps(meta,indent=2,ensure_ascii=False))
    return frame,meta


def forcing(frame, meta, azimuth=180., albedo=.2):
    # NOAA approximate solar position, isotropic sky diffuse assumption.
    hour = frame.hour.to_numpy()+.5
    g = 2*np.pi/365*(frame.doy.to_numpy()-1+(hour-12)/24)
    eq = 229.18*(.000075+.001868*np.cos(g)-.032077*np.sin(g)
                 -.014615*np.cos(2*g)-.040849*np.sin(2*g))
    dec = (.006918-.399912*np.cos(g)+.070257*np.sin(g)-.006758*np.cos(2*g)
           +.000907*np.sin(2*g)-.002697*np.cos(3*g)+.00148*np.sin(3*g))
    ha = np.deg2rad((hour*60+eq+4*meta['longitude']-60*meta['timezone'])/4-180)
    lat = np.deg2rad(meta['latitude'])
    up = np.sin(lat)*np.sin(dec)+np.cos(lat)*np.cos(dec)*np.cos(ha)
    east = -np.cos(dec)*np.sin(ha)
    north = np.cos(lat)*np.sin(dec)-np.sin(lat)*np.cos(dec)*np.cos(ha)
    az = np.deg2rad(azimuth)
    incidence = np.maximum(0,east*np.sin(az)+north*np.cos(az))*(up>0)
    vertical = frame.DNI.to_numpy()*incidence+.5*frame.DHI.to_numpy()+.5*albedo*frame.GHI.to_numpy()
    return np.column_stack([frame['T'],frame.w,frame.P,vertical,frame.GHI,vertical])


def forcing_for_parameters(frame,meta,p):
    values=forcing(frame,meta,p.azimuth,p.ground_albedo)
    if p.corner>.5:
        side=forcing(frame,meta,(p.azimuth+90.)%360.,p.ground_albedo)
        front=p.width*p.height-p.window_area-p.metal_area-p.frame_area
        side_area=p.length*p.height
        values[:,3]=(front*values[:,3]+side_area*side[:,3])/(front+side_area)
    return values
