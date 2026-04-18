"""
仿真引擎模块

将正交表与热力学模型结合，批量运行实验并输出结果 DataFrame。
"""

import sys
import os
import pandas as pd
import numpy as np

# 确保同目录下的模块可以被导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from thermal_model import ThermalParams, energy_scheme_a, energy_scheme_b


def run_experiment(orthogonal_array, factor_levels, UA=0.5, COP_degradation=0.6):
    """
    批量运行正交实验

    参数:
        orthogonal_array: numpy array, shape=(n, 6), 值为 0-4 的索引
                          （对于临界区补充实验，值为实际参数值）
        factor_levels: dict, 格式为:
            {
                'A': {'levels': [v1, v2, ...]},
                'B': {'levels': [v1, v2, ...]},
                ...
            }
            对于正交表实验，levels 列表按索引映射；
            对于临界区补充实验（orthogonal_array 中已是实际值），
            levels 可以设为 None，此时直接使用 orthogonal_array 中的值。
        UA: 综合传热系数 (kW/°C)
        COP_degradation: COP 衰减系数

    返回:
        pandas DataFrame, 包含每次运行的参数和结果
    """
    factor_keys = ['A', 'B', 'C', 'D', 'E', 'F']
    results = []

    # 判断是否为"直接值"模式（临界区补充实验）
    direct_value_mode = all(
        factor_levels.get(k, {}).get('levels') is None for k in factor_keys
    )

    for i, row in enumerate(orthogonal_array):
        if direct_value_mode:
            # 临界区补充实验：orthogonal_array 中存储的是实际参数值
            levels = {k: float(row[j]) for j, k in enumerate(factor_keys)}
        else:
            # 正交表实验：通过索引映射到实际水平值
            levels = {
                k: factor_levels[k]['levels'][int(row[j])]
                for j, k in enumerate(factor_keys)
            }

        params = ThermalParams(
            T_out=levels['B'],
            T_in_init=levels['C'],
            T_set=levels['D'],
            tau_k=levels['E'],
            COP=levels['F'],
            UA=UA,
            COP_degradation=COP_degradation
        )

        E_A = energy_scheme_a(params)
        E_B = energy_scheme_b(params, t_off=levels['A'])
        delta_E = E_A - E_B
        savings_pct = (delta_E / E_A * 100) if E_A > 0 else 0

        results.append({
            'Run': i + 1,
            't_off': levels['A'],
            'T_out': levels['B'],
            'T_in_init': levels['C'],
            'T_set': levels['D'],
            'tau': levels['E'],
            'COP': levels['F'],
            'E_A': round(E_A, 4),
            'E_B': round(E_B, 4),
            'delta_E': round(delta_E, 4),
            'savings_pct': round(savings_pct, 2),
            'winner': 'B关机更省' if E_B < E_A else 'A常开更省'
        })

    return pd.DataFrame(results)


if __name__ == '__main__':
    from orthogonal_array import get_L25, get_L50, get_critical_zone_supplementary
    from config import FACTORS_L25, FACTORS_L50

    # 运行 L25 实验
    L25 = get_L25()
    df_L25 = run_experiment(L25, FACTORS_L25)
    print("=== L25 正交实验结果 ===")
    print(df_L25.to_string(index=False))
    print(f"\n方案B更省电的次数: {(df_L25['winner'] == 'B关机更省').sum()} / {len(df_L25)}")
    print(f"平均节能率: {df_L25['savings_pct'].mean():.2f}%")
