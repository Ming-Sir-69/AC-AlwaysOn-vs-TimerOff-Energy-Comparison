"""Guard against mixing unknown building facts into headline statistics."""
import pandas as pd
import pytest
from acstudy.presentation import baseline, paired_values


def test_baseline_keeps_only_requested_building_and_paired_samples():
    rows = []
    for sample, top, corner, extra in [(0,0,0,76),(1,1,0,116),(2,0,1,98),(3,1,1,150)]:
        for policy, energy in [('cut_all',1000),('manual',1000+extra)]:
            rows.append(dict(sample=sample,p_topfloor=top,p_corner=corner,
                             policy=policy,kind='fixed',energy_kWh=energy))
    original = pd.DataFrame(rows)
    selected = baseline(original)
    assert set(selected['sample']) == {0}
    assert paired_values(selected,'fixed','manual','energy_kWh').tolist() == [76]
    assert len(original) == 8


def test_pairing_uses_sample_identity_and_rejects_unmatched_samples():
    data = pd.DataFrame([
        dict(sample=2,kind='fixed',policy='manual',energy=209),
        dict(sample=1,kind='fixed',policy='manual',energy=103),
        dict(sample=1,kind='fixed',policy='cut_all',energy=100),
        dict(sample=2,kind='fixed',policy='cut_all',energy=200)])
    assert paired_values(data,'fixed','manual','energy').sort_index().tolist() == [3,9]
    with pytest.raises(AssertionError):
        paired_values(data.iloc[:-1],'fixed','manual','energy')
