"""Summarize and audit matched west-facing results, including prior scope comparison."""

def summarize():
    from pathlib import Path
    import json,sys,hashlib
    import pandas as pd
    import numpy as np
    ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'))
    from acstudy.presentation import baseline,paired_values
    from acstudy.confirmed import CASES
    mc=pd.read_csv(ROOT/'results/building_confirmed.csv.gz')
    west=baseline(mc);west=west[west.room=='base']
    rows=[]
    def add(part,label):
     for kind in ['fixed','inverter']:
      cur=part[(part.kind==kind)&(part.policy=='cut_all')]
      extra=paired_values(part,kind,'manual','energy_kWh')
      work=paired_values(part,kind,'manual','workday_kWh')
      rest=paired_values(part,kind,'manual','restday_kWh')
      assert np.abs(extra-132*work-52*rest).max()<1e-8
      row=dict(case=label,kind=kind,n=len(cur))
      fields={'saving_pct':cur.saving_pct,'manual_extra_kWh':extra,'extra_workday_kWh':work,'extra_restday_kWh':rest,'rest_peak_C':cur.rest_peak_C,
       'current_energy_kWh':cur.energy_kWh,'manual_energy_kWh':part[(part.kind==kind)&(part.policy=='manual')].energy_kWh,
       'heat_reduced_degree_hours':-paired_values(part,kind,'manual','occupied_degree_hours')}
      for metric,vals in fields.items():
       for suffix,val in zip(['p05','p50','p95'],np.quantile(vals,[.05,.5,.95])):row[metric+'_'+suffix]=float(val)
      rows.append(row)
    for case,label in CASES:add(mc[(mc.room=='base')&(mc.building_case==case)],case)
    pd.DataFrame(rows).to_csv(ROOT/'results/confirmed_summary.csv',index=False)
    # Paired construction and azimuth controls really share the same unresolved inputs.
    westc=west[(west.kind=='fixed')&(west.policy=='cut_all')].set_index('sample').sort_index()
    for case,_ in CASES[1:]:
     sub=mc[(mc.room=='base')&(mc.building_case==case)&(mc.kind=='fixed')&(mc.policy=='cut_all')].set_index('sample').sort_index()
     assert sub.index.equals(westc.index)
     for key in westc.columns:
      if key.startswith('p_') and key not in ['p_azimuth','p_topfloor','p_corner']:
       assert np.allclose(sub[key],westc[key],rtol=0,atol=1e-8),(case,key)
     if case=='east':assert np.allclose(sub.p_azimuth,westc.p_azimuth-180,rtol=0,atol=1e-10)
    assert mc[mc.building_case=='west'].p_azimuth.between(240,300).all()
    assert westc.p_topfloor.eq(0).all() and westc.p_corner.eq(0).all()
    n=len(westc)
    assert westc.groupby('station').size().to_dict()=={'guangzhou':n//2,'shenzhen':n//2}
    assert len(mc)==60*n and mc.energy_kWh.gt(0).all()
    summary={'cases':rows,'seasonal_trajectories':len(mc),'west_trajectories':int((mc.building_case=='west').sum()),'paired_controls_checked':True,'workday_restday_energy_identity_checked':True,'max_enthalpy_residual_W':float(mc.enthalpy_residual_max_W.max()),'building_facts':'floor2; single exterior balcony facade; west confirmed; non-topfloor assumed because total floors unknown','fields':'p05,p50,p95 are scenario quantiles, not confidence intervals'}
    (ROOT/'results/confirmed_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(pd.DataFrame(rows)[['case','kind','n','saving_pct_p50','manual_extra_kWh_p05','manual_extra_kWh_p50','manual_extra_kWh_p95','rest_peak_C_p50','extra_restday_kWh_p50']].to_string(index=False),flush=True)

if __name__=='__main__':summarize()
