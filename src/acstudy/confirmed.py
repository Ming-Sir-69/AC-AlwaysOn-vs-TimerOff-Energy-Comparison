"""Building facts and matched west/east/roof/corner counterfactuals."""
from .analysis import BOUNDS, LABELS
from .model import room_parameters

CASES = [('west','二楼西向·单面外墙（基准）'),('east','朝东对照·非顶层单面外墙'),
         ('west_top','顶层对照·西向单面外墙'),('west_corner','转角对照·非顶层西向')]
WEST_BOUNDS = {k:((240.,300.) if k=='azimuth' else span)
               for k,span in BOUNDS.items() if k not in ['topfloor','corner']}
WEST_LABELS = [LABELS[list(BOUNDS).index(k)] for k in WEST_BOUNDS]


def case_parameters(unit, case='west', room='base'):
    """Use the original unit draws for all unresolved inputs; replace known facts."""
    d={k:lo+(hi-lo)*float(x) for x,(k,(lo,hi)) in zip(unit,BOUNDS.items())}
    bearing=float(unit[list(BOUNDS).index('azimuth')])
    d.update(topfloor=float(case=='west_top'),corner=float(case=='west_corner'),
             azimuth=(60. if case=='east' else 240.)+60.*bearing)
    if room=='tile80':d.update(width=4.3,length=6.2)
    elif room=='upper':d.update(width=4.8,length=6.2)
    return room_parameters(**d)


def west_parameters(unit):
    d={k:lo+(hi-lo)*float(x) for x,(k,(lo,hi)) in zip(unit,WEST_BOUNDS.items())}
    return room_parameters(topfloor=0.,corner=0.,**d)
