# 上下文编排基线工装端到端骨架验证（TT-044）

> 属性：本报告为**工装链端到端骨架验证**产物（TT-044），以固定集构建回执样例，判定模型为演示注入（skeleton-judge-v1）。**真实 B0/B1 数值测量**以 D3 + 真实回执导出（AC-148-01-1）为前提，不以本骨架样例充当基结论。

## 方法
只观测测量：同一固定集、固定参数、固定模型下取相邻点位差值；A 引用检测为主指标（仅纵向对比），B LLM 归因抽样校准漏检率，C 消融做效度检验

## 样本量
- 样本量：30（可判定下限 30）
- 是否可判定：是

## 漏检率区间
- 区间：[0.45, 0.55]（窗口 ±0.05，由 B LLM 归因抽样校准 A 引用检测）

## 无效上下文占比（WCR，三分口径）
- 硬浪费率：0.23
- 软占用率：0.29
- 必要占用率：0.49
- 三分之和：1.00（须为 1.00，不得只给单值）

## 判定方法（三要素）
1. A 引用检测：随每次调用计算，主指标，**只能纵向对比**；
2. B LLM 归因：抽样 ≥30 条，校准漏检率，判定模型不与被评模型同源；
3. C 消融：一次性 10~15 条，做效度检验。

## 结论
- 本点位数据齐备，按判定规则与相邻点位差值解读。

---

## 复现与验证记录

| 项目 | 内容 |
|------|------|
| 执行时点 | 2026-09-22 |
| 驱动脚本 | `backend/scripts/run_baseline_pipeline.py`（**只做数据编排**，不含裁剪 / 改写对话输出逻辑，不落存片段或回答正文） |
| 执行命令 | `python scripts/run_baseline_pipeline.py --out <本文件>` |
| 退出码 | **0**（工装链端到端跑通） |
| 运行环境 | Windows / PowerShell 5 / Python 3.10.11 / pytest 9.1.1 |
| 静态质量 | `ruff check scripts/run_baseline_pipeline.py` → `All checks passed!` |
| 提交 | OpenLLM 仓 `feature/s4-identity-channel-b`：**`cb3d301`**（`test(v148)`，1 文件 `+234`，显式路径 `git add`） |

### 各环节实测值

| 环节（工装编号） | 实测值 |
|------------------|--------|
| 工装 6 固定集校验 | `total=35`、场景 `7`（S1~S7 各 5 条）、负例 `10`、`ok=True`；评分记录模板 9 项（含四维评分） |
| 工装 5 归因 B 抽样 | 抽样后样本量 `30`（= 可判定下限 `MIN_SAMPLES`）；判定模型 `skeleton-judge-v1`；prompt `ab-judge-v1` |
| 工装 5 归因 B 判定 | 标签计数 `{"used": 30, "unused": 30, "uncertain": 30}` |
| 工装 5 校准 → 工装 7 汇总 | 漏检率（校准样例）`0.500`，区间 `0.45~0.55`（窗口 ±0.05） |
| 工装 7 WCR 三分 | 硬浪费 `0.23` / 软占用 `0.29` / 必要占用 `0.49`，**之和 = 1.00** |
| 工装 7 渲染 | 报告骨架四要素齐备：方法 / 样本量 / 漏检率区间 / WCR 三分（另含判定方法三要素、结论） |

### 单测回归（工装链无回归）

```
python -m pytest tests/unit/test_golden_set_and_scale.py tests/unit/test_attribution_b_tool.py \
                 tests/unit/test_baseline_report_tool.py tests/unit/test_context_metrics_instrumentation.py \
                 tests/unit/test_s4_t1_baseline_probe.py -q --noconftest -p no:cacheprovider
→ 59 passed in 16.64s
```

> 说明：本次调用加 `--noconftest`，用于规避仓库根 `tests/conftest.py` 在本机的**既知环境缺陷**（pgAdmin 内嵌 `site-packages` 路径遮蔽导致 `cryptography._rust` DLL 加载失败）。上述 5 个工装单测文件均为自包含用例，不依赖应用级夹具，规避遮蔽不影响用例有效性与结论。

### 验证结论与限制

1. **TT-044 验收项达成**：七项工装可端到端跑通（驱动脚本退出码 0），产出报告骨架且四要素齐备。
2. **工装链无回归**：59 项工装相关单测全通过（0 failed）。
3. **限制（须显式声明）**：本文件为**骨架验证**产物 —— 回执为固定集构建的样例、判定为演示注入（`skeleton-judge-v1`）、WCR 计数为注入值；**真实 B0/B1 数值测量**仍以 `D3` + 真实回执导出（`AC-148-01-1`）为前提，**不得以本文件样例值充当基线结论**。