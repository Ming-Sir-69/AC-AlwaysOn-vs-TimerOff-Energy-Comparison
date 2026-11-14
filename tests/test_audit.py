import numpy as np
from acstudy.model import Parameters,simulate
from acstudy.audit import reconstruct_budgets,electric_reconstruction


def test_independent_reconstruction_and_corruption_detection():
    weather=np.tile([32.,.019,101325.,250.,500.,250.],(24,1))
    p=Parameters()
    for kind in ['fixed','inverter']:
        a=simulate(weather,p,kind,'cut_all',warmup_hours=0)
        budget=reconstruct_budgets(weather,p,a,[26.,26.,26.,.012])
        electric=electric_reconstruction(weather,p,a,kind)
        assert abs(budget['thermal_difference_J'])<.001
        assert abs(budget['water_difference_kg'])<1e-10
        assert abs(electric['electric_difference_kWh'])<1e-9
        damaged=a.copy();damaged[:,8]+=100.
        assert abs(reconstruct_budgets(weather,p,damaged,[26,26,26,.012])['thermal_difference_J'])>1e6
        damaged=a.copy();damaged[:,7]+=100.
        assert abs(electric_reconstruction(weather,p,damaged,kind)['electric_difference_kWh'])>2.
