"""
主入口脚本 — 空调能耗对比仿真

运行流程：
1. 加载配置
2. 生成正交表（L25 + L50 + 临界区加密）
3. 运行仿真
4. 田口分析（主效应 + ANOVA）
5. 生成图表（7张）
6. 导出Excel
7. 打印摘要报告
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from config import (
    FACTORS_L25, FACTORS_L50, CRITICAL_ZONE_FACTORS,
    DATA_DIR, CHART_DIR, UA_DEFAULT, COP_DEGRADATION,
    BASE_DIR
)
from orthogonal_array import get_L25, get_L50, get_critical_zone_supplementary
from energy_simulator import run_experiment
from taguchi_analyzer import compute_main_effects, compute_anova, find_critical_threshold
from plot_utils import save_fig, COLORS
import matplotlib.pyplot as plt

def generate_charts(df_l25, df_l50, df_cz, main_effects_l50, chart_dir, df_critical=None):
    """生成7张分析图表"""

    # 图表1：散点图 — 出门时间 vs 节能比例（L50数据，按室外温度着色）
    fig, ax = plt.subplots(figsize=(12, 7))
    for t_out_val in sorted(df_l50['T_out'].unique()):
        subset = df_l50[df_l50['T_out'] == t_out_val]
        ax.scatter(subset['t_off'], subset['savings_pct'],
                   label=f'T_out={t_out_val}\u00b0C', alpha=0.7, s=60)
    ax.axhline(y=0, color=COLORS['critical'], linestyle='--', linewidth=2, label='临界线(0%)')
    ax.set_xlabel('出门时间 (h)', fontsize=12)
    ax.set_ylabel('节能比例 (%)', fontsize=12)
    ax.set_title('出门时间 vs 节能比例（按室外温度分组）', fontsize=14)
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left')
    ax.grid(True, alpha=0.3)
    save_fig(fig, 'chart1_scatter_savings.png', chart_dir)

    # 图表2：主效应图（L50数据）
    factor_cols = ['t_off', 'T_out', 'T_in_init', 'T_set', 'tau', 'COP']
    factor_names = ['出门时间(h)', '室外温度(\u00b0C)', '室内初始温(\u00b0C)', '目标温度(\u00b0C)', '热惯性\u03c4(h)', 'COP']

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()
    for idx, (col, name) in enumerate(zip(factor_cols, factor_names)):
        ax = axes[idx]
        effects = main_effects_l50.get(col, pd.Series())
        if len(effects) > 0:
            ax.plot(range(len(effects)), effects.values, 'o-', color=COLORS['levels'][idx], linewidth=2, markersize=8)
            ax.set_xticks(range(len(effects)))
            ax.set_xticklabels([str(v) for v in effects.index], fontsize=9)
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.set_title(name, fontsize=11)
        ax.set_ylabel('\u0394E均值 (kWh)', fontsize=9)
        ax.grid(True, alpha=0.3)
    fig.suptitle('各因子主效应图（L50实验）', fontsize=14, y=1.02)
    plt.tight_layout()
    save_fig(fig, 'chart2_main_effects.png', chart_dir)

    # 图表3：临界点等高线图（出门时间 x 室外温度）
    fig, ax = plt.subplots(figsize=(12, 7))
    # 用L50数据创建透视表
    pivot = df_l50.pivot_table(values='savings_pct', index='t_off', columns='T_out', aggfunc='mean')
    X, Y = np.meshgrid(pivot.columns, pivot.index)
    Z = pivot.values
    cs = ax.contourf(X, Y, Z, levels=20, cmap='RdYlGn', alpha=0.8)
    ax.contour(X, Y, Z, levels=[0], colors=COLORS['critical'], linewidths=3)
    plt.colorbar(cs, ax=ax, label='节能比例(%)')
    ax.set_xlabel('室外温度 (\u00b0C)', fontsize=12)
    ax.set_ylabel('出门时间 (h)', fontsize=12)
    ax.set_title('节能比例等高线图（橙色线=临界点）', fontsize=14)
    save_fig(fig, 'chart3_contour.png', chart_dir)

    # 图表4：拟合曲线图 — 使用二分法数据绘制不同tau下临界出门时间随T_out变化
    if df_critical is not None and len(df_critical) > 0:
        fig, ax = plt.subplots(figsize=(12, 7))
        tau_values = sorted(df_critical['tau'].unique())
        for tau_val in tau_values:
            subset = df_critical[df_critical['tau'] == tau_val]
            if len(subset) >= 2:
                # 对每个tau，按T_out排序并绘制t_critical
                subset_sorted = subset.sort_values('T_out')
                ax.plot(subset_sorted['T_out'], subset_sorted['t_critical'],
                        'o-', label=f'τ={tau_val}h', linewidth=2, markersize=6)
        ax.set_xlabel('室外温度 (°C)', fontsize=12)
        ax.set_ylabel('临界外出时长 (h)', fontsize=12)
        ax.set_title('不同热惯性下临界出门时长随室外温度变化', fontsize=14)
        ax.legend()
        ax.grid(True, alpha=0.3)
        save_fig(fig, 'chart4_critical_curve.png', chart_dir)

    # 图表5：箱线图 — 各因子对节能比例的分布
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()
    for idx, (col, name) in enumerate(zip(factor_cols, factor_names)):
        ax = axes[idx]
        data_groups = [df_l50[df_l50[col] == lv]['savings_pct'].values for lv in sorted(df_l50[col].unique())]
        bp = ax.boxplot(data_groups, labels=[str(v) for v in sorted(df_l50[col].unique())], patch_artist=True)
        for patch in bp['boxes']:
            patch.set_facecolor(COLORS['levels'][idx])
            patch.set_alpha(0.6)
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.set_title(name, fontsize=11)
        ax.set_ylabel('节能比例(%)', fontsize=9)
        ax.grid(True, alpha=0.3)
    fig.suptitle('各因子对节能比例的分布影响（箱线图）', fontsize=14, y=1.02)
    plt.tight_layout()
    save_fig(fig, 'chart5_boxplot.png', chart_dir)

    # 图表6：方差贡献饼图
    fig, ax = plt.subplots(figsize=(10, 8))
    # 运行ANOVA
    anova = compute_anova(df_l50, factor_cols)
    anova_factors = anova[anova['Factor'] != 'Error']
    labels = anova_factors['Factor'].values
    sizes = anova_factors['Contribution(%)'].values
    # 过滤掉贡献率极小的因子
    mask = sizes > 0.5
    if mask.sum() > 0:
        labels, sizes = labels[mask], sizes[mask]
    colors_pie = COLORS['levels'][:len(labels)]
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors_pie, startangle=90)
    ax.set_title('各因子方差贡献率', fontsize=14)
    save_fig(fig, 'chart6_anova_pie.png', chart_dir)

    # 图表7：3D曲面图 — 出门时间 x 室外温度 x 节能比例
    from mpl_toolkits.mplot3d import Axes3D
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')
    if not pivot.empty and not np.all(np.isnan(pivot.values)):
        X3, Y3 = np.meshgrid(pivot.columns, pivot.index)
        Z3 = pivot.values
        surf = ax.plot_surface(X3, Y3, Z3, cmap='RdYlGn', alpha=0.8, edgecolor='none')
        fig.colorbar(surf, ax=ax, shrink=0.5, label='节能比例(%)')
    ax.set_xlabel('室外温度 (\u00b0C)', fontsize=11)
    ax.set_ylabel('出门时间 (h)', fontsize=11)
    ax.set_zlabel('节能比例 (%)', fontsize=11)
    ax.set_title('节能比例3D曲面图', fontsize=14)
    save_fig(fig, 'chart7_3d_surface.png', chart_dir)


def main():
    print("=" * 60)
    print("  空调能耗对比仿真 — 本地深入研究版")
    print("=" * 60)

    # 1. 生成正交表
    print("\n[1/6] 生成正交表...")
    L25 = get_L25()
    L50 = get_L50()
    cz_array, cz_info = get_critical_zone_supplementary()
    print(f"  L25: {L25.shape}, L50: {L50.shape}, 临界区补充: {cz_array.shape}")

    # 2. 运行仿真
    print("\n[2/6] 运行仿真...")
    df_l25 = run_experiment(L25, FACTORS_L25, UA=UA_DEFAULT, COP_degradation=COP_DEGRADATION)
    df_l50 = run_experiment(L50, FACTORS_L50, UA=UA_DEFAULT, COP_degradation=COP_DEGRADATION)
    cz_factor_levels = {k: {'levels': None} for k in ['A', 'B', 'C', 'D', 'E', 'F']}
    df_cz = run_experiment(cz_array, cz_factor_levels, UA=UA_DEFAULT, COP_degradation=COP_DEGRADATION)

    # 保存CSV
    os.makedirs(DATA_DIR, exist_ok=True)
    df_l25.to_csv(os.path.join(DATA_DIR, 'L25_base_results.csv'), index=False)
    df_l50.to_csv(os.path.join(DATA_DIR, 'L50_enhanced_results.csv'), index=False)
    df_cz.to_csv(os.path.join(DATA_DIR, 'critical_zone_dense_results.csv'), index=False)
    print(f"  L25: B更省 {(df_l25['winner']=='B关机更省').sum()}/{len(df_l25)}, 平均节能 {df_l25['savings_pct'].mean():.2f}%")
    print(f"  L50: B更省 {(df_l50['winner']=='B关机更省').sum()}/{len(df_l50)}, 平均节能 {df_l50['savings_pct'].mean():.2f}%")
    print(f"  临界区: B更省 {(df_cz['winner']=='B关机更省').sum()}/{len(df_cz)}, 平均节能 {df_cz['savings_pct'].mean():.2f}%")

    # 3. 田口分析
    print("\n[3/6] 田口分析...")
    factor_cols = ['t_off', 'T_out', 'T_in_init', 'T_set', 'tau', 'COP']
    main_effects_l25 = compute_main_effects(df_l25, factor_cols)
    main_effects_l50 = compute_main_effects(df_l50, factor_cols)
    anova_l25 = compute_anova(df_l25, factor_cols)
    anova_l50 = compute_anova(df_l50, factor_cols)

    # 保存主效应和ANOVA
    me_df = pd.DataFrame(main_effects_l50)
    me_df.to_csv(os.path.join(DATA_DIR, 'main_effects_summary.csv'))

    t_crit_l25 = find_critical_threshold(df_l25)
    t_crit_l50 = find_critical_threshold(df_l50)
    t_crit_cz = find_critical_threshold(df_cz)
    print(f"  L25临界点: {t_crit_l25:.2f}h" if t_crit_l25 else "  L25未找到临界点")
    print(f"  L50临界点: {t_crit_l50:.2f}h" if t_crit_l50 else "  L50未找到临界点")
    print(f"  临界区临界点: {t_crit_cz:.2f}h" if t_crit_cz else "  临界区未找到临界点")

    # 4. 二分法临界点精确搜索（提前到图表生成之前，chart4需要此数据）
    print("\n[4/6] 二分法临界点搜索...")
    from binary_search_critical import run_critical_point_study, generate_factor_combos
    # 生成全因子工况组合（8 x 3 x 5 x 5 = 600组）
    factor_combos = generate_factor_combos()
    df_critical = run_critical_point_study(factor_combos, UA=UA_DEFAULT, COP_deg=COP_DEGRADATION)
    df_critical.to_csv(os.path.join(DATA_DIR, 'critical_points_binary_search.csv'), index=False)
    print(f"  完成 {len(df_critical)} 组工况的临界点搜索")
    print(f"  临界时长范围: {df_critical['t_critical'].min():.2f}h ~ {df_critical['t_critical'].max():.2f}h")
    print(f"  平均临界时长: {df_critical['t_critical'].mean():.2f}h")

    # 5. 生成图表（chart4使用二分法数据）
    print("\n[5/6] 生成图表...")
    generate_charts(df_l25, df_l50, df_cz, main_effects_l50, CHART_DIR, df_critical=df_critical)

    # 6. 导出Excel
    print("\n[6/6] 导出Excel...")
    from export_excel import export_all_results
    excel_path = os.path.join(BASE_DIR, '空调能耗仿真结果.xlsx')
    export_all_results(df_l25, df_l50, df_cz, main_effects_l50, anova_l50, excel_path)

    # 摘要报告
    print("\n摘要报告")
    print("=" * 60)
    print(f"  L25实验({len(df_l25)}组): 临界出门时长 ≈ {t_crit_l25:.1f}h" if t_crit_l25 else "  L25: 未找到临界点")
    print(f"  L50实验({len(df_l50)}组): 临界出门时长 ≈ {t_crit_l50:.1f}h" if t_crit_l50 else "  L50: 未找到临界点")
    print(f"  临界区加密({len(df_cz)}组): 临界出门时长 ≈ {t_crit_cz:.1f}h" if t_crit_cz else "  临界区: 未找到临界点")
    print(f"\n  Excel已保存: {excel_path}")
    print(f"  图表已保存: {CHART_DIR}/")
    print("=" * 60)

    # ── [额外2] 多维度双方案对比图表 ──
    print("\n[额外] 生成双方案对比图表...")
    from chart_dual_scheme import generate_all_dual_scheme_charts
    generate_all_dual_scheme_charts(df_l25, df_l50, df_cz, df_critical, CHART_DIR)

if __name__ == '__main__':
    main()
