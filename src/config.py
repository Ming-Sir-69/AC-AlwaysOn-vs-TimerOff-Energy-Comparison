"""
全局配置文件 — 空调能耗对比研究
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, 'src')
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'outputs')
CHART_DIR = os.path.join(OUTPUT_DIR, 'charts')
SVG_DIR = os.path.join(OUTPUT_DIR, 'svg_out_clean')
PNG_DIR = os.path.join(OUTPUT_DIR, 'png_out_clean')
ACADEMIC_TRAIL_DIR = os.path.join(BASE_DIR, 'academic_trail')

# ── 物理常数默认值 ──
UA_DEFAULT = 0.1          # 围护结构综合传热系数 (kW/K)，由原始L25数据反推校准
COP_DEGRADATION = 0.6     # 满负荷急冷时COP衰减系数
HOURS_PER_CYCLE = 24      # 一个完整循环时长 (h)

# ── L25(5^6) 基础实验因子与水平 ──
FACTORS_L25 = {
    'A': {
        'name': '出门时间', 'unit': 'h',
        'levels': [2, 5, 8, 11, 14],
        'col_name': 't_off'
    },
    'B': {
        'name': '室外温度', 'unit': '°C',
        'levels': [28, 30, 32, 34, 36],
        'col_name': 'T_out'
    },
    'C': {
        'name': '关机瞬间室内温', 'unit': '°C',
        'levels': [26, 27, 28, 29, 30],
        'col_name': 'T_in_init'
    },
    'D': {
        'name': '目标温度', 'unit': '°C',
        'levels': [22, 23, 24, 25, 26],
        'col_name': 'T_set'
    },
    'E': {
        'name': '建筑热惯性τ', 'unit': 'h',
        'levels': [2, 4, 6, 9, 12],
        'col_name': 'tau'
    },
    'F': {
        'name': 'COP', 'unit': '无',
        'levels': [2.6, 3.0, 3.3, 3.6, 4.0],
        'col_name': 'COP'
    },
}

# ── L50(5^6) 升级实验 — B因子扩展温度范围 ──
FACTORS_L50 = {
    **FACTORS_L25,
    'B': {
        'name': '室外温度', 'unit': '°C',
        'levels': [26, 30, 34, 38, 40],
        'col_name': 'T_out'
    },
}

# ── 临界区加密补充实验 ──
CRITICAL_ZONE_FACTORS = {
    'A': {
        'name': '出门时间', 'unit': 'h',
        'levels': [7, 8, 9, 10, 12],
        'col_name': 't_off'
    },
    'B': {
        'name': '室外温度', 'unit': '°C',
        'levels': [30, 32, 34, 36],
        'col_name': 'T_out'
    },
    'C': {
        'name': '关机瞬间室内温', 'unit': '°C',
        'levels': [28],
        'col_name': 'T_in_init'
    },
    'D': {
        'name': '目标温度', 'unit': '°C',
        'levels': [24],
        'col_name': 'T_set'
    },
    'E': {
        'name': '建筑热惯性τ', 'unit': 'h',
        'levels': [4, 6, 9],
        'col_name': 'tau'
    },
    'F': {
        'name': 'COP', 'unit': '无',
        'levels': [3.0, 3.6],
        'col_name': 'COP'
    },
}

# ── 图表样式 ──
CHART_STYLE = {
    'figsize': (12, 7),
    'dpi': 150,
    'color_scheme': {
        'scheme_a': '#2196F3',   # 蓝色 - 方案A常开
        'scheme_b': '#F44336',   # 红色 - 方案B关机
        'critical': '#FF9800',   # 橙色 - 临界线
        'fill_a': '#BBDEFB',
        'fill_b': '#FFCDD2',
    },
    'font_family': 'sans-serif',
    'font_names': ['SimHei', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'DejaVu Sans'],
}

# ── Excel 样式 ──
EXCEL_STYLE = {
    'header_fill': '1F4E79',
    'header_font_color': 'FFFFFF',
    'zebra_fill': 'F2F2F2',
    'winner_b_fill': 'FFCCCC',   # B关机更省 - 浅红
    'winner_a_fill': 'CCE5FF',   # A常开更省 - 浅蓝
    'critical_fill': 'FFFFCC',   # 临界区 - 浅黄
    'kpi_fill': 'C6EFCE',        # KPI高亮 - 浅绿
}
