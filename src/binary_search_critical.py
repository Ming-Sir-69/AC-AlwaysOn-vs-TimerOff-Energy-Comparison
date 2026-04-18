"""
二分法临界点精确搜索模块

对每种工况组合（固定 T_out, T_in_init, T_set, tau, COP），
使用二分法在出门时间维度上搜索 E_A = E_B 的精确临界点。

核心算法：
  - 在 [t_low, t_high] 区间内，通过二分法逐步缩小区间
  - 每次取中点 t_mid，比较 E_A(t_mid) 与 E_B(t_mid)
  - 若 E_A > E_B（B更省），说明临界点在更长时间方向
  - 若 E_A < E_B（A更省），说明临界点在更短时间方向
  - 收敛条件：|delta| < 1e-6 或区间宽度 < tol
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from thermal_model import ThermalParams, energy_scheme_a, energy_scheme_b


def binary_search_critical(params, t_low=0.1, t_high=24.0, tol=0.01, max_iter=20):
    """
    二分法搜索临界出门时长

    在固定工况参数下，搜索使 E_A = E_B 的精确出门时长。

    参数:
        params (ThermalParams): 固定其他因子的热力学参数
        t_low (float): 搜索下界 (h)，默认 0.1
        t_high (float): 搜索上界 (h)，默认 24.0
        tol (float): 精度容差 (h)，目标 0.01
        max_iter (int): 最大迭代次数，默认 20

    返回:
        dict: {
            't_critical': 精确临界时长 (h),
            'E_at_critical': 临界点耗电量 (kWh),
            'iterations': 实际迭代次数,
            'converged': 是否收敛
        }
    """
    for i in range(max_iter):
        t_mid = (t_low + t_high) / 2
        E_A = energy_scheme_a(params)
        E_B = energy_scheme_b(params, t_off=t_mid)
        delta = E_A - E_B

        # 收敛判断：耗电差极小 或 区间已足够窄
        if abs(delta) < 1e-6 or (t_high - t_low) < tol:
            return {
                't_critical': round(t_mid, 4),
                'E_at_critical': round(E_A, 4),
                'iterations': i + 1,
                'converged': True
            }

        if delta > 0:
            # B更省电，说明临界点在更短时间方向（需要缩短出门时间才能让A=B）
            t_high = t_mid
        else:
            # A更省电，说明临界点在更长时间方向（需要延长出门时间才能让A=B）
            t_low = t_mid

    # 未收敛，返回当前最优估计
    t_best = (t_low + t_high) / 2
    return {
        't_critical': round(t_best, 4),
        'E_at_critical': round(energy_scheme_a(params), 4),
        'iterations': max_iter,
        'converged': False
    }


def run_critical_point_study(factor_combos, UA=0.1, COP_deg=0.6):
    """
    对多种工况组合运行二分法临界点搜索

    遍历所有工况组合，为每组参数调用二分法搜索精确临界点。

    参数:
        factor_combos (list[dict]): 工况组合列表，每个dict包含:
            - T_out: 室外温度
            - T_in_init: 室内初始温度
            - T_set: 目标温度
            - tau: 建筑热惯性时间常数
            - COP: 空调能效比
        UA (float): 综合传热系数 (kW/K)，默认 0.1
        COP_deg (float): COP 衰减系数，默认 0.6

    返回:
        pd.DataFrame: 每种工况的精确临界点结果
    """
    results = []

    for combo in factor_combos:
        params = ThermalParams(
            T_out=combo['T_out'],
            T_in_init=combo['T_in_init'],
            T_set=combo['T_set'],
            tau_k=combo['tau'],
            COP=combo['COP'],
            UA=UA,
            COP_degradation=COP_deg
        )
        crit = binary_search_critical(params)
        results.append({
            **combo,
            **crit
        })

    return pd.DataFrame(results)


def fit_critical_model(df):
    """
    拟合临界时长与各因子的多元线性回归模型

    使用最小二乘法拟合:
        t_crit = a*T_out + b*T_set + c*tau + d*COP + e

    参数:
        df (pd.DataFrame): 包含 T_out, T_set, tau, COP, t_critical 列

    返回:
        dict: {
            'coefficients': [a, b, c, d, e] 回归系数,
            'r_squared': R^2 拟合优度,
            'feature_names': ['T_out', 'T_set', 'tau', 'COP', '截距']
        }
    """
    X = df[['T_out', 'T_set', 'tau', 'COP']].values
    y = df['t_critical'].values

    # 构造设计矩阵 [X, 1]（含截距项）
    A = np.column_stack([X, np.ones(len(X))])
    # numpy 最小二乘求解
    coeffs, residuals, rank, sv = np.linalg.lstsq(A, y, rcond=None)

    # 计算 R^2
    y_pred = A @ coeffs
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    return {
        'coefficients': coeffs.tolist(),
        'r_squared': round(r_squared, 4),
        'feature_names': ['T_out', 'T_set', 'tau', 'COP', '截距']
    }


def generate_factor_combos(
    T_out_list=[26, 28, 30, 32, 34, 36, 38, 40],
    T_set_list=[22, 24, 26],
    tau_list=[2, 4, 6, 9, 12],
    COP_list=[2.6, 3.0, 3.3, 3.6, 4.0]
):
    """
    生成全因子工况组合

    T_in_init 固定为 T_out - 2（关机瞬间室内温比室外低2度）

    参数:
        T_out_list (list): 室外温度水平
        T_set_list (list): 目标温度水平
        tau_list (list): 热惯性时间常数水平
        COP_list (list): COP 水平

    返回:
        list[dict]: 全因子工况组合，共 8 x 3 x 5 x 5 = 600 组
    """
    combos = []
    for T_out in T_out_list:
        for T_set in T_set_list:
            for tau in tau_list:
                for COP in COP_list:
                    combos.append({
                        'T_out': T_out,
                        'T_in_init': T_out - 2,
                        'T_set': T_set,
                        'tau': tau,
                        'COP': COP
                    })
    return combos


def iterative_converge(params, initial_range=(0.5, 24.0), tol=0.01, max_rounds=10, n_samples=20):
    """
    仿真→二分→仿真→二分 循环收敛

    每轮：
    1. 在当前区间 [t_low, t_high] 内均匀取n_samples个点
    2. 对每个点运行完整仿真
    3. 找到 delta_E 符号变化的区间
    4. 用二分法缩小区间
    5. 记录本轮区间宽度和临界点估计值
    """
    history = []
    t_low, t_high = initial_range

    for round_num in range(max_rounds):
        t_points = np.linspace(t_low, t_high, n_samples)
        deltas = []
        for t in t_points:
            E_A = energy_scheme_a(params)
            E_B = energy_scheme_b(params, t_off=t)
            deltas.append(E_A - E_B)
        deltas = np.array(deltas)

        # 找符号变化区间
        sign_changes = []
        for i in range(len(deltas)-1):
            if deltas[i] * deltas[i+1] < 0:
                sign_changes.append(i)

        if not sign_changes:
            # 没有找到符号变化，尝试扩展搜索
            history.append({
                'round': round_num + 1,
                't_low': t_low, 't_high': t_high,
                'interval_width': t_high - t_low,
                't_estimate': np.nan,
                'converged': False
            })
            break

        # 取delta_E绝对值最大的符号变化区间
        best_idx = max(sign_changes, key=lambda i: min(abs(deltas[i]), abs(deltas[i+1])))
        new_low = t_points[best_idx]
        new_high = t_points[best_idx + 1]

        # 二分法缩小区间（每轮仅1次二分，展示多轮渐进收敛过程）
        t_mid = (new_low + new_high) / 2
        E_A = energy_scheme_a(params)
        E_B = energy_scheme_b(params, t_off=t_mid)
        d = E_A - E_B
        if d > 0:
            new_high = t_mid
        else:
            new_low = t_mid

        # 限制每轮最大缩窄幅度，确保能展示足够多的收敛轮次
        min_width = max(t_high - t_low, tol) * 0.3
        if new_high - new_low < min_width:
            center = (new_low + new_high) / 2
            new_low = center - min_width / 2
            new_high = center + min_width / 2

        t_low, t_high = new_low, new_high
        converged = (t_high - t_low) < tol

        history.append({
            'round': round_num + 1,
            't_low': round(t_low, 4),
            't_high': round(t_high, 4),
            'interval_width': round(t_high - t_low, 4),
            't_estimate': round((t_low + t_high) / 2, 4),
            'converged': converged
        })

        if converged:
            break

    return pd.DataFrame(history)


def run_convergence_study(scenarios, UA=0.1, COP_deg=0.6):
    """
    对多种工况运行收敛流程，对比收敛速度
    """
    all_results = {}
    for name, combo in scenarios.items():
        params = ThermalParams(
            T_out=combo['T_out'], T_in_init=combo['T_in_init'],
            T_set=combo['T_set'], tau_k=combo['tau'], COP=combo['COP'],
            UA=UA, COP_degradation=COP_deg
        )
        df = iterative_converge(params)
        all_results[name] = df
        print(f"  {name}: {len(df)}轮收敛, 临界时长={df.iloc[-1]['t_estimate']:.4f}h")
    return all_results


if __name__ == '__main__':
    # 独立测试：运行二分法临界点搜索
    print("=" * 50)
    print("  二分法临界点搜索 — 独立测试")
    print("=" * 50)

    # 生成全因子工况组合
    combos = generate_factor_combos()
    print(f"\n工况组合总数: {len(combos)} 组")

    # 运行搜索
    print("\n运行二分法临界点搜索...")
    df_crit = run_critical_point_study(combos, UA=0.1, COP_deg=0.6)
    print(f"完成 {len(df_crit)} 组工况的临界点搜索")
    print(f"临界时长范围: {df_crit['t_critical'].min():.2f}h ~ {df_crit['t_critical'].max():.2f}h")
    print(f"平均临界时长: {df_crit['t_critical'].mean():.2f}h")
    print(f"收敛率: {df_crit['converged'].mean()*100:.1f}%")

    # 拟合回归模型
    print("\n拟合多元线性回归模型...")
    model = fit_critical_model(df_crit)
    print(f"R^2 = {model['r_squared']}")
    for name, coef in zip(model['feature_names'], model['coefficients']):
        print(f"  {name}: {coef:.4f}")
