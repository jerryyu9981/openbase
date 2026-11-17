# Spec：P0~P4 改动对 OpenLLM 主备通道影响核查与 P1 读侧收口

## 文档元信息

| 项 | 内容 |
|---|---|
| 版本 | v1.0.1 |
| 状态 | [Approved]（已批准；P1 读侧收口已实施并验证） |
| 适用环境 | Dev（OpenBase 8000 + DPS 8030/8000 + OpenLLM B 通道 + 前端 5173） |
| 作者 | AI 编码代理 |
| 创建日期 | 2026-11-17 |
| 关联文档 | `doc/design/OpenBase-画像模板-标注模板-评分项对应关系与治理方案-v1.0.0.md`（v1.4.2） |

## 1. 核查结论（已完成静态核查）

B 通道（OpenLLM 经 `DpsClient`）固定调用 4 个 DPS 接口，本阶段改动未新增/删除/改签名：

| B 通道调用 | 文件 | P0 | P1 | P2 | P3 | P4 | 结论 |
|---|---|---|---|---|---|---|---|
| `POST /api/v2/portrait/calculate` | `backend/app/edgerouter/adapters/dps_client.py` `profile_read` | 默认口径不变（不传 `template_code` → 常量 6 维/权重）；但前缀标签现在可命中常量规则 | 默认口径不变 | 未改 | 未改 | 未改 | 无契约变化，分数/状态可能出现预期内数据面变化 |
| `GET /api/v2/portrait/{person_id}` | 同上 | 未改 | **读侧未按 D-04 择优，tags 出现同名多行** | 未改 | 未改 | 未改 | **存在疏漏（本次修复）** |
| `PUT/PATCH /api/v2/portrait/{person_id}` | `dps_client.py` `profile_update` + `profile.py` 映射 | 未改 | 未改 | 未改 | 未改 | 未改 | 无影响 |
| `GET /api/v2/portrait/list`（探活） | `dps_client.py` `ping` | 未改 | 未改 | 未改 | 未改 | 未改 | 无影响 |

补充事实：

- P0（`bf4eb12`）核查：
  - `_execute_calc(person_id, None)` 的四类模板入参均为 `None` → `core.calculate_portrait` 回落到 `_DIMENSION_RULES` / `_DIMENSION_WEIGHTS`，模板不再成为默认路径的隐式事实源（`routes_profiles.py` L138-164、`core.py` L92-95）。
  - `validation._calculate_overall_score` 的 `weights=None` 回落 `self._dimension_weights`，默认综合分口径不变（`validation.py` L25-51）。
  - **数据面变化（有意）**：`calculate_dimension_score` 新增「规则 key 去前缀 → 标签去前缀」后缀匹配（`core.py` L159-200），`_calculate_data_completeness` 同步支持后缀匹配（`validation.py` L80-97）。此前 DB 中 `<dimension>:<tag_key>` 标签对无前缀常量规则永不命中；现在若标签 key 与常量规则 key 同名即可命中，默认计算的维度分/完整度/`status` 可能变化。治理方案 §4 已确认标注字段 key 与常量规则 key 当前交集为 0，故存量标注数据无变化；仅手工/导入标签可能触发。
  - 其余 P0 改动（`tag_key`/`score_map`/`score_direction`、`tag_bindings` 归一与引用校验、`scoring-items` 新接口）均为 A 通道管理/标注写入面，B 通道不调用、不感知。
  - 结论：B 通道无需代码适配；仅需在文档登记「默认计算对前缀标签的后缀匹配属 P0 有意修复」。

- P1 的 `profile_tag` 来源隔离（DDL 删除 `UNIQUE(profile_id, tag_code)`，新增 `source`/`annotation_template_code`）使同一 `tag_code` 可有多行；评分读路径（`engines/portrait/crud.py::pick_preferred_tags`）已择优，但**通用画像读**（`engines/query_engine.py::get_portrait/get_portraits`）仍 `SELECT *` 原样返回。
- OpenLLM 对 tags 不做解析：`dps_client._normalize_portrait` 原样保留列表，`profile.py::_map_real_portrait_to_sections` 放入 `business["tags"]`，`openllm_gateway._format_profile_ctx` 直接字符串化进入 Prompt。因此多行同名标签 = Prompt 重复且值冲突；新增列属附加字段，不破坏解析。
- P2 三个只读接口（lineage/field-mapping/dimension-details）与 `scoring-items` 内部复用改造：仅 A 通道（OpenBase dps-proxy）暴露，B 通道不调用；`scoring-items` 响应结构不变（治理方案 §13.6）。
- P3 证据门禁/异常规则（标注创建与审核）与 2 个只读接口：B 通道不写标注、不调用新接口；`/portrait/governance/*`、`/portrait/{person_id}/anomaly-alerts` 在 DPS 与 OpenBase 代理均注册于动态段之前（已核对）。
- P4：已核查并收口（文档 v1.4.2），本次不重复修改。
- A/B 能力矩阵为能力级（`OpenLLM/backend/app/identity/ab_equivalence.py`，仅「画像读/画像写」）；P2/P3 的解释性/策略面属 A 通道管理面扩展，不要求 B 对齐，但需在治理方案中显式登记，避免后续误判为遗漏。

## 2. 变更方案（唯一代码修复，P1 读侧收口）

### 2.1 目标

在不改存储、不改 DDL、不改 OpenLLM 契约解析的前提下，让通用画像读恢复 P1 之前的「同一 `tag_code` 唯一生效行」不变式，且择优规则与评分读路径完全一致（D-04）。

### 2.2 精确改动

文件：`D:\Trae CN\myproject\Dev\DPS\src\engines\query_engine.py`

1. 顶部导入（位于 `from models import (...)` 之后）：
   ```python
   from engines.portrait.crud import pick_preferred_tags
   ```
2. 新增模块级函数（放在 `logger = logging.getLogger(__name__)` 之后）：
   ```python
   def _prefer_unique_tags(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
       """多来源同名标签按 D-04 择优；legacy/异构行（缺 tag_code）原样返回。"""
       if not rows or not all(
           isinstance(row, dict) and row.get("tag_code") for row in rows
       ):
           return rows
       return list(pick_preferred_tags(rows).values())
   ```
3. `get_portrait`：标签查询完成后、组装 `portrait_data` 前（当前 L139 附近）插入
   `tags = _prefer_unique_tags(tags)`。
4. `get_portraits`：`tags_list` 按 person_id 分组前（当前 L226 附近）对每个分组值应用
   `tags_map[pid] = _prefer_unique_tags(tags_map[pid])`（在组装循环内、写缓存前）。

约束：不删除 `source`/`annotation_template_code` 列（附加字段对 B 通道向后兼容）；不改缓存键；不改 SQLite 缺列分支（`all(...)` 守卫保证原样返回）。

### 2.3 新增测试

文件（新建）：`D:\Trae CN\myproject\Dev\DPS\src\tests\test_p1_read_side_tag_preference.py`

用例（3 条）：

1. `test_get_portrait_prefers_manual_annotation`：mock `query_engine.cache.get_portrait → None`、`cache.set_portrait → AsyncMock`、`db.fetch_one` 返回画像行、`db.fetch_all` 返回三条同 `tag_code` 不同来源（`legacy`/`other`/`manual_annotation`）→ 结果 `tags` 长度 1 且 `source == "manual_annotation"`。
2. `test_get_portrait_keeps_legacy_rows_without_tag_code`：标签行仅含 `profile_id`/`tag_name`（无 `tag_code`）→ 原样返回全部行（不丢标签）。
3. `test_get_portraits_dedupes_each_person`：两人各含重复 `tag_code` → 每人 `tags` 均唯一。

测试要求：`monkeypatch.setattr(qe, "db", ...)` / `qe.cache`，禁止真实数据库；`python -m pytest` 可独立运行。

## 3. 验证步骤

工作目录 `D:\Trae CN\myproject\Dev\DPS`：

```bash
python -m pytest src/tests/test_p1_read_side_tag_preference.py -q
python -m pytest src/tests/test_p0_template_scoring_v3.py src/tests/test_p1_governance_v3.py src/tests/test_portrait_list_route.py src/tests/test_tenant_isolation.py -q
python -m ruff check src/engines/query_engine.py src/tests/test_p1_read_side_tag_preference.py
```

工作目录 `D:\Trae CN\myproject\Dev\OpenLLM\backend`（确认 B 通道无回归；纯读取兼容，不改代码）：

```bash
python -m pytest tests/unit/test_real_contract_profile.py -q
```

## 4. 文档回填

文件：`d:\Trae CN\myproject\Dev\OpenBase\doc\design\OpenBase-画像模板-标注模板-评分项对应关系与治理方案-v1.0.0.md`

- 版本 v1.4.2 → **v1.4.3**；修订历史新增一行（核查 P1~P3 主备通道 + P1 读侧择优收口）。
- 新增 `## 16. 主备通道影响核查（P1~P4）`：B 通道 4 接口影响表、P2/P3 A-only 扩展登记、修复与验证证据。
- 状态列维持 [Approved]，注明「P1~P4 主备通道核查完成」。

## 5. 提交与推送

- DPS：`fix(portrait): 读侧按 D-04 择优同名标签`（`src/engines/query_engine.py` + 新测试），推送 origin/backup/github。
- OpenBase：文档 v1.4.3，推送 origin/backup/github。

## 6. 风险与边界

| 风险 | 处置 |
|---|---|
| 直接消费「全部来源行」的外部调用方 | 当前仓库内无此类消费方；A 前端 `PortraitDetail.vue` 仅展示标签，去重后更符合预期 |
| SQLite legacy 无 `tag_code` | `all(...)` 守卫，原样返回，零行为变化 |
| 缓存中已存在旧形态（多行）数据 | 缓存 TTL 自然过期；本次不改缓存键（避免影响面扩大） |
| B 通道 Prompt 出现 `source` 等内部列 | 附加字段，本次不裁剪（避免改动 OpenLLM 契约层）；登记为可接受残余 |

## 7. 验收标准

- AC-01：`GET /api/v2/portrait/{person_id}` 对同名 `tag_code` 只返回 1 行，优先级 `manual_annotation > 其他 > legacy`。
- AC-02：无 `tag_code` 的 legacy 行不被丢弃。
- AC-03：`get_portraits` 批量结果同样去重。
- AC-04：新增 3 条单测通过，定向回归无新增失败，`ruff` 0 错误。
- AC-05：OpenLLM `test_real_contract_profile.py` 通过（B 通道兼容）。
- AC-06：治理方案升至 v1.4.3 并含 §16 证据（含 P0 默认计算后缀匹配登记）；双仓三远程推送完成。
