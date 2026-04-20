# 空调常开还是定时关更省电？ · 开发文档

## 研究问题

空调一直开着维持恒定温度，与回家开、出门关，哪种方式更省电？考虑多重维度和不同数值区间，是否存在一个**临界外出时长**，使得两种方式耗电量一致。

## 研究方法

1. **数学建模**：牛顿冷却定律 + 稳态热负荷方程 + COP衰减模型
2. **田口正交实验设计**：L25(5^6) 基础 + L50(5^6) 升级 + 临界区加密补充
3. **Python仿真**：热力学模型 + 能耗对比 + 主效应分析 + ANOVA

## 项目结构

```
├── docs/                  # 数学公式与理论文档（附权威来源URL）
├── outputs/
│   ├── svg_out_clean/     # 公式SVG（矢量）
│   ├── png_out_clean/     # 公式PNG（位图）
│   └── charts/            # 仿真图表（30+张）
├── src/                   # Python仿真脚本
│   ├── config.py          # 全局配置
│   ├── orthogonal_array.py # 正交表生成
│   ├── thermal_model.py   # 热力学模型
│   ├── energy_simulator.py # 仿真引擎
│   ├── taguchi_analyzer.py # 田口分析
│   ├── plot_utils.py      # 绘图工具
│   ├── export_excel.py    # Excel导出
│   └── run_simulation.py  # 主入口
├── data/                  # CSV数据文件
├── interactive/           # Streamlit交互式仪表盘
├── academic_trail/        # Perplexity已有成果
├── 空调能耗仿真结果.xlsx
├── 空调能耗对比研究_综合分析报告.pptx
└── 空调能耗对比研究_综合分析报告V2.pptx
```

## 运行方式

```bash
cd src
pip install -r requirements.txt
python run_simulation.py
```

## 5因子参数空间

| 因子 | 符号 | 范围 | 水平数 |
|------|------|------|:---:|
| 外出时长 | t_off | 0.5-12h | 5 |
| 室外温度 | T_out | 26-40°C | 5 |
| 热时间常数 | τ | 2-12h | 5 |
| 能效比 | COP | 2.5-4.5 | 5 |
| 设定温度 | T_set | 22-28°C | 5 |

## 后续开发方向

- [ ] Streamlit仪表盘部署为在线应用
- [ ] 增加更多建筑类型（轻钢/混凝土/木结构）
- [ ] 与实际空调能耗数据对比验证
- [ ] 论文投稿
