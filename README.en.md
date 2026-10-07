<picture>
  <source media="(prefers-color-scheme: dark)" srcset="readme-assets/header-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="readme-assets/header-light.svg">
  <img alt="Always On or Timed Off? · ✦ EricMingle69" src="readme-assets/header-light.svg" width="100%">
</picture>

<p align="center">
  <a href="README.md">简体中文</a> · <a href="README.en.md">English</a> · <a href="PERSONAL-NOTICE.md">✦ EricMingle69</a>
</p>

# Always On or Timed Off?

An energy study comparing continuous temperature control with switching off while away and restarting on return.
It connects Newtonian cooling, Taguchi experimental design and ANOVA to charts and reports.

## Inspect results and assumptions

| Goal | Entry |
| --- | --- |
| Understand the model and references | [Formula and source index](docs/07_公式汇总与来源索引.md) |
| Follow development and reproduction | [README_DEV.md](README_DEV.md) |
| Explore interactive charts | [Energy comparison dashboard](interactive/能耗对比交互仪表盘.html) |
| Read results | [Charts](outputs/charts/) · [Excel](空调能耗仿真结果.xlsx) · [Report](空调能耗对比研究_综合分析报告.pptx) |

The dashboard is an HTML file; download it and open it in a browser.

## Reproduce in a separate copy

Prepare Python and pip, then run from the repository root:

```sh
cd src
python3 -m pip install -r requirements.txt
python3 run_simulation.py
```

The entry regenerates CSV files, charts and the root Excel workbook; preserve outputs you want to compare first.
Check the development guide for the minimum Python version, fonts and complete environment requirements.

## Continue from the source

[The entry point](src/run_simulation.py) orchestrates simulation; [configuration](src/config.py) defines parameters; [the thermal model](src/thermal_model.py) implements model calculations.
Energy-saving findings are model results under specific assumptions and parameters, not measured guarantees for every room or device.

## Scope of use

Describe the environment, boundary conditions, parameters and measured validation when interpreting results.
No LICENSE covers the original code and research materials; confirm sources and permission for citation and redistribution separately.

---

Documentation maintained by **✦ EricMingle69** · [Ming-Sir-69](https://github.com/Ming-Sir-69)  
[Personal identity, licensing and permissions](PERSONAL-NOTICE.md) · The header follows your GitHub theme.
