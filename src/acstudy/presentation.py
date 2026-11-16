"""Explicit reporting strata; do not mix unknown building facts into a headline."""
STRATA = [(0,0,'非顶层、单面外墙（基准假设）'),(1,0,'顶层、单面外墙'),(0,1,'非顶层、转角两面外墙'),(1,1,'顶层、转角两面外墙')]
PUBLIC_POLICIES = ['always','cut_all','cut_workday','setback30','manual','auto_restore','early60','precool_restday']

def baseline(mc):
    if 'building_case' in mc.columns:
        return mc[mc.building_case=='west'].copy()
    return mc[(mc.p_topfloor==0)&(mc.p_corner==0)].copy()

def paired_values(mc,kind,policy,column,reference='cut_all'):
    a=mc[(mc.kind==kind)&(mc.policy==policy)].set_index('sample')[column]
    b=mc[(mc.kind==kind)&(mc.policy==reference)].set_index('sample')[column]
    assert a.index.is_unique and b.index.is_unique and set(a.index)==set(b.index)
    return a-b
