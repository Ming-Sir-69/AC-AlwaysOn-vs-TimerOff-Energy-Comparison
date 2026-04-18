"""
田口分析模块

提供主效应分析、方差分析（ANOVA）和临界阈值搜索功能。
"""

import pandas as pd
import numpy as np


def compute_main_effects(df, factor_cols, response_col='delta_E'):
    """
    计算各因子各水平的主效应均值

    参数:
        df (pd.DataFrame): 实验结果数据
        factor_cols (list): 因子列名列表
        response_col (str): 响应变量列名，默认 'delta_E'

    返回:
        dict: {因子名: Series(水平值 -> 均值)}
    """
    results = {}
    for col in factor_cols:
        effects = df.groupby(col)[response_col].mean()
        results[col] = effects
    return results


def compute_anova(df, factor_cols, response_col='delta_E'):
    """
    单因素方差分析（田口方法）

    计算各因子的平方和、自由度、均方和贡献率。

    参数:
        df (pd.DataFrame): 实验结果数据
        factor_cols (list): 因子列名列表
        response_col (str): 响应变量列名，默认 'delta_E'

    返回:
        pd.DataFrame: ANOVA 表，包含 Factor, SS, df, MS, Contribution(%)
    """
    n_total = len(df)
    grand_mean = df[response_col].mean()
    SS_total = np.sum((df[response_col] - grand_mean) ** 2)

    anova_results = []
    for col in factor_cols:
        levels = df[col].unique()
        SS = sum(
            len(df[df[col] == lv]) *
            (df[df[col] == lv][response_col].mean() - grand_mean) ** 2
            for lv in levels
        )
        df_val = len(levels) - 1
        MS = SS / df_val if df_val > 0 else 0
        contribution = SS / SS_total * 100 if SS_total > 0 else 0
        anova_results.append({
            'Factor': col,
            'SS': round(SS, 4),
            'df': df_val,
            'MS': round(MS, 4),
            'Contribution(%)': round(contribution, 2)
        })

    SS_error = SS_total - sum(r['SS'] for r in anova_results)
    df_error = n_total - 1 - sum(r['df'] for r in anova_results)
    MS_error = SS_error / df_error if df_error > 0 else 0
    anova_results.append({
        'Factor': 'Error',
        'SS': round(SS_error, 4),
        'df': df_error,
        'MS': round(MS_error, 4),
        'Contribution(%)': round(SS_error / SS_total * 100, 2) if SS_total > 0 else 0
    })

    return pd.DataFrame(anova_results)


def find_critical_threshold(df, t_off_col='t_off', delta_col='delta_E'):
    """
    通过线性插值寻找 delta_E = 0 的临界出门时长

    当 delta_E > 0 时，方案 B（关机）更省电；
    当 delta_E < 0 时，方案 A（常开）更省电。
    临界点即两种方案耗电相等的出门时长。

    参数:
        df (pd.DataFrame): 实验结果数据
        t_off_col (str): 出门时长列名，默认 't_off'
        delta_col (str): 耗电差值列名，默认 'delta_E'

    返回:
        float or None: 临界出门时长 (h)，若无零点则返回 None
    """
    df_sorted = df.sort_values(t_off_col).reset_index(drop=True)

    for i in range(len(df_sorted) - 1):
        d1 = df_sorted.loc[i, delta_col]
        d2 = df_sorted.loc[i + 1, delta_col]
        t1 = df_sorted.loc[i, t_off_col]
        t2 = df_sorted.loc[i + 1, t_off_col]

        if d1 * d2 < 0:  # 符号变化，存在零点
            # 线性插值
            t_crit = t1 - d1 * (t2 - t1) / (d2 - d1)
            return t_crit

    return None


if __name__ == '__main__':
    # 构造测试数据
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from orthogonal_array import get_L25
    from energy_simulator import run_experiment
    from config import FACTORS_L25

    factor_levels = FACTORS_L25

    L25 = get_L25()
    df = run_experiment(L25, factor_levels)

    # 主效应分析
    factor_cols = ['t_off', 'T_out', 'T_in_init', 'T_set', 'tau', 'COP']
    main_effects = compute_main_effects(df, factor_cols)
    print("=== 主效应分析 ===")
    for col, effects in main_effects.items():
        print(f"\n{col}:")
        for lv, val in effects.items():
            print(f"  水平 {lv}: delta_E = {val:.4f}")

    # 方差分析
    anova_table = compute_anova(df, factor_cols)
    print("\n=== 方差分析 (ANOVA) ===")
    print(anova_table.to_string(index=False))

    # 临界阈值搜索
    t_crit = find_critical_threshold(df)
    print(f"\n=== 临界出门时长 ===")
    print(f"临界 t_off = {t_crit:.2f} h" if t_crit else "未找到临界点")
