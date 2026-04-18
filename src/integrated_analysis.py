"""
综合分析模块 -- 空调常开 vs 定时关节能研究

功能:
1. 多元回归加权影响力分析（基于临界外出时长数据） -> 1张独立图
2. 单因子敏感性分析（每因子独立一张图，共5张）
3. 临界工况散点矩阵（T_out vs tau） -> 1张独立图
4. 相关性判定汇总表（打印到控制台 + 返回 DataFrame）

所有图表独立输出，不合并子图。
"""

import sys
import os
import numpy as np
import pandas as pd
from scipy import stats

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 确保同目录下的模块可以被导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from thermal_model import ThermalParams, energy_scheme_a, energy_scheme_b
from plot_utils import setup_chinese_font, save_fig, COLORS

# 确保中文字体就绪
setup_chinese_font()

# 配色常量
COLOR_A = '#2196F3'       # 方案A 蓝色
COLOR_B = '#F44336'       # 方案B 红色
COLOR_CRITICAL = '#4CAF50' # 临界点 绿色


# ============================================================
# 1. 多元回归加权影响力分析
# ============================================================

def compute_weighted_influence(df_critical):
    """
    对600组二分法数据的临界外出时长做多元线性回归
    因子：T_out, T_set, tau（COP已验证无影响，排除）
    返回 DataFrame：因子名, 原始系数, 标准化系数(Beta), 权重(%), 相关性方向
    """
    features = ['T_out', 'T_set', 'tau']
    X = df_critical[features].values
    y = df_critical['t_critical'].values

    # 添加截距项
    X_with_intercept = np.column_stack([np.ones(len(X)), X])

    # 最小二乘法多元线性回归
    coeffs, _, _, _ = np.linalg.lstsq(X_with_intercept, y, rcond=None)
    raw_coeffs = coeffs[1:]

    # 标准化系数 (Beta) = coeff_i * (std(X_i) / std(y))
    X_std = np.std(X, axis=0, ddof=1)
    y_std = np.std(y, ddof=1)
    beta_coeffs = raw_coeffs * (X_std / y_std)

    # 权重百分比
    abs_betas = np.abs(beta_coeffs)
    total_abs = abs_betas.sum()
    weights_pct = abs_betas / total_abs * 100

    # 相关性方向
    directions = []
    for bc in beta_coeffs:
        if bc > 0.01:
            directions.append('正向影响')
        elif bc < -0.01:
            directions.append('负向影响')
        else:
            directions.append('几乎无影响')

    factor_labels = {
        'T_out': '室外温度',
        'T_set': '设定温度',
        'tau': '热时间常数'
    }

    result = pd.DataFrame({
        '因子名': [factor_labels[f] for f in features],
        '因子代码': features,
        '原始系数': np.round(raw_coeffs, 6),
        '标准化系数(Beta)': np.round(beta_coeffs, 4),
        '权重(%)': np.round(weights_pct, 2),
        '相关性方向': directions
    })

    # 回归统计量
    y_pred = X_with_intercept @ coeffs
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    n = len(y)
    p = len(features)
    adj_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - p - 1) if n > p + 1 else 0

    print(f"多元回归统计量:")
    print(f"  R^2 = {r_squared:.4f}")
    print(f"  调整R^2 = {adj_r_squared:.4f}")
    print(f"  样本量 = {n}")
    print(f"  因子数 = {p}")
    print()
    print(result.to_string(index=False))

    return result, r_squared, adj_r_squared


def plot_weighted_influence(influence_df, r_squared, adj_r_squared, chart_dir):
    """
    图表：综合影响力加权分析（水平柱状图）
    每个因子一个柱子，标注权重百分比和排名
    """
    fig, ax = plt.subplots(figsize=(12, 7.5), facecolor='white')

    factors = influence_df['因子名'].tolist()
    weights = influence_df['权重(%)'].tolist()
    betas = influence_df['标准化系数(Beta)'].tolist()
    directions = influence_df['相关性方向'].tolist()

    # 按权重降序排列
    sorted_idx = np.argsort(weights)[::-1]
    sorted_factors = [factors[i] for i in sorted_idx]
    sorted_weights = [weights[i] for i in sorted_idx]
    sorted_betas = [betas[i] for i in sorted_idx]
    sorted_directions = [directions[i] for i in sorted_idx]

    n = len(sorted_factors)

    # 颜色：正向=蓝色，负向=橙色
    bar_colors = ['#1976D2' if d == '正向影响' else '#F57C00' if d == '负向影响' else '#78909C'
                  for d in sorted_directions]

    bars = ax.barh(range(n), sorted_weights, height=0.5, color=bar_colors,
                   edgecolor='white', linewidth=0.8, alpha=0.9)

    # 标注：排名 + 权重百分比 + Beta值 + 方向
    for i, (w, b, d) in enumerate(zip(sorted_weights, sorted_betas, sorted_directions)):
        rank = i + 1
        ax.text(w + 0.8, i,
                f'#{rank}  {w:.1f}%  (Beta={b:.3f}, {d})',
                va='center', ha='left', fontsize=11, fontweight='bold',
                color='#212121')

    ax.set_yticks(range(n))
    ax.set_yticklabels(sorted_factors, fontsize=13, fontweight='bold')
    ax.set_xlabel('权重占比 (%)', fontsize=13)
    ax.set_xlim(0, max(sorted_weights) * 1.8)
    ax.invert_yaxis()  # 排名第1在上方

    # 美化
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    # 标题
    ax.set_title('综合影响力加权分析\n（多元线性回归标准化Beta系数）',
                 fontsize=16, fontweight='bold', pad=15)

    # 底部统计信息
    stats_text = f'R^2 = {r_squared:.4f}  |  调整R^2 = {adj_r_squared:.4f}  |  样本量 = 600'
    fig.text(0.5, 0.01, stats_text, ha='center', fontsize=11, color='#616161', style='italic')

    plt.tight_layout(rect=[0, 0.04, 1, 1])

    filepath = save_fig(fig, '综合影响力加权分析_1200x750.png', chart_dir, dpi=150)
    return filepath


# ============================================================
# 2. 单因子敏感性分析
# ============================================================

def single_factor_sensitivity():
    """
    固定基准参数，逐一扫描5个因子。
    每个因子计算 E_A, E_B, 节能比例 eta，以及 Pearson r。

    返回:
        dict: 各因子的扫描结果（含 E_A, E_B 曲线数据）
        DataFrame: 汇总表
    """
    # 基准参数
    base = {
        'T_out': 32,
        'T_in_init': 30,
        'T_set': 24,
        'tau': 6,
        'COP': 3.3,
        'UA': 0.1,
        'COP_deg': 0.6,
        't_off': 8  # 固定外出时长
    }

    # 各因子扫描范围（50个采样点）
    scan_ranges = {
        't_off': {'label': '外出时长', 'unit': 'h',
                  'values': np.linspace(0.5, 16, 50)},
        'T_out': {'label': '室外温度', 'unit': '°C',
                  'values': np.linspace(24, 42, 50)},
        'T_set': {'label': '设定温度', 'unit': '°C',
                  'values': np.linspace(20, 28, 50)},
        'tau':   {'label': '热时间常数', 'unit': 'h',
                  'values': np.linspace(1, 14, 50)},
        'COP':   {'label': '能效比', 'unit': '',
                  'values': np.linspace(2.0, 5.0, 50)},
    }

    results = {}

    for factor, info in scan_ranges.items():
        E_A_list = []
        E_B_list = []
        savings_list = []

        for val in info['values']:
            params = ThermalParams(
                T_out=val if factor == 'T_out' else base['T_out'],
                T_in_init=base['T_in_init'],
                T_set=val if factor == 'T_set' else base['T_set'],
                tau_k=val if factor == 'tau' else base['tau'],
                COP=val if factor == 'COP' else base['COP'],
                UA=base['UA'],
                COP_degradation=base['COP_deg']
            )
            t_off_val = val if factor == 't_off' else base['t_off']

            E_A = energy_scheme_a(params)
            E_B = energy_scheme_b(params, t_off=t_off_val)
            delta_E = E_A - E_B
            savings_pct = (delta_E / E_A * 100) if E_A > 0 else 0

            E_A_list.append(E_A)
            E_B_list.append(E_B)
            savings_list.append(savings_pct)

        savings_arr = np.array(savings_list)
        E_A_arr = np.array(E_A_list)
        E_B_arr = np.array(E_B_list)
        x_arr = info['values']

        # Pearson 相关系数
        r, p_value = stats.pearsonr(x_arr, savings_arr)

        # 判断单调性
        diffs = np.diff(savings_arr)
        positive_ratio = np.sum(diffs > 0) / len(diffs)
        negative_ratio = np.sum(diffs < 0) / len(diffs)

        # 判断相关性类型（按铭哥给的标准）
        abs_r = abs(r)
        if abs_r > 0.7:
            if r > 0:
                corr_type = '强正相关'
            else:
                corr_type = '强负相关'
        elif abs_r > 0.3:
            if r > 0:
                corr_type = '正相关'
            else:
                corr_type = '负相关'
        elif abs_r > 0.1:
            if r > 0:
                corr_type = '弱正相关'
            else:
                corr_type = '弱负相关'
        else:
            # 检查是否为复合相关（有拐点）
            sign_changes = np.sum(np.diff(np.sign(diffs)) != 0)
            if sign_changes >= 2:
                corr_type = '复合相关'
            else:
                corr_type = '无关'

        # 查找 E_A 和 E_B 的交点（即节能比例 = 0 的点）
        crossings = []
        for i in range(len(savings_arr) - 1):
            if savings_arr[i] * savings_arr[i + 1] < 0:
                # 线性插值求交点
                x_cross = x_arr[i] - savings_arr[i] * (x_arr[i + 1] - x_arr[i]) / (savings_arr[i + 1] - savings_arr[i])
                crossings.append(x_cross)

        # 生成说明文字
        if abs_r > 0.7:
            if r > 0:
                desc = f'因子增大显著提升关机节能比例'
            else:
                desc = f'因子增大显著降低关机节能比例'
        elif abs_r > 0.3:
            if r > 0:
                desc = f'因子增大有利于关机省电'
            else:
                desc = f'因子增大不利于关机省电'
        elif abs_r > 0.1:
            desc = f'因子对节能比例影响较弱'
        elif corr_type == '复合相关':
            desc = f'因子与节能比例呈非线性关系，存在拐点'
        else:
            desc = f'因子对节能比例几乎无影响'

        if crossings:
            desc += f'；临界交叉点约在{", ".join([f"{c:.2f}" for c in crossings])}{info["unit"]}'

        results[factor] = {
            'label': info['label'],
            'unit': info['unit'],
            'x_values': x_arr,
            'E_A': E_A_arr,
            'E_B': E_B_arr,
            'savings_pct': savings_arr,
            'pearson_r': r,
            'p_value': p_value,
            'corr_type': corr_type,
            'crossings': crossings,
            'desc': desc,
            'range_str': f"{info['values'][0]:.1f}~{info['values'][-1]:.1f}{info['unit']}"
        }

        print(f"因子: {info['label']} ({factor})")
        print(f"  范围: {info['values'][0]:.1f}~{info['values'][-1]:.1f}{info['unit']}")
        print(f"  Pearson r = {r:.4f} (p = {p_value:.2e})")
        print(f"  相关性类型: {corr_type}")
        if crossings:
            print(f"  交叉点: {crossings}")
        print()

    # 汇总表
    summary_rows = []
    for factor, res in results.items():
        summary_rows.append({
            '因子': res['label'],
            'Pearson r': round(res['pearson_r'], 4),
            '相关性类型': res['corr_type'],
            '说明': res['desc']
        })

    summary_df = pd.DataFrame(summary_rows)
    print("=" * 70)
    print("相关性判定汇总表:")
    print("=" * 70)
    print(summary_df.to_string(index=False))
    print("=" * 70)

    return results, summary_df


def plot_single_factor_sensitivity(factor, res, chart_dir):
    """
    单因子敏感性分析独立图
    X轴：因子值，Y轴：节能比例 eta(%)
    同时绘制 E_A 和 E_B 两条曲线（右侧Y轴）
    标注交点、Pearson r 和相关性类型
    """
    fig, ax1 = plt.subplots(figsize=(12, 7.5), facecolor='white')

    x = res['x_values']
    savings = res['savings_pct']
    E_A = res['E_A']
    E_B = res['E_B']

    # ── 左Y轴：节能比例 eta(%) ──
    ax1.plot(x, savings, linewidth=2.5, color='#FF9800', label='节能比例 eta (%)', zorder=4)
    ax1.fill_between(x, savings, 0, where=(savings > 0), alpha=0.15, color=COLOR_CRITICAL, interpolate=True)
    ax1.fill_between(x, savings, 0, where=(savings < 0), alpha=0.15, color='#F44336', interpolate=True)
    ax1.axhline(y=0, color='#9E9E9E', linestyle='--', linewidth=1.2, alpha=0.7, zorder=2)

    ax1.set_xlabel(f'{res["label"]} ({res["unit"]})' if res['unit'] else res['label'], fontsize=13)
    ax1.set_ylabel('节能比例 eta (%)', fontsize=13, color='#FF9800')
    ax1.tick_params(axis='y', labelcolor='#FF9800')

    # ── 右Y轴：能耗 E_A, E_B (kWh) ──
    ax2 = ax1.twinx()
    ax2.plot(x, E_A, linewidth=2, color=COLOR_A, linestyle='-', label='方案A能耗 E_A (kWh)', alpha=0.85, zorder=3)
    ax2.plot(x, E_B, linewidth=2, color=COLOR_B, linestyle='-', label='方案B能耗 E_B (kWh)', alpha=0.85, zorder=3)
    ax2.set_ylabel('能耗 (kWh)', fontsize=13, color='#616161')
    ax2.tick_params(axis='y', labelcolor='#616161')

    # ── 标注交叉点 ──
    for xc in res['crossings']:
        ax1.axvline(x=xc, color=COLOR_CRITICAL, linestyle=':', linewidth=1.5, alpha=0.8, zorder=2)
        ax1.plot(xc, 0, 'o', color=COLOR_CRITICAL, markersize=10, zorder=5,
                 markeredgecolor='white', markeredgewidth=1.5)
        ax1.annotate(f'临界点\n{xc:.2f}{res["unit"]}',
                     xy=(xc, 0), xytext=(xc, max(savings) * 0.15 if max(savings) > 0 else min(savings) * 0.15),
                     fontsize=10, fontweight='bold', color=COLOR_CRITICAL,
                     ha='center',
                     arrowprops=dict(arrowstyle='->', color=COLOR_CRITICAL, lw=1.5),
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=COLOR_CRITICAL, alpha=0.9))

    # ── 标注 Pearson r 和相关性类型 ──
    r_text = f'Pearson r = {res["pearson_r"]:.4f}'
    corr_text = res['corr_type']
    info_box = f'{r_text}\n{corr_text}'
    ax1.text(0.03, 0.97, info_box,
             transform=ax1.transAxes, fontsize=12, fontweight='bold',
             verticalalignment='top',
             bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='#BDBDBD', alpha=0.95))

    # ── 区域标注 ──
    y_min, y_max = ax1.get_ylim()
    if y_max > 0:
        ax1.text(0.97, 0.95, '关机更省电', transform=ax1.transAxes,
                 fontsize=11, ha='right', va='top', color=COLOR_CRITICAL, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.2', facecolor='#E8F5E9', edgecolor=COLOR_CRITICAL, alpha=0.8))
    if y_min < 0:
        ax1.text(0.97, 0.05, '常开更省电', transform=ax1.transAxes,
                 fontsize=11, ha='right', va='bottom', color='#F44336', fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFEBEE', edgecolor='#F44336', alpha=0.8))

    # ── 合并图例 ──
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               loc='lower right', fontsize=10, framealpha=0.9,
               edgecolor='#BDBDBD')

    # ── 标题 ──
    ax1.set_title(f'敏感性分析：{res["label"]} vs 节能比例',
                  fontsize=16, fontweight='bold', pad=15)

    # 美化
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.spines['top'].set_visible(False)

    # 基准参数注释
    base_text = ('基准: T_out=32°C, T_in_init=30°C, T_set=24°C,\n'
                 'tau=6h, COP=3.3, UA=0.1, COP_deg=0.6')
    fig.text(0.5, 0.01, base_text, ha='center', fontsize=9, color='#9E9E9E', style='italic')

    plt.tight_layout(rect=[0, 0.05, 1, 1])

    # 输出文件名映射
    filename_map = {
        't_off': '敏感性分析_外出时长_1200x750.png',
        'T_out': '敏感性分析_室外温度_1200x750.png',
        'T_set': '敏感性分析_设定温度_1200x750.png',
        'tau':   '敏感性分析_热时间常数_1200x750.png',
        'COP':   '敏感性分析_能效比_1200x750.png',
    }
    filename = filename_map.get(factor, f'敏感性分析_{factor}_1200x750.png')
    filepath = save_fig(fig, filename, chart_dir, dpi=150)
    return filepath


# ============================================================
# 3. 临界工况散点矩阵
# ============================================================

def plot_critical_scatter(df_critical, chart_dir):
    """
    T_out vs tau 的临界时长散点图（1张独立图）
    X轴：室外温度，Y轴：临界外出时长
    散点颜色按临界时长映射，添加趋势线
    """
    fig, ax = plt.subplots(figsize=(12, 7.5), facecolor='white')

    T_out = df_critical['T_out'].values
    tau = df_critical['tau'].values
    t_critical = df_critical['t_critical'].values

    # 散点颜色按临界时长映射
    scatter = ax.scatter(T_out, t_critical, c=t_critical, cmap='RdYlGn',
                         s=30, alpha=0.6, edgecolors='white', linewidths=0.3, zorder=3)

    # 添加颜色条
    cbar = plt.colorbar(scatter, ax=ax, pad=0.02)
    cbar.set_label('临界外出时长 (h)', fontsize=11)

    # 趋势线（按tau分组）
    tau_values = np.unique(tau)
    colors_trend = plt.cm.Set2(np.linspace(0, 1, len(tau_values)))

    for i, tv in enumerate(sorted(tau_values)):
        mask = tau == tv
        if mask.sum() > 1:
            # 对每个tau值，拟合 T_out vs t_critical 的趋势
            x_sub = T_out[mask]
            y_sub = t_critical[mask]
            # 排序后绘制平滑趋势
            sort_idx = np.argsort(x_sub)
            x_sorted = x_sub[sort_idx]
            y_sorted = y_sub[sort_idx]
            ax.plot(x_sorted, y_sorted, '-', color=colors_trend[i],
                    linewidth=2, alpha=0.8, label=f'tau={tv:.0f}h', zorder=4)

    # 轴标签和标题
    ax.set_xlabel('室外温度 (°C)', fontsize=13)
    ax.set_ylabel('临界外出时长 (h)', fontsize=13)
    ax.set_title('临界工况：室外温度与热惯性的交互效应',
                 fontsize=16, fontweight='bold', pad=15)

    # 图例
    ax.legend(title='热时间常数', fontsize=10, title_fontsize=11,
              loc='upper left', framealpha=0.9)

    # 美化
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()

    filepath = save_fig(fig, '临界工况_温度与热惯性_1200x750.png', chart_dir, dpi=150)
    return filepath


# ============================================================
# 4. 主函数
# ============================================================

def main():
    """运行全部综合分析，生成所有独立图表"""
    # 路径设置
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    chart_dir = os.path.join(base_dir, 'outputs', 'charts')

    os.makedirs(chart_dir, exist_ok=True)

    # 读取数据
    critical_path = os.path.join(data_dir, 'critical_points_binary_search.csv')
    print(f"读取临界点数据: {critical_path}")
    df_critical = pd.read_csv(critical_path)
    print(f"  -> {len(df_critical)} 条记录")
    print()

    print("=" * 70)
    print("开始综合分析...")
    print("=" * 70)

    # ── 1. 多元回归加权影响力分析 ──
    print("\n>>> [1] 多元回归加权影响力分析")
    print("-" * 50)
    influence_df, r_sq, adj_r_sq = compute_weighted_influence(df_critical)
    print()
    path1 = plot_weighted_influence(influence_df, r_sq, adj_r_sq, chart_dir)

    # ── 2. 单因子敏感性分析 ──
    print("\n>>> [2] 单因子敏感性分析")
    print("-" * 50)
    sensitivity_results, summary_df = single_factor_sensitivity()

    # 每个因子生成独立图
    factor_order = ['t_off', 'T_out', 'T_set', 'tau', 'COP']
    sensitivity_paths = []
    for factor in factor_order:
        res = sensitivity_results[factor]
        print(f"\n绘制 {res['label']} 敏感性分析图...")
        fp = plot_single_factor_sensitivity(factor, res, chart_dir)
        sensitivity_paths.append(fp)

    # ── 3. 临界工况散点矩阵 ──
    print("\n>>> [3] 临界工况散点矩阵")
    print("-" * 50)
    path3 = plot_critical_scatter(df_critical, chart_dir)

    # ── 汇总 ──
    print("\n" + "=" * 70)
    print("综合分析完成！共生成 7 张独立图表:")
    print(f"  1. {path1}")
    for i, fp in enumerate(sensitivity_paths, 2):
        print(f"  {i}. {fp}")
    print(f"  7. {path3}")
    print("=" * 70)

    return influence_df, sensitivity_results, summary_df


if __name__ == '__main__':
    influence_df, sensitivity_results, summary_df = main()
