# 本地小模型精炼对比基准（Ollama）

用于给「上下文精炼用小模型」选型：在同一个 Ollama 端点上跑同一套中文评测集，比较候选模型在
四类精炼任务上的**精度**与**时延**，产出可直接比较的表格（Markdown / CSV）与原始明细（JSON）。

服务端选型背景与精炼护栏见 `doc/design/OpenBase-上下文精装配与组件通道优化技术方案-v1.0.0.md` §5。

## 评测任务与精度指标

| 任务 | 输入 | 期望输出 | 主指标 |
|------|------|----------|--------|
| `route` | 一条用户问题 | JSON `{"need_memory":bool,"need_rag":bool}` | 逐字段准确率（另有 JSON 合规率、完全一致率） |
| `select` | 问题 + 10 条候选条目（4 条相关） | 相关条目编号 | 与标注的 F1（另有精确率、召回率、格式合规率） |
| `compress` | 问题 + 5 条长条目 | 编号要点列表（≤5 条） | 关键事实保留率（另有压缩率、格式合规率） |
| `summarize` | 1 条长记忆 | ≤2 句话要点 | 关键事实保留率（另有压缩率、格式合规率） |

精度判定不依赖人工评分：`compress` / `summarize` 的 gold 是**预先标注的关键事实**（样本标识、
预算代号、数值、实体），按字符串命中率计算；`select` 的 gold 是**预先标注的相关条目下标**。

时延口径：**预热后**单次调用的墙钟耗时（P50 / P95 / max）；预热（模型加载）单独记录且不计入分位。
同时从 Ollama 响应读取 `eval_count` / `eval_duration` 计算 tokens/s，并记录 `size_vram` 判断推理位置
（`0` 或缺失表示 CPU 或未完全卸载到 GPU）。

## 公平性设置

跨模型完全一致：同一个 system prompt、`temperature=0`、`seed=20260927`、`num_ctx=4096`、
`num_predict` 按任务固定（route 64 / select 96 / compress 192 / summarize 128）、`think=false`；
输出统一剥离 ` thinking` 块后再评分。每个模型先做一次预热调用。

## 用法

```powershell
# 快速试跑（每任务前 4 条）
python small_model_bench.py --base-url http://127.0.0.1:11434 `
  --models qwen3:0.6b,llama3.2:1b --limit-items 4 --tag local-cpu

# 扩展候选（在能拉取模型的机器上）
ollama pull qwen3.5:0.8b
ollama pull qwen3:1.7b
ollama pull qwen3.5:4b
python small_model_bench.py --base-url http://127.0.0.1:11434 `
  --models qwen3.5:0.8b,qwen3:1.7b,qwen3.5:4b --tag local-gpu

# 只跑某几类任务
python small_model_bench.py --models qwen3:1.7b --tasks route,compress
```

产物（与脚本同目录）：`small-model-bench-<日期>[-标签].json`（逐条明细）、`.md`（对比表 + 排序）、
`.csv`（便于画图）。另有一行解析式基线 `rule-baseline(no-model)`：原文原样保留，用于衡量精炼的
精度代价与压缩收益。

## 选型规则

1. 先看**精度门槛**：`compress` / `summarize` 的关键事实保留率 ≥ 0.90，`select` 的 F1 ≥ 0.70，
   `route` 的逐字段准确率 ≥ 0.90（低于门槛的模型不进入候选）。
2. 再看**时延门槛**：P95 ≤ 精炼预算（方案 §5.6：CPU 档 800ms、GPU 档 400ms）。
3. 门槛内取**最低 P95**；若没有模型同时满足，则先降低任务难度（缩短输入、减少条目），
   或退回规则档（去重 + 排序 + 配额裁剪），把模型精炼留给离线场景。

## 已知环境约束（本仓库执行环境实测）

- 本机无 NVIDIA GPU（`nvidia-smi` 缺失），CPU 为 i5-8400（6 核 6 线程）、内存 11.9 GB；
  Ollama 运行在 `127.0.0.1:11434`（v0.32.15），模型加载耗时约 26 s，CPU 推理 tokens/s 偏低。
- Ollama 默认模型目录 `D:\Ollama\Models` 在本环境**不可写**（拉取新模型报 Access denied）；
  基准改用可写目录运行：设置 `OLLAMA_MODELS` 指向工作目录下的 `ollama-models`，
  并把已有的 `blobs` / `manifests` 复制过去即可复用已下载模型。
- 本环境到 `registry.ollama.ai` 的下载不稳定（多次拉取长时间停在中途），
  因此完整候选梯队（1.7B / 4B）建议在具备 GPU 且网络可达的节点上执行。
- 局域网 Ollama 端点 `192.168.0.4:11434`（v0.32.15）可直连，当前镜像内模型为
  `qwen2.5:0.5b`、`llama3.2:1b`；同一脚本可用 `--base-url` 指向它做跨机对比。
