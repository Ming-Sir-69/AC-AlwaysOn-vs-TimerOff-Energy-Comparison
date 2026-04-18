"""
热力学模型核心模块

基于牛顿冷却定律的简化房间热力学模型，用于计算空调两种运行方案的耗电量。
"""

import numpy as np


class ThermalParams:
    """
    热力学参数容器

    参数:
        T_out (float): 室外温度 (°C)
        T_in_init (float): 室内初始温度 (°C)
        T_set (float): 空调目标设定温度 (°C)
        tau_k (float): 建筑热惯性时间常数 (h)
        COP (float): 空调能效比 (额定)
        UA (float): 综合传热系数 (kW/°C)，默认 0.5
        COP_degradation (float): 急冷工况下 COP 衰减系数，默认 0.6
    """

    def __init__(self, T_out, T_in_init, T_set, tau_k, COP, UA=0.5, COP_degradation=0.6):
        self.T_out = T_out
        self.T_in_init = T_in_init
        self.T_set = T_set
        self.tau_k = tau_k
        self.COP = COP
        self.UA = UA
        self.COP_degradation = COP_degradation
        self.C_th = UA * tau_k  # 建筑等效热容 (kWh/°C)

    def __repr__(self):
        return (f"ThermalParams(T_out={self.T_out}°C, T_in_init={self.T_in_init}°C, "
                f"T_set={self.T_set}°C, tau={self.tau_k}h, COP={self.COP}, "
                f"UA={self.UA}, C_th={self.C_th:.2f})")


def room_temp_after_shutdown(params, t_off):
    """
    关机 t_off 小时后的室温（牛顿冷却定律）

    公式: T(t) = T_out - (T_out - T_in_init) * exp(-t / tau_k)

    参数:
        params (ThermalParams): 热力学参数
        t_off (float): 关机时长 (h)

    返回:
        float: 关机后的室温 (°C)
    """
    return params.T_out - (params.T_out - params.T_in_init) * np.exp(-t_off / params.tau_k)


def energy_scheme_a(params, hours=24):
    """
    方案 A：恒温常开 24h 耗电 (kWh)

    空调持续运行以维持设定温度，耗电 = 维持功率 x 时间。
    维持功率 P_idle = UA * (T_out - T_set) / COP

    参数:
        params (ThermalParams): 热力学参数
        hours (float): 总运行时长 (h)，默认 24

    返回:
        float: 耗电量 (kWh)
    """
    P_idle = params.UA * (params.T_out - params.T_set) / params.COP
    return P_idle * hours


def energy_scheme_b(params, t_off, hours=24):
    """
    方案 B：出门关机 t_off 小时后回家重启耗电 (kWh)

    分为三个阶段:
    1. 关机期间 (t_off 小时): 室温按牛顿冷却回升，空调不耗电
    2. 急冷阶段: 回家后空调全力运行，将室温从 T_return 降至 T_set
       - 急冷耗电 E_cool = C_th * delta_T / COP_eff
       - COP_eff = COP * COP_degradation (急冷工况效率下降)
    3. 维持阶段: 达到设定温度后，以维持功率运行剩余时间

    参数:
        params (ThermalParams): 热力学参数
        t_off (float): 出门关机时长 (h)
        hours (float): 总时长 (h)，默认 24

    返回:
        float: 耗电量 (kWh)
    """
    # 阶段1: 关机后室温回升
    T_return = room_temp_after_shutdown(params, t_off)
    delta_T = max(0, T_return - params.T_set)

    # 阶段2: 急冷耗电（COP 衰减）
    COP_eff = params.COP * params.COP_degradation
    E_cool = params.C_th * delta_T / COP_eff

    # 急冷时间估算
    P_max = params.UA * (params.T_out - params.T_set) / COP_eff
    t_cool = E_cool / P_max if P_max > 0 else 0

    # 阶段3: 维持运行耗电
    t_maint = max(0, hours - t_off - t_cool)
    P_idle = params.UA * (params.T_out - params.T_set) / params.COP
    E_maint = P_idle * t_maint

    return E_cool + E_maint


if __name__ == '__main__':
    # 测试用例
    params = ThermalParams(
        T_out=35, T_in_init=28, T_set=24,
        tau_k=6, COP=3.5, UA=0.5, COP_degradation=0.6
    )
    print(params)

    for t_off in [2, 4, 6, 8, 10]:
        T_ret = room_temp_after_shutdown(params, t_off)
        E_A = energy_scheme_a(params)
        E_B = energy_scheme_b(params, t_off)
        delta = E_A - E_B
        print(f"t_off={t_off}h: T_return={T_ret:.2f}°C, "
              f"E_A={E_A:.4f}kWh, E_B={E_B:.4f}kWh, "
              f"delta={delta:.4f}kWh ({'B省' if delta > 0 else 'A省'})")
