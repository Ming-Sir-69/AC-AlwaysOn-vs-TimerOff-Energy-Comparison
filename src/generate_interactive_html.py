#!/usr/bin/env python3
"""
生成空调能耗对比交互仪表盘 HTML 文件
读取CSV数据 -> 转JSON -> 嵌入HTML -> Plotly.js交互图表
"""

import pandas as pd
import numpy as np
import json
import os

# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "interactive")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "能耗对比交互仪表盘.html")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── 读取数据 ──────────────────────────────────────────────
df = pd.read_csv(os.path.join(DATA_DIR, "L50_enhanced_results.csv"))
df_crit = pd.read_csv(os.path.join(DATA_DIR, "critical_points_binary_search.csv"))

# ── 数据预处理 ────────────────────────────────────────────
# 图表1: 散点图数据
scatter_data = {
    "t_off": df["t_off"].tolist(),
    "T_out": df["T_out"].tolist(),
    "E_A": df["E_A"].round(4).tolist(),
    "E_B": df["E_B"].round(4).tolist(),
    "savings_pct": df["savings_pct"].round(2).tolist(),
    "winner": df["winner"].tolist(),
}
scatter_data["T_out_unique"] = sorted(df["T_out"].unique().tolist())

# 图表2: 临界时长热力图数据
# 策略：固定 T_set=22, COP=3.0, 对 T_in_init 取平均，得到 T_out x tau 的完整矩阵
crit_heatmap = df_crit[
    (df_crit["T_set"] == 22) &
    (df_crit["COP"] == 3.0)
].copy()

heatmap_data = {"T_out_vals": [], "tau_vals": [], "t_critical_matrix": []}
if len(crit_heatmap) > 0:
    pivot = crit_heatmap.pivot_table(
        index="tau", columns="T_out", values="t_critical", aggfunc="mean"
    )
    heatmap_data["T_out_vals"] = [float(x) for x in pivot.columns.tolist()]
    heatmap_data["tau_vals"] = [float(x) for x in pivot.index.tolist()]
    heatmap_data["t_critical_matrix"] = [
        [round(float(v), 4) if not np.isnan(v) else None for v in row]
        for row in pivot.values.tolist()
    ]
else:
    # 最终兜底：不筛选，全部聚合
    pivot = df_crit.pivot_table(
        index="tau", columns="T_out", values="t_critical", aggfunc="mean"
    )
    heatmap_data["T_out_vals"] = [float(x) for x in pivot.columns.tolist()]
    heatmap_data["tau_vals"] = [float(x) for x in pivot.index.tolist()]
    heatmap_data["t_critical_matrix"] = [
        [round(float(v), 4) if not np.isnan(v) else None for v in row]
        for row in pivot.values.tolist()
    ]

# 图表3: 单因子敏感性曲线数据
# 对每个因子，固定其他因子为中位数，计算 savings_pct 随该因子的变化
sensitivity_data = {}
factors = {
    "t_off": "外出时长 (h)",
    "T_out": "室外温度 (°C)",
    "T_set": "设定温度 (°C)",
    "tau": "热时间常数 (h)",
    "COP": "能效比 COP",
}

# 使用 df 数据直接按因子分组
for factor, label in factors.items():
    levels = sorted(df[factor].unique().tolist())
    # 对每个水平，计算平均 savings_pct, E_A, E_B
    group = df.groupby(factor).agg(
        savings_mean=("savings_pct", "mean"),
        savings_std=("savings_pct", "std"),
        E_A_mean=("E_A", "mean"),
        E_B_mean=("E_B", "mean"),
    ).reindex(levels)
    sensitivity_data[factor] = {
        "label": label,
        "levels": [float(x) for x in group.index.tolist()],
        "savings_mean": [round(float(x), 2) for x in group["savings_mean"].tolist()],
        "savings_std": [round(float(x), 2) if not np.isnan(x) else 0 for x in group["savings_std"].tolist()],
        "E_A_mean": [round(float(x), 4) for x in group["E_A_mean"].tolist()],
        "E_B_mean": [round(float(x), 4) for x in group["E_B_mean"].tolist()],
    }

# 图表4: ANOVA 方差贡献率
# 使用 main_effects_summary.csv 如果存在，否则从数据估算
main_effects_path = os.path.join(DATA_DIR, "main_effects_summary.csv")
if os.path.exists(main_effects_path):
    df_me = pd.read_csv(main_effects_path)
    # 计算每个因子的极差（最大均值 - 最小均值）作为贡献代理
    anova_data = {}
    factor_cols = ["t_off", "T_out", "T_in_init", "T_set", "tau", "COP"]
    factor_labels_cn = {
        "t_off": "外出时长", "T_out": "室外温度",
        "T_in_init": "初始室温", "T_set": "设定温度",
        "tau": "热时间常数", "COP": "能效比",
    }
    contributions = []
    for col in factor_cols:
        if col in df_me.columns:
            vals = df_me[col].dropna().values
            if len(vals) > 0:
                range_val = float(np.nanmax(vals) - np.nanmin(vals))
                contributions.append({"factor": factor_labels_cn.get(col, col), "contribution": round(abs(range_val), 4)})
    total = sum(c["contribution"] for c in contributions) if contributions else 1
    for c in contributions:
        c["pct"] = round(c["contribution"] / total * 100, 1) if total > 0 else 0
    anova_data = contributions
else:
    # 从 L50 数据估算：用各因子水平的 savings_pct 均值极差
    factor_labels_cn = {
        "t_off": "外出时长", "T_out": "室外温度",
        "T_in_init": "初始室温", "T_set": "设定温度",
        "tau": "热时间常数", "COP": "能效比",
    }
    contributions = []
    for factor in ["t_off", "T_out", "T_in_init", "T_set", "tau", "COP"]:
        grp = df.groupby(factor)["savings_pct"].mean()
        if len(grp) > 1:
            range_val = float(grp.max() - grp.min())
            contributions.append({"factor": factor_labels_cn.get(factor, factor), "contribution": round(abs(range_val), 2)})
    total = sum(c["contribution"] for c in contributions) if contributions else 1
    for c in contributions:
        c["pct"] = round(c["contribution"] / total * 100, 1) if total > 0 else 0
    anova_data = contributions

# KPI 卡片数据
kpi_data = {
    "avg_critical_hours": round(float(df_crit["t_critical"].mean()), 2),
    "max_savings_pct": round(float(df["savings_pct"].max()), 2),
    "best_case": "",
    "worst_case": "",
}

# 最有利工况（关机最省电 = savings_pct 最大）
best_idx = df["savings_pct"].idxmax()
best_row = df.loc[best_idx]
kpi_data["best_case"] = (
    f"外出{best_row['t_off']}h, 室外{best_row['T_out']}°C, "
    f"tau={best_row['tau']}h, COP={best_row['COP']}, "
    f"节能{best_row['savings_pct']:.1f}%"
)

# 最不利工况（关机反而费电 = savings_pct 最小）
worst_idx = df["savings_pct"].idxmin()
worst_row = df.loc[worst_idx]
kpi_data["worst_case"] = (
    f"外出{worst_row['t_off']}h, 室外{worst_row['T_out']}°C, "
    f"tau={worst_row['tau']}h, COP={worst_row['COP']}, "
    f"多耗{abs(worst_row['savings_pct']):.1f}%"
)

# ── 组装 JSON ─────────────────────────────────────────────
all_data = {
    "scatter": scatter_data,
    "heatmap": heatmap_data,
    "sensitivity": sensitivity_data,
    "anova": anova_data,
    "kpi": kpi_data,
}

json_str = json.dumps(all_data, ensure_ascii=False)

# ── HTML 模板 ─────────────────────────────────────────────
html_template = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>空调能耗对比交互仪表盘</title>
<script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: system-ui, -apple-system, "Microsoft YaHei", sans-serif;
    background: #0b1220;
    color: #e5e7eb;
    min-height: 100vh;
  }
  /* ── 顶部标题栏 ── */
  .header {
    background: linear-gradient(135deg, #0f1b33 0%, #162544 100%);
    border-bottom: 2px solid #f59e0b;
    padding: 18px 32px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .header h1 {
    font-size: 1.6rem;
    font-weight: 700;
    color: #f59e0b;
    letter-spacing: 1px;
  }
  .header .subtitle {
    font-size: 0.85rem;
    color: #9ca3af;
  }
  /* ── 主布局 ── */
  .main-layout {
    display: flex;
    min-height: calc(100vh - 70px);
  }
  /* ── 左侧面板 ── */
  .sidebar {
    width: 260px;
    min-width: 260px;
    background: #0f1b33;
    border-right: 1px solid #1e3a5f;
    padding: 20px 16px;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }
  .sidebar h3 {
    font-size: 0.95rem;
    color: #f59e0b;
    border-bottom: 1px solid #1e3a5f;
    padding-bottom: 8px;
  }
  .control-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .control-group label {
    font-size: 0.8rem;
    color: #9ca3af;
  }
  .control-group select {
    background: #162544;
    color: #e5e7eb;
    border: 1px solid #1e3a5f;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 0.85rem;
    cursor: pointer;
    outline: none;
    transition: border-color 0.2s;
  }
  .control-group select:focus {
    border-color: #f59e0b;
  }
  /* ── 右侧内容 ── */
  .content {
    flex: 1;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    overflow-y: auto;
  }
  /* ── 图表网格 ── */
  .chart-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .chart-card {
    background: #0f1b33;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 14px;
    position: relative;
  }
  .chart-card h4 {
    font-size: 0.9rem;
    color: #f59e0b;
    margin-bottom: 10px;
    padding-left: 10px;
    border-left: 3px solid #f59e0b;
  }
  .chart-card .plotly-chart {
    width: 100%;
    height: 340px;
  }
  /* ── KPI 卡片 ── */
  .kpi-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
  }
  .kpi-card {
    background: #0f1b33;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    transition: border-color 0.3s, transform 0.2s;
  }
  .kpi-card:hover {
    border-color: #f59e0b;
    transform: translateY(-2px);
  }
  .kpi-card .kpi-label {
    font-size: 0.75rem;
    color: #9ca3af;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .kpi-card .kpi-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #f59e0b;
  }
  .kpi-card .kpi-detail {
    font-size: 0.72rem;
    color: #6b7280;
    margin-top: 6px;
    line-height: 1.4;
  }
  .kpi-card.green .kpi-value { color: #66bb6a; }
  .kpi-card.red .kpi-value { color: #ef5350; }
  .kpi-card.blue .kpi-value { color: #42A5F5; }
  /* ── 响应式 ── */
  @media (max-width: 1100px) {
    .chart-grid { grid-template-columns: 1fr; }
    .kpi-row { grid-template-columns: repeat(2, 1fr); }
  }
  @media (max-width: 768px) {
    .main-layout { flex-direction: column; }
    .sidebar { width: 100%; min-width: unset; flex-direction: row; flex-wrap: wrap; }
    .kpi-row { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>

<!-- 顶部标题栏 -->
<div class="header">
  <div>
    <h1>空调能耗对比交互仪表盘</h1>
    <div class="subtitle">方案A（恒温持续运行） vs 方案B（间歇关机重启） — 基于L50正交实验与二分法临界点搜索</div>
  </div>
</div>

<!-- 主布局 -->
<div class="main-layout">
  <!-- 左侧控制面板 -->
  <div class="sidebar">
    <h3>筛选与控制</h3>

    <div class="control-group">
      <label>图表1 — 室外温度筛选</label>
      <select id="filterTout">
        <option value="all">全部温度</option>
      </select>
    </div>

    <div class="control-group">
      <label>图表3 — 敏感性因子</label>
      <select id="sensitivityFactor">
        <option value="t_off">外出时长 (h)</option>
        <option value="T_out">室外温度 (°C)</option>
        <option value="T_set">设定温度 (°C)</option>
        <option value="tau">热时间常数 (h)</option>
        <option value="COP">能效比 COP</option>
      </select>
    </div>

    <div class="control-group">
      <label>图表4 — 方差分析类型</label>
      <select id="anovaType">
        <option value="bar">柱状图</option>
        <option value="pie">饼图</option>
      </select>
    </div>

    <div style="margin-top: auto; padding-top: 16px; border-top: 1px solid #1e3a5f;">
      <div style="font-size:0.72rem; color:#6b7280; line-height:1.5;">
        <strong style="color:#9ca3af;">数据说明</strong><br>
        L50增强正交实验（50组工况）<br>
        二分法临界点搜索（600组）<br>
        悬浮图表可查看详细数值
      </div>
    </div>
  </div>

  <!-- 右侧内容 -->
  <div class="content">
    <!-- 图表网格 -->
    <div class="chart-grid">
      <!-- 图表1: 两方案耗电量对比散点图 -->
      <div class="chart-card">
        <h4>两方案耗电量对比散点图</h4>
        <div id="chart1" class="plotly-chart"></div>
      </div>

      <!-- 图表2: 临界时长热力图 -->
      <div class="chart-card">
        <h4>临界外出时长热力图</h4>
        <div id="chart2" class="plotly-chart"></div>
      </div>

      <!-- 图表3: 单因子敏感性曲线 -->
      <div class="chart-card">
        <h4>单因子敏感性分析</h4>
        <div id="chart3" class="plotly-chart"></div>
      </div>

      <!-- 图表4: 方差贡献率 -->
      <div class="chart-card">
        <h4>各因子方差贡献率 (ANOVA)</h4>
        <div id="chart4" class="plotly-chart"></div>
      </div>
    </div>

    <!-- KPI 卡片 -->
    <div class="kpi-row">
      <div class="kpi-card green">
        <div class="kpi-label">平均临界外出时长</div>
        <div class="kpi-value" id="kpi1">--</div>
        <div class="kpi-detail">超过此时长关机更省电</div>
      </div>
      <div class="kpi-card blue">
        <div class="kpi-label">最大节能比例</div>
        <div class="kpi-value" id="kpi2">--</div>
        <div class="kpi-detail">方案B相对方案A</div>
      </div>
      <div class="kpi-card green">
        <div class="kpi-label">最有利工况（关机最省）</div>
        <div class="kpi-value" id="kpi3" style="font-size:0.9rem;">--</div>
        <div class="kpi-detail" id="kpi3detail"></div>
      </div>
      <div class="kpi-card red">
        <div class="kpi-label">最不利工况（关机反而费电）</div>
        <div class="kpi-value" id="kpi4" style="font-size:0.9rem;">--</div>
        <div class="kpi-detail" id="kpi4detail"></div>
      </div>
    </div>
  </div>
</div>

<script>
// ── 嵌入数据 ─────────────────────────────────────────────
const DATA = __JSON_PLACEHOLDER__;

// ── Plotly 全局布局 ───────────────────────────────────────
const DARK_LAYOUT = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "system-ui, -apple-system, 'Microsoft YaHei', sans-serif", color: "#e5e7eb", size: 12 },
  margin: { t: 10, r: 20, b: 50, l: 55 },
  xaxis: { gridcolor: "#1e3a5f", zerolinecolor: "#1e3a5f", tickfont: { size: 11 } },
  yaxis: { gridcolor: "#1e3a5f", zerolinecolor: "#1e3a5f", tickfont: { size: 11 } },
  legend: { bgcolor: "rgba(0,0,0,0)", font: { size: 11, color: "#e5e7eb" } },
  hoverlabel: { bgcolor: "#162544", font: { color: "#e5e7eb", size: 12 } },
};
const CONFIG = { responsive: true, displayModeBar: true, modeBarButtonsToRemove: ["lasso2d", "select2d"], displaylogo: false };

// ── 初始化温度筛选下拉 ───────────────────────────────────
const selTout = document.getElementById("filterTout");
DATA.scatter.T_out_unique.forEach(t => {
  const opt = document.createElement("option");
  opt.value = t;
  opt.textContent = t + "°C";
  selTout.appendChild(opt);
});

// ── 图表1: 两方案耗电量对比散点图 ────────────────────────
function renderChart1(filterTout) {
  const sd = DATA.scatter;
  const idx = [];
  for (let i = 0; i < sd.t_off.length; i++) {
    if (filterTout === "all" || sd.T_out[i] === filterTout) idx.push(i);
  }

  const traceA = {
    x: idx.map(i => sd.t_off[i]),
    y: idx.map(i => sd.E_A[i]),
    mode: "markers+lines",
    type: "scatter",
    name: "方案A（恒温常开）",
    marker: { color: "#42A5F5", size: 8, line: { color: "#1e88e5", width: 1 } },
    line: { color: "#42A5F5", width: 1, dash: "dot" },
    customdata: idx.map(i => [sd.T_out[i], sd.savings_pct[i], sd.winner[i]]),
    hovertemplate:
      "<b>方案A 恒温常开</b><br>" +
      "外出时长: %{x} h<br>" +
      "日均耗电: %{y:.4f} kWh<br>" +
      "室外温度: %{customdata[0]}°C<br>" +
      "节能比例: %{customdata[1]:.2f}%<br>" +
      "胜出: %{customdata[2]}<extra></extra>",
  };

  const traceB = {
    x: idx.map(i => sd.t_off[i]),
    y: idx.map(i => sd.E_B[i]),
    mode: "markers+lines",
    type: "scatter",
    name: "方案B（间歇关机）",
    marker: { color: "#ef5350", size: 8, line: { color: "#c62828", width: 1 } },
    line: { color: "#ef5350", width: 1, dash: "dot" },
    customdata: idx.map(i => [sd.T_out[i], sd.savings_pct[i], sd.winner[i]]),
    hovertemplate:
      "<b>方案B 间歇关机</b><br>" +
      "外出时长: %{x} h<br>" +
      "日均耗电: %{y:.4f} kWh<br>" +
      "室外温度: %{customdata[0]}°C<br>" +
      "节能比例: %{customdata[1]:.2f}%<br>" +
      "胜出: %{customdata[2]}<extra></extra>",
  };

  const layout = JSON.parse(JSON.stringify(DARK_LAYOUT));
  layout.xaxis.title = { text: "外出时长 (h)", standoff: 10 };
  layout.yaxis.title = { text: "日均耗电量 (kWh)", standoff: 10 };
  layout.title = { text: "", font: { size: 0 } };

  Plotly.react("chart1", [traceA, traceB], layout, CONFIG);
}

selTout.addEventListener("change", () => renderChart1(selTout.value));
renderChart1("all");

// ── 图表2: 临界时长热力图 ────────────────────────────────
function renderChart2() {
  const hm = DATA.heatmap;
  if (!hm.t_critical_matrix || hm.t_critical_matrix.length === 0) {
    document.getElementById("chart2").innerHTML = "<div style='color:#9ca3af;text-align:center;padding-top:80px;'>暂无热力图数据</div>";
    return;
  }

  const trace = {
    z: hm.t_critical_matrix,
    x: hm.T_out_vals,
    y: hm.tau_vals,
    type: "heatmap",
    colorscale: [
      [0, "#1a237e"],
      [0.25, "#42A5F5"],
      [0.5, "#66bb6a"],
      [0.75, "#f59e0b"],
      [1, "#ef5350"],
    ],
    colorbar: {
      title: { text: "临界时长 (h)", font: { color: "#e5e7eb", size: 11 } },
      tickfont: { color: "#e5e7eb" },
      thickness: 14,
    },
    hovertemplate:
      "室外温度: %{x}°C<br>" +
      "热时间常数: %{y} h<br>" +
      "临界外出时长: %{z:.2f} h<extra></extra>",
    showscale: true,
  };

  const layout = JSON.parse(JSON.stringify(DARK_LAYOUT));
  layout.xaxis.title = { text: "室外温度 (°C)", standoff: 10 };
  layout.yaxis.title = { text: "建筑热时间常数 (h)", standoff: 10 };

  Plotly.react("chart2", [trace], layout, CONFIG);
}
renderChart2();

// ── 图表3: 单因子敏感性曲线 ──────────────────────────────
function renderChart3(factor) {
  const sd = DATA.sensitivity[factor];
  if (!sd) return;

  const traceSavings = {
    x: sd.levels,
    y: sd.savings_mean,
    type: "scatter",
    mode: "lines+markers",
    name: "节能比例 (%)",
    line: { color: "#66bb6a", width: 3 },
    marker: { color: "#66bb6a", size: 8 },
    yaxis: "y",
    hovertemplate:
      "<b>" + sd.label + "</b><br>" +
      "水平: %{x}<br>" +
      "平均节能: %{y:.2f}%<extra></extra>",
  };

  const traceEA = {
    x: sd.levels,
    y: sd.E_A_mean,
    type: "scatter",
    mode: "lines+markers",
    name: "方案A 耗电 (kWh)",
    line: { color: "#42A5F5", width: 2, dash: "dash" },
    marker: { color: "#42A5F5", size: 6 },
    yaxis: "y2",
    hovertemplate:
      "方案A: %{y:.4f} kWh<extra></extra>",
  };

  const traceEB = {
    x: sd.levels,
    y: sd.E_B_mean,
    type: "scatter",
    mode: "lines+markers",
    name: "方案B 耗电 (kWh)",
    line: { color: "#ef5350", width: 2, dash: "dash" },
    marker: { color: "#ef5350", size: 6 },
    yaxis: "y2",
    hovertemplate:
      "方案B: %{y:.4f} kWh<extra></extra>",
  };

  // 零线
  const traceZero = {
    x: [sd.levels[0] - 1, sd.levels[sd.levels.length - 1] + 1],
    y: [0, 0],
    type: "scatter",
    mode: "lines",
    name: "零线（临界）",
    line: { color: "#f59e0b", width: 1.5, dash: "dot" },
    yaxis: "y",
    hoverinfo: "skip",
  };

  const layout = JSON.parse(JSON.stringify(DARK_LAYOUT));
  layout.xaxis.title = { text: sd.label, standoff: 10 };
  layout.yaxis.title = { text: "节能比例 (%)", standoff: 10, color: "#66bb6a" };
  layout.yaxis2 = {
    title: { text: "耗电量 (kWh)", standoff: 10, color: "#9ca3af" },
    overlaying: "y",
    side: "right",
    gridcolor: "rgba(0,0,0,0)",
    zerolinecolor: "#1e3a5f",
    tickfont: { color: "#9ca3af", size: 10 },
    rangemode: "tozero",
  };
  layout.legend.x = 0.02;
  layout.legend.y = 0.98;

  Plotly.react("chart3", [traceSavings, traceZero, traceEA, traceEB], layout, CONFIG);
}

document.getElementById("sensitivityFactor").addEventListener("change", (e) => renderChart3(e.target.value));
renderChart3("t_off");

// ── 图表4: 方差贡献率 ────────────────────────────────────
function renderChart4(type) {
  const anova = DATA.anova;
  if (!anova || anova.length === 0) return;

  let traces;
  let layout;

  if (type === "pie") {
    traces = [{
      labels: anova.map(d => d.factor),
      values: anova.map(d => d.pct),
      type: "pie",
      hole: 0.4,
      marker: {
        colors: ["#42A5F5", "#ef5350", "#66bb6a", "#f59e0b", "#ab47bc", "#26c6da"],
        line: { color: "#0f1b33", width: 2 },
      },
      textinfo: "label+percent",
      textfont: { color: "#e5e7eb", size: 11 },
      hovertemplate: "<b>%{label}</b><br>贡献率: %{value:.1f}%<extra></extra>",
    }];
    layout = JSON.parse(JSON.stringify(DARK_LAYOUT));
    layout.showlegend = false;
    layout.margin = { t: 10, r: 10, b: 10, l: 10 };
  } else {
    traces = [{
      x: anova.map(d => d.factor),
      y: anova.map(d => d.pct),
      type: "bar",
      marker: {
        color: anova.map((_, i) => ["#42A5F5", "#ef5350", "#66bb6a", "#f59e0b", "#ab47bc", "#26c6da"][i % 6]),
        line: { color: "#0f1b33", width: 1 },
        opacity: 0.9,
      },
      text: anova.map(d => d.pct.toFixed(1) + "%"),
      textposition: "outside",
      textfont: { color: "#e5e7eb", size: 11 },
      hovertemplate: "<b>%{x}</b><br>贡献率: %{y:.1f}%<extra></extra>",
    }];
    layout = JSON.parse(JSON.stringify(DARK_LAYOUT));
    layout.xaxis.title = { text: "影响因子", standoff: 10 };
    layout.yaxis.title = { text: "方差贡献率 (%)", standoff: 10 };
    layout.yaxis.rangemode = "tozero";
  }

  Plotly.react("chart4", traces, layout, CONFIG);
}

document.getElementById("anovaType").addEventListener("change", (e) => renderChart4(e.target.value));
renderChart4("bar");

// ── KPI 卡片 ─────────────────────────────────────────────
function renderKPIs() {
  const kpi = DATA.kpi;
  document.getElementById("kpi1").textContent = kpi.avg_critical_hours + " h";
  document.getElementById("kpi2").textContent = kpi.max_savings_pct + "%";
  document.getElementById("kpi3").textContent = "节能 " + kpi.max_savings_pct + "%";
  document.getElementById("kpi3detail").textContent = kpi.best_case;
  // 最不利工况
  const worstMatch = kpi.worst_case.match(/多耗([\d.]+)%/);
  const worstPct = worstMatch ? worstMatch[1] : "0";
  document.getElementById("kpi4").textContent = "多耗 " + worstPct + "%";
  document.getElementById("kpi4detail").textContent = kpi.worst_case;
}
renderKPIs();

// ── 窗口大小变化时重绘 ───────────────────────────────────
window.addEventListener("resize", () => {
  Plotly.Plots.resize("chart1");
  Plotly.Plots.resize("chart2");
  Plotly.Plots.resize("chart3");
  Plotly.Plots.resize("chart4");
});
</script>

</body>
</html>"""

# ── 替换 JSON 占位符并写入文件 ────────────────────────────
html_content = html_template.replace("__JSON_PLACEHOLDER__", json_str)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"[OK] HTML 文件已生成: {OUTPUT_FILE}")
print(f"     文件大小: {os.path.getsize(OUTPUT_FILE) / 1024:.1f} KB")
print(f"     数据行数: L50={len(df)}, 临界点={len(df_crit)}")
