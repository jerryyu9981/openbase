# OpenLLM v2.14.5 跨仓修复交付回执（2026-09-30）

| 项 | 内容 |
|----|------|
| **回执编号** | `E-LLM-v2145-20260930` |
| **对应派单** | `OB-v1.4.10-LLM-CFG-01`（本文档首次登记；来源 OpenBase 侧实测 `E-LLMPROXY-20260930` 的 **F1／F2**） |
| **落点仓** | **OpenLLM**（`backend/`） |
| **交付版本** | **v2.14.5**（patch 位最小版本化） |
| **提交** | `c67bbd5`（分支 `feature/s4-identity-channel-b`） |
| **Tag** | **`v2.14.5` = `25c28f3fc1ad56e7b104e4e7842e38e99bf64d69`** |
| **远端** | **origin ＋ backup ＋ github 三仓一致**（`ls-remote` 实测三仓哈希相同） |
| **执行人** | DO-OpenBase-Dev（跨仓实施） |
| **结论** | ✅ **已修复并实测验证**（正路径 ＋ 负路径双验） |

---

## 1. 修复内容

### 1.1 F1 版本口径漂移

| 项 | 内容 |
|----|------|
| **现象** | 运行时 `/health` 报 `version=2.14.3`，而该仓已按 **v2.14.4** 交付改动（新字段已生效）⇒ 「tag 了 vX、运行时报 vY」 |
| **根因** | `.env` 的 `APP_VERSION=2.14.3` **覆盖**代码默认值；升级时未同步环境配置 |
| **修复** | ① **`.env`（本机，不入库）** 同步为 `APP_VERSION=2.14.5`；② **`.env.example`（入库）新增「应用版本（口径一致性）」段**，明确「升级须同步本值」及漂移后果；③ **代码**：新增启动期**版本口径自检**（`detect_version_drift`），配置版本 ≠ 代码版本时**显式告警** |

### 1.2 F2 默认模型未注册

| 项 | 内容 |
|----|------|
| **现象** | 调用 `qwen3:0.6b`（`.env` 的 `DEFAULT_LLM_MODEL`）返回 **404 `code=2001` 模型不存在** |
| **根因** | 该模型虽在**内置静态支持清单** `app/core/supported_models.py` 内，却**不在 DB 模型注册表** `llm_models`（运行时真正用于选路）—— **两份"模型清单"语义不同，`.env` 取值混淆了二者** |
| **修复** | ① **`.env`** 改为实测可用且已注册的 `deepseek-v4-flash`；② **`.env.example`** 与 **`config.py`** 增注「本值须为 **DB 注册表内 `status=active`** 的模型；静态清单 ≠ 运行时注册表；不一致会 404(2001)」；③ **代码**：新增启动期**注册表一致性自检**（`detect_default_model_drift`），未注册时**告警并列出可用样本** |

### 1.3 修复口径（三条硬约束）

> ① **fail-open**：自检异常只记 WARNING，**不阻塞启动**；
> ② **不静默替换**：**不自动改用**其他模型 —— 那会把配置错误藏起来；
> ③ **启动即暴露**：把「靠人工发现」变为「启动日志一眼可见」。

---

## 2. 交付物清单（5 个文件）

| # | 文件 | 变更 |
|:-:|------|------|
| 1 | `backend/app/core/startup_alignment.py` | **新增**：`code_app_version()`／`detect_version_drift()`／`detect_default_model_drift()`／`run_startup_alignment_checks(session_factory)`（读 `llm_models` 中 `status=active` 的 `model_code`／`model_name`，未命中告警并列出 ≤8 个可用样本） |
| 2 | `backend/app/core/config.py` | `APP_VERSION` 默认 **2.14.4 → 2.14.5**；`DEFAULT_LLM_MODEL` 增注口径 |
| 3 | `backend/main.py` | `lifespan` 在**启动预热之后**接线自检，暴露为启动日志告警 |
| 4 | `backend/.env.example` | 新增「应用版本」段；`DEFAULT_LLM_MODEL` 增注 |
| 5 | `backend/tests/unit/test_v2145_startup_alignment.py` | **新增 12 例**（TDD：先 RED 后 GREEN） |

---

## 3. 验证证据

### 3.1 单测与静态检查

| 项 | 结果 |
|----|------|
| v2.14.5 新增用例 | **12 passed**（先 RED：11 failed ⇒ 实现后 GREEN） |
| 回归（v2.14.4 守护 10 例 ＋ 新增 12 例） | **22 passed** |
| `ruff check`（改动 4 个 py 文件 ＋ 测试） | **All checks passed** |

### 3.2 正路径实测（启动自检通过）

| 观测点 | 实测结果 |
|--------|----------|
| `/health` | `"version":"2.14.5"`，`metrics.app_version:"2.14.5"` —— **版本口径已一致** |
| 启动日志 | `启动自检｜默认模型已注册: deepseek-v4-flash` |
| 启动日志 | `启动自检通过：版本口径与默认模型注册状态一致` |

### 3.3 负路径实测（告警确实会触发）

以**故意错误取值**（`configured_version=2.14.3`／`configured_model=qwen3:0.6b`）对**真实 DB 注册表**调用自检：

```
告警条数: 2
  1. 版本口径漂移: 运行时 APP_VERSION=2.14.3 与代码版本 2.14.5 不一致（.env 覆盖了代码默认值）
     ⇒ 版本核对会失真；请同步 .env／部署配置到 2.14.5
  2. 默认模型未注册: DEFAULT_LLM_MODEL=qwen3:0.6b 不在 DB 模型注册表中
     （可用样本: E2E-Test, deepseek-v4-flash, gpt-4）
     ⇒ 依赖默认模型的调用将返回 404（code=2001）；请改用已注册模型，或先注册该模型
```

> **判据**：① 两条告警**均按预期触发** ⇒ 自检有效；② 样本列表**取自真实注册表**（含 `E2E-Test`／`gpt-4`／`deepseek-v4-flash`）⇒ **注册表读取路径与真实 schema 一致**（非 mock）。

### 3.4 三仓推送核验

| 远端 | `refs/tags/v2.14.5` |
|------|---------------------|
| origin | `25c28f3fc1ad56e7b104e4e7842e38e99bf64d69` |
| backup | `25c28f3fc1ad56e7b104e4e7842e38e99bf64d69` |
| github | `25c28f3fc1ad56e7b104e4e7842e38e99bf64d69` |

**三仓哈希一致** ⇒ 满足 `code-version-backup-management` §5.0「任一远程遗漏视为发布不完整」。

---

## 4. 未纳入本次修复（如实登记）

| # | 项 | 说明 | 处置 |
|:-:|----|------|------|
| 1 | **F3**：`gpt-4` 上游 provider 不可用（实测 500 `code=5001`） | **属上游 provider／网络可达性**，非本仓配置错误 | 保持登记（TD-新增-046 保留该半项）；**联调／用例选可用模型** |
| 2 | **F4**：OpenBase 启动时 DB 初始化失败并降级内存 | **属 OpenBase 侧**，不在本次 OpenLLM 修复范围 | 已在 OpenBase《设计基线及开发测试移交说明》§4 前置 **#7** 登记 |
| 3 | `.env` 本机同步值不入库 | 依安全规则 `.env*` 不落 git | 以 `.env.example` ＋ 启动自检**机制化**兜住后续漂移 |

---

## 5. 对 OpenBase v1.4.10 的影响

| 项 | 变化 |
|----|------|
| **`llm_proxy` → OpenLLM 链路** | 仍为 **✅ 通过**（本次修复不改变链路，只消除配置漂移） |
| **AI 复核辅助模型选择** | `.env` 默认模型已修正为已注册模型；**原「须显式传真实模型名」的约束可放宽为「建议显式指定」**，但**Step 4 用例仍须选可用模型**（因 `gpt-4` 上游不可用） |
| **技术债务** | **TD-新增-047 已偿还**（F1 闭环）；**TD-新增-046 部分偿还**（F2 闭环，F3 provider 项保留） |
| **新增强制项** | 后续 OpenLLM 版本升级**须同步 `.env` 的 `APP_VERSION`**；否则启动日志将出现「版本口径漂移」告警（**已变可观测**） |
