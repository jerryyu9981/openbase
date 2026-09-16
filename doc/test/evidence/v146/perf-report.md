# OpenBase v1.4.6 专项测试 · 性能测试报告

| 项目 | 内容 |
|------|------|
| 文档名称 | OpenBase v1.4.6 专项测试 · 性能测试报告 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 被测版本 | v1.4.6（`/api/v1/logs/search`、`/api/v1/logs/export` 为主） |
| 测试类型 | 专项测试（后端微基准 P50/P95/P99 + 串行/小并发；前端构建产物性能） |
| 作者 | SE-OpenBase-Test（测试工程师）/ AT-OpenBase-Test（自动化测试） |
| 执行日期 | 2026-09-15 |
| 原始数据 | `doc/test/evidence/v146/perf-raw.json`、`doc/test/evidence/v146/perf-dist-stats.json` |
| 依据 | `doc/design/OpenBase-非功能设计说明-v1.4.6.md` §2（P99<2s / 三重限幅 / 导出流式）、`doc/design/OpenBase-API接口设计文档-v1.4.6.md` §3.1/§3.3、`doc/requirements/OpenBase-开发需求文档-v1.4.6.md` §7 |

---

## 1. 执行环境（真实、含已知干扰项）

| 项 | 实测值 |
|----|--------|
| OS / CPU | Windows / Intel Core i5-8400 @2.80GHz，**逻辑处理器 6** |
| Python / 依赖 | Python 3.10.11；FastAPI 0.139.2、uvicorn 0.51.0、SQLAlchemy 2.0.49、asyncpg 0.31.0 |
| 被测服务 | `python -m uvicorn openbase.demo_app:app --port 8021`（`OPENBASE_LOG_DIR=<临时目录>`、`OPENBASE_LOG_SETUP=0`）；截断探测实例 8022 |
| 数据库 | PostgreSQL `192.168.0.151:5432`（**跨网段远端库**，导出留痕需同步写 `audit_logs`） |
| Redis / 上游四服务 | 均未启动（本测试不依赖） |
| **并发干扰（如实登记）** | ① 端口 8011 存在先前启动的 OpenBase 实例；② 本机同时有 6 个 python 进程 / 4 个 node 进程（含其他 Step 4 测试轨的进程）。故本次为**共享机器上的相对基准**，绝对值偏保守 |

**数据集（合成，脚本 `gen_log_data.py`）**

| 数据集 | 行数 | 字节 | 说明 |
|--------|-----:|-----:|------|
| 主分片 `openbase-20260914.jsonl` | 50,000 | 12,959,221（12.4 MiB） | 检索/导出微基准 |
| 截断探测分片 `openbase-20260915.jsonl` | **201,000** | 50,846,779（48.5 MiB） | 触顶扫描上限（200,000 行）与 `truncated` 语义 |

**执行命令**

```powershell
python -u 'c:\Users\jerry\.trae-cn\work\6a8c5d08e67967d7e6726b59\perf_test.py'   # → perf-raw.json
npm run build                                                                      # openbase-ui（vue-tsc --noEmit && vite build）
python 'c:\Users\jerry\.trae-cn\work\6a8c5d08e67967d7e6726b59\dist_stats.py'       # → perf-dist-stats.json
```

---

## 2. `/api/v1/logs/search` 微基准

### 2.1 串行（含 3 次预热；单源 `l1_file`，50,000 行分片）

| 场景 | n | min(ms) | **P50** | P90 | **P95** | **P99** | max | mean | sd |
|------|---|--------:|--------:|----:|--------:|--------:|----:|-----:|---:|
| `q=bench-llm`（命中 8,000）+ `page=1&page_size=20` | 20 | 1,078.33 | **1,338.84** | 1,486.05 | **1,666.46** | **1,666.46** | 1,666.46 | 1,318.77 | 146.70 |
| 无关键字 + `page=2&page_size=20`（命中 50,000） | 20 | 1,215.44 | **1,434.15** | 1,745.50 | **1,803.88** | **1,803.88** | 1,803.88 | 1,491.53 | 173.53 |
| `page_size=100` | 10 | 1,193.12 | **1,436.95** | 1,641.26 | 1,641.26 | 1,641.26 | 1,641.26 | 1,424.08 | 108.94 |

响应体：`page_size=20` 中位 7,840 B；`page_size=100` 中位 37,107 B。全部 200。

### 2.2 小并发（10 并发 × 20 次 = 200 请求；`q=bench-llm`）

| 指标 | 值 |
|------|----|
| 请求数 / 全部状态 | 200 / **200**（无 5xx） |
| min / **P50** / P90 / **P95** / **P99** / max | 2,450.11 / **12,722.12** / 20,214.03 / **23,005.28** / **26,550.82** / 27,626.49 ms |
| mean / sd | 12,944.03 / 5,492.54 ms |
| 总墙钟 / 吞吐 | **269.22 s** / **0.74 rps** |
| 对比串行吞吐 | 串行 20 次耗时约 26.4 s ≈ **0.76 rps** → **并发增益 ≈ 0（甚至略降）**，而单请求延迟上升约 **9.5 倍** |

结论：在 6 核机器上 10 并发**没有带来任何吞吐提升**，仅把延迟线性放大（P50 1.34 s → 12.72 s）。与实现特征一致：日志检索端点为 `def`（同步）→ 由 FastAPI 线程池执行，而检索主体是 **Python 层 CPU 密集的全分片读取 + 逐行 `json.loads`**（受 GIL 串行化），因此线程数增加不产生并行收益。

---

## 3. `/api/v1/logs/export` 微基准

| 场景 | n | min | **P50** | P90 | **P95** | P99 | max | 响应体中位 |
|------|---|----:|--------:|----:|--------:|----:|----:|-----------:|
| CSV，命中 8,000 行（1 次预热） | 10 | 1,224.54 | **1,434.14** | 1,552.08 | 1,552.08 | 1,552.08 | 1,552.08 | 1,247,905 B（1.19 MiB） |
| JSON，命中 4 行 | 10 | 1,184.16 | **1,392.62** | 1,604.99 | 1,604.99 | 1,604.99 | 1,604.99 | 1,942 B |

| 小并发场景 | 值 |
|------------|----|
| CSV 5 并发 × 10 次（50 请求） | min 3,173.74 / **P50 8,820.14** / P90 **63,386.08** / **P95 68,142.60** / **P99 69,250.60** / max 69,250.60 ms；mean 23,121.13；**墙钟 267.90 s，吞吐 0.19 rps**；50/50 成功 |

**关键观察（导出耗时与命中行数无关）**：命中 **4 行** 的 JSON 导出 P50 1,392.62 ms ≈ 命中 **8,000 行** 的 CSV 导出 P50 1,434.14 ms → 耗时几乎全部来自「**整个分片的全量读取 + 逐行解析**」，而非行数或序列化。导出并发时的 P90/P95（63–68 s）表明：全量扫描 + 同步 `audit_logs` 远端写库叠加后尾延迟急剧劣化。

### 3.1 上限与截断语义（正向验证）

| 用例 | 真实响应 | 判定 |
|------|----------|:----:|
| 主分片（50,000 行）`/logs/search` | `{"total":50000,"truncated":false,...}` | ✅ 未触顶 |
| **截断分片（201,000 行）** `/logs/search` | `{"total":200000,"truncated":true,"page":1,"page_size":20}`；**单请求耗时 102,331.70 ms** | ✅ 语义正确（200 + `truncated=true`，非静默截断） |
| 截断分片 `/logs/export?format=csv` | **400** `{"code":"PARAM_400","message":"export matched rows exceed limit: matched=200000, limit=10000","detail":{"matched":200000,"limit":10000}}`（耗时 61,591.58 ms） | ✅ 导出上限生效 |
| 主分片 `/logs/export?format=csv`（命中 50,000 > 10,000） | **400** `{"code":"PARAM_400",...,"detail":{"matched":50000,"limit":10000}}` | ✅ |

> **性能结论（P1）**：设计指标为「单次 **P99 < 2s**（默认 24h 窗、`page_size=20`、单源）」。实测：50,000 行分片 P99=1.67 s（达标但仅占设计扫描上限的 **1/4**）；**达到设计扫描上限（200,000 行）时单请求高达 102.3 s，超目标约 51 倍**。同时设计要求的「L1 分片倒序 + 命中足量**提前终止**」在 `L1FileAdapter.fetch()` 中未体现（`page_size=20` 的请求同样扫描完整分片；`read_text().splitlines()` 全量入内存），这是耗时与文件体积线性相关、且并发无增益的直接原因。

---

## 4. 前端产物性能

**构建命令与结果**

```powershell
> npm run build        # vue-tsc --noEmit && vite build
vite v6.4.3 building for production...
✓ 3030 modules transformed.
✓ built in 3m 46s
```

- 无「chunk 超过 `chunkSizeWarningLimit`（1200 kB）」告警；
- 1 条构建告警：`src/core/router/index.ts` 既被动态导入又被静态导入（`main.ts`），"dynamic import will not move module into another chunk"（既有实现口径，非本次增量引入）。

**dist 体积（`perf-dist-stats.json`）**

| 维度 | 文件数 | 原始字节 | gzip 字节 |
|------|-------:|---------:|----------:|
| 合计 | **157** | **3,061,075**（2.92 MiB） | **978,184**（955 KiB） |
| `.js` | 83 | 2,668,030 | 913,643 |
| `.css` | 73 | 392,570 | 64,207 |
| `index.html` | 1 | 475 | 334 |

**最大 chunk（Top 10）**

| 文件 | 原始字节 | gzip 字节 | 说明 |
|------|---------:|----------:|------|
| `assets/echarts-ClPwX7rX.js` | **1,036,306** | **341,878** | 最大 chunk（手动分块） |
| `assets/element-plus-CZdQSH-C.js` | **1,034,658** | **335,778** | 次大 chunk（手动分块） |
| `assets/index-DmoTU3W7.css` | 362,235 | 48,141 | 全局样式 |
| `assets/index-D0uylQhk.js` | 104,001 | 39,412 | 应用主包 |
| `assets/MemoryGraph-Dn1A4Air.js` | 74,328 | 26,036 | 模块按需 chunk |
| **`assets/LogsView-CnHIFnWa.js`** | **15,809** | **5,376** | **v1.4.6 日志中心页 chunk（本增量）** |

- echarts + element-plus 两个 chunk 合计 **2,070,964 B（占 JS 总量 77.6%）**，是首屏/交互加载的主要成本项；
- 本增量新增页面 `LogsView` 仅 15.8 kB（gzip 5.4 kB），**增量对产物体积影响极小**（占比 0.5%）。

**Lighthouse：不可用（明确标注）**

| 项 | 结论 |
|----|------|
| 工具状态 | `openbase-ui/node_modules` 中**无 `lighthouse` / `chrome-launcher`**（命令：`Get-ChildItem node_modules -Directory | Where-Object Name -like 'lighthouse*'` → 无输出）；任务口径要求「不联网安装」 |
| 浏览器条件 | 仅存在 Playwright 内置 `chromium_headless_shell`（`%LOCALAPPDATA%\ms-playwright`），非 Lighthouse 所需稳定 Chrome 通道 |
| 未执行项 | 性能/可访问性/最佳实践/SEO 四类 Lighthouse 审计均**未执行** |
| 补救计划 | 在有网环境执行 `npx lighthouse http://<host>/platform/observability/logs --only-categories=performance,accessibility,best-practices --output=json --output-path=lighthouse-v146.json`（或 `npm i -D lighthouse chrome-launcher` 后本地跑），结果回填本节 |

---

## 5. 结果汇总

| 序 | 测试项 | 关键数字 | 结论 |
|:--:|--------|----------|------|
| 1 | search 串行（50k 分片） | P50 1,338.84 ms / P99 1,666.46 ms | ✅ 达标（24h 窗、page_size=20、单源） |
| 2 | search 串行（无关键字、更大页） | P99 1,803.88 ms（50k）/ 1,641.26 ms（page_size=100） | ✅ 接近上限但达标 |
| 3 | search 10 并发 × 20 | P50 12,722 ms / P95 23,005 ms / **0.74 rps** | ❌ **P1：无并发增益、延迟线性劣化** |
| 4 | export 串行（8,000 行 CSV） | P50 1,434.14 ms / 1.19 MiB | ✅ 单请求可用 |
| 5 | export 5 并发 × 10 | P90 63,386 ms / P95 68,143 ms / **0.19 rps** | ❌ **P1：尾延迟不可接受** |
| 6 | 扫描上限与 truncated | 201k → total=200000、truncated=true；**102.3 s/请求** | ⚠️ 语义正确 / **P1 性能**（超 P99<2s 目标 51 倍） |
| 7 | 导出上限 | 命中 >10,000 → 400 `PARAM_400`，`detail={matched,limit}` | ✅ 契约正确 |
| 8 | 前端产物 | 157 文件 / 3.06 MB 原始 / 0.98 MB gzip；最大 chunk 1.04 MB（echarts） | ⚠️ 可接受 + 优化建议（P2） |
| 9 | Lighthouse | — | ⚪ **未执行（工具缺失，含补救计划）** |

---

## 6. 问题清单

### P1-1（代码缺陷 · 性能）扫描上限下检索/导出严重超时，且并发无吞吐增益

- **现象**：200,000 行（设计扫描上限）单请求 **102.3 s**（目标 P99 < 2 s）；10 并发检索 P95 **23.0 s**、吞吐 0.74 rps（= 串行水平）；5 并发导出 P95 **68.1 s**。
- **根因（代码级，只读核对）**：`openbase/modules/logs/repository.py:L1FileAdapter.fetch()` 对分片 `path.read_text().splitlines()` **全量读入内存**并**逐行 `json.loads` + 逐条构造 `LogEntry`**，仅在"收集到 `limit`（200,000）条"时才停止 —— 对 `page_size=20` 的分页请求亦扫描完整分片；设计 §2 要求的「命中足量**提前终止**」与「分片倒序按需回退」未生效；端点 `def`（同步）→ 线程池 + GIL，CPU 密集无并行收益。
- **契约依据**：非功能设计 §2（P99<2s、三重限幅、提前终止）；需求 §7 性能指标。
- **建议**：① 解析结果按分片做进程内缓存（mtime 失效）；② 分页场景按需扫描到 `page*page_size` 即止并记录 `scanned_lines`；③ 或改为异步 + 解析下沉（`orjson`/`uvloop`、`asyncio.to_thread` + 独立引擎），并在 API 暴露 `scanned` 供前端提示；④ 引入「近 24h + 命中数」联合限幅，避免无关键字全量扫描。
- **证据**：`perf-raw.json` → `search_concurrent_10x20`、`truncation_probe_search`、`truncation_probe_export`、`main_shard_meta`。

### P1-2（代码缺陷 · 性能/可靠性）导出并发时尾延迟爆炸

- **现象**：5 并发 × 10 次导出，P90 63.4 s / P95 68.1 s / P99 69.3 s（单并发仅 1.43 s）。
- **根因**：① 与 P1-1 同源的全量扫描；② 每次导出**同步**写 1 条 `audit_logs` 到**远端** PostgreSQL（留痕为 fail-closed 前置校验，见安全报告 P2-1 的关联实现），并发时形成连接/锁竞争；③ 导出内容在内存整体拼接（`io.StringIO`，未 `StreamingResponse`），大响应体同时占用内存与 socket 时间。
- **建议**：留痕写独立连接池/批量写入；导出改 `StreamingResponse`；对导出加并发闸门（如信号量）与队列化，避免无限并发。
- **证据**：`perf-raw.json` → `export_concurrent_5x10`、`export_serial_csv_8000`。

### P2-1（优化建议）前端首屏两大 chunk 各约 1.04 MB

- echarts（1,036,306 B / gzip 341,878 B）与 element-plus（1,034,658 B / gzip 335,778 B）合计占 JS 体积 77.6%；echarts 仅在图谱类页面使用，建议改为**路由级异步加载**（移除 `manualChunks` 强制打入公共块），Element Plus 建议按需引入（`unplugin-vue-components`）或分包，预计可显著改善首屏。
- 依据：`perf-dist-stats.json`；构建命令 `npm run build`。

### P2-2（测试环境限制）共享机器与远端数据库带来的基准偏差

- 本机 6 逻辑核，同机存在 6 个 python 与 4 个 node 进程（含其他测试轨）；PostgreSQL 位于跨网段 `192.168.0.151`。故 P50/P95 绝对值偏保守，**但"并发无增益"这一结构性结论与 CPU/GIL 特征一致，不受网络影响**。建议在独占环境复测以固化基线。

---

## 7. 未执行 / 受限项与补救计划

| 项 | 状态 | 原因 | 补救计划 |
|----|------|------|----------|
| Lighthouse（性能/可访问性/最佳实践/SEO） | **未执行** | `lighthouse` 未安装且任务口径禁止联网安装；仅有 Playwright chromium_headless_shell | 有网环境 `npx lighthouse …` 或 `npm i -D lighthouse chrome-launcher`；结果回填 §4 |
| gzip/Brotli 服务器端传输实测 | 未执行 | 本次以 `gzip.compress` 静态计算产物压缩比（0.98 MB / 3.06 MB ≈ 32%），未验证 Web 服务器是否开启 `gzip_static`/Brotli | 部署窗口对 `nginx.conf.example` 的 gzip/brotli 配置做响应头核验（`Content-Encoding`） |
| 前端运行时性能（FCP/LCP/INP、内存） | 未执行 | 无 Lighthouse/Performance API 采集脚本（超出本次工具条件） | 与 Lighthouse 一并补充，或在 E2E 中加 `performance.getEntriesByType('navigation')` 采集 |
| 数据库直连压测（连接池饱和） | 未执行 | 本轮聚焦四端点微基准；`audit_db` 源本身不可用（见安全报告 P1-2） | `audit_db` 修复后补充 DB 源单请求与并发基准 |
| 200k 分片下的多次重复基准 | 部分执行 | 单请求已 102 s，重复 20 次成本过高（≈34 分钟），故只取 1 次实测 + 1 次导出 | 优化（P1-1）后重跑并给出 P50/P95/P99 |

---

## 8. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-15 | SE-OpenBase-Test / AT-OpenBase-Test | 初始版本：search/export 串行与并发微基准（50k/201k 分片）、truncated 与三重限幅正向验证、前端构建产物统计（157 文件 / 3.06 MB）；登记 P1 性能缺陷 2 项、P2 2 项、未执行项 4 项（含 Lighthouse 缺失说明）；原始数据 `perf-raw.json`、`perf-dist-stats.json` |
