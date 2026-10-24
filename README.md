# academic_skills

科研图表制作 skill 的源码仓库。核心产物是 `scientific-figure/`——一个 DSH / Agent Skill，让模型从数据或需求出发，产出可投稿的图表。

## 安装

DSH 从 `~/.dsh/skills` 发现用户级 skill。源码留在本仓库，用软链暴露：

```bash
ln -sfn "$(pwd)/scientific-figure" ~/.dsh/skills/scientific-figure
```

验证：重启 DSH 会话后，技能目录中应出现 `scientific-figure`。卸载：`rm ~/.dsh/skills/scientific-figure`（只删链接）。

## 环境要求

| 组件 | 用途 | 必需 |
|---|---|---|
| `uv` | 运行脚本（PEP 723 内联依赖，零污染） | 是 |
| Python 3.11+ | 脚本运行时 | 是 |
| matplotlib / numpy / pillow | 绘图与图像处理 | 由 uv 自动安装 |
| LaTeX（xelatex + pgfplots） | TikZ 路线、PGF 导出 | TikZ 路线必需 |
| `pdfcrop` / `pdftoppm` / `pdfinfo` / `pdffonts`（poppler） | TikZ 编译后处理、字体校验 | TikZ 路线必需 |

自检：

```bash
uv run scientific-figure/scripts/sf_doctor.py --fix
```

## 它做什么

| 能力 | 实现 |
|---|---|
| 多期刊风格 | 11 个 `.mplstyle`（Nature/Science/IEEE/Elsevier/Cell/PNAS/ACS/APS/ACM/中文期刊/学位论文）+ `journals.json` 机器可读规格 |
| 多格式导出 | PDF/SVG/PGF/TikZ/EPS/PNG/TIFF，含字体嵌入与可编辑性校验 |
| 两条路线 | matplotlib 脚本，或模型手写 TikZ 模板 + Python 填数据 |
| 三层质量门禁 | L1 静态源码分析 → L2 运行时布局检查 → L3 裁剪视觉审查 |
| 配色审计 | WCAG 对比度、CIE L* 灰度分离、Machado 色盲模拟 |
| 表格 | booktabs / siunitx 三线表生成 |
| 团队协作 | 角色分工、写作用域、任务 DAG、交接协议 |

## 核心设计

**裁剪坐标由模型决定，不由脚本猜。** `sf_crop.py --overlay` 先渲染一张带 0–1 坐标网格的参考图，模型读图后写出裁剪 spec，脚本只执行坐标。因此它适用于任何来源的图像——matplotlib、TikZ、Origin、他人论文截图——不依赖任何绘图库内部结构。

**三层门禁不重叠：**

| 层 | 查什么 | 查不到什么 |
|---|---|---|
| L1 静态 | 可复现性、单位、不确定性、N、colormap、等网格、导出格式 | 任何依赖数据分布的问题 |
| L2 运行时 | 文本碰撞、图例遮挡、面板重叠、字号、刻度拥挤、越界 | 字形质量、负号正确性 |
| L3 视觉 | 构图、灰度可辨、字形、对齐、四轴判断 | — |

L3 不可跳过。示例 `examples/fig1-timeseries-ci/review.md` 记录了一个真实案例：图形通过了 L1 与 L2 的全部检查，但视觉裁剪发现 `-0.5` 的负号被渲染成连字符。这个缺陷静态分析看不到。

## 目录

```
scientific-figure/
├── SKILL.md            # 模型入口：4 条硬规则、六阶段、路线选择、脚本与文档索引
├── references/         # 11 篇渐进披露文档
├── scripts/            # 11 个 CLI，PEP 723，JSON 输出 + 退出码
├── styles/             # 11 个期刊 .mplstyle + journals.json
├── palettes/           # 10 组色板 + 色盲模拟数据
├── templates/          # contract / 绘图脚本 / 团队任务 DAG
├── evals/              # 7 个预埋缺陷负样本 + 20 条触发测试
└── examples/           # 完整示例（脚本 + 数据 + 契约 + 审查记录）
```

## 验收

```bash
# 环境
uv run scientific-figure/scripts/sf_doctor.py

# 负样本：7 个预埋缺陷必须全部被检出
cd scientific-figure/evals/negative-cases
uv run make_cases.py -o .
for f in case-*.py; do uv run ../../scripts/sf_lint.py --all "$f"; done

# 端到端示例
cd ../../examples/fig1-timeseries-ci && uv run plot.py
```

## 参考来源

设计吸收了以下开源项目的公开思路，代码为原创实现：

- [TAO-QKV/Icarus-Figures](https://github.com/TAO-QKV/Icarus-Figures)（MIT）：四轴质量标尺、Figure Contract、静态 critique 门禁
- [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)（MIT）：科学诚信护栏、期刊规格快照、配色审计
- [tvhahn/matplotlib-skill](https://github.com/tvhahn/matplotlib-skill)（MIT）：运行时布局检查
- [thunlp/MatPlotAgent](https://github.com/thunlp/MatPlotAgent)：视觉反馈修正闭环
- [Dsadd4/AgentFigureGallery](https://github.com/Dsadd4/AgentFigureGallery)（MIT）：参考图驱动的风格反推

## 开发

```bash
uv sync          # 开发环境
uv run pytest    # 脚本回归
```
