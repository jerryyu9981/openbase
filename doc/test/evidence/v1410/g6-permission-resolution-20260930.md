# G6 实测证据 —— 补代理端点权限判定口径（2026-09-30）

| 项 | 内容 |
|----|------|
| **证据编号** | `E-G6-20260930` |
| **对应待验项** | D-1410-03 遗留「待实测」第 1 项：**补代理 12 端点权限点**（G6） |
| **执行人** | AA-OpenBase-Dev |
| **执行日期** | 2026-09-30 |
| **被测对象** | DPS 实现模块 `src/middleware/permission_middleware.py`（v2.11.x） |
| **取证方式** | **直接执行被测模块的真实判定函数**（非文档推断、非人工阅读）：`PermissionMiddleware._resolve_resource_type` ／ `_resolve_action` ／ `declared_action` |
| **执行环境** | `DPS/src` 源码路径注入 `sys.path`；判定为纯函数，**无需起服务与 DB** |
| **执行脚本** | `check_g6_resource_resolution.py`（临时脚本，不入仓；15 条探针） |
| **结论** | **⚠ 实测发现 3 处偏差（G6 确认 ＋ 新发现 G8／G9）**，设计侧权限映射须修正 |

---

## 1. 实测输出（原始结果，逐条）

| 方法 | 路径（DPS 侧） | **判定资源** | **判定动作** | 端点级声明 |
|:----:|----------------|:------------:|:------------:|:----------:|
| GET | `/api/v2/portrait/templates` | `portrait_template` | `read` | — |
| POST | `/api/v2/portrait/templates` | `portrait_template` | `create` | — |
| POST | `/api/v2/portrait/templates/cc-1/activate` | `portrait_template` | **`create`** | **—（无声明）** |
| POST | `/api/v2/portrait/templates/cc-1/deactivate` | `portrait_template` | **`create`** | **—（无声明）** |
| POST | `/api/v2/portrait/templates/cc-1/rollback` | `portrait_template` | `update` | `update` |
| GET | `/api/v2/portrait/templates/cc-1/diff` | `portrait_template` | `read` | — |
| GET | `/api/v2/portrait/annotation-templates` | **`portrait`** | `read` | — |
| GET | `/api/v2/portrait/annotation-templates/cc-1` | **`portrait`** | `read` | — |
| POST | `/api/v2/portrait/annotation-templates` | **`portrait`** | `create` | — |
| PUT | `/api/v2/portrait/annotation-templates/cc-1` | **`portrait`** | `update` | — |
| DELETE | `/api/v2/portrait/annotation-templates/cc-1` | **`portrait`** | `delete` | — |
| POST | `/api/v2/portrait/annotations/9/review` | `annotation_template` | `create` | — |
| GET | `/api/v2/portrait/labels` | **`portrait`** | `read` | — |
| GET | `/api/v2/portrait/lineage/tags/t1` | `annotation_template` | `read` | — |
| POST | `/api/v2/portrait/template-packages/export` | `portrait_template` | `create` | — |

---

## 2. 结论逐项

### 2.1 G6 确认：标注模板 CRUD 判定资源错位

| 端点（本版补代理 #） | 设计声明权限点 | **实测判定** | 差异 |
|---------------------|----------------|--------------|------|
| #17 `GET /annotation-templates` | `annotation_template:read` | **`portrait:read`** | ✗ 不一致 |
| #18 `GET /annotation-templates/{code}` | `annotation_template:read` | **`portrait:read`** | ✗ 不一致 |
| #19 `POST /annotation-templates` | `annotation_template:create` | **`portrait:create`** | ✗ 不一致 |
| #20 `PUT /annotation-templates/{code}` | `annotation_template:update` | **`portrait:update`** | ✗ 不一致 |
| #21 `DELETE /annotation-templates/{code}` | `annotation_template:delete` | **`portrait:delete`** | ✗ 不一致 |

**机理（实现级）**：`SUBPATH_RESOURCE_MAP` 的键为 `("portrait", "annotations")`，而实现路径的第二段是 **`annotation-templates`**；`_resolve_resource_type` 按 `(parts[2], parts[3])` **精确元组匹配** ⇒ 不命中 ⇒ 回落 `PATH_RESOURCE_MAP["portrait"]` = `portrait`。
**后果**：`annotation_template:create/update/delete` 对 **CRUD 面不可达**；仅持 `annotation_template:*` 者被拒，仅持 `portrait:*` 者可通行。

### 2.2 **新发现 G8**：模板启停判定动作为 `create`（非 `update`）

| 端点 | 设计声明（本仓 API 设计 §3.1 #15） | **实测判定** | 差异 |
|------|------------------------------------|--------------|------|
| `POST /templates/{code}/activate` | `portrait_template:update`（**端点级动作声明例外**） | **`portrait_template:create`** | ✗ **不一致** |
| `POST /templates/{code}/deactivate` | `portrait_template:update`（同上） | **`portrait_template:create`** | ✗ **不一致** |

**机理**：`ENDPOINT_ACTION_OVERRIDES` **仅含** `("POST", "/rollback") → update`，**未含** activate／deactivate ⇒ 回落 HTTP 方法映射 `POST → create`。
**后果（越权面，与已修回滚端点同构）**：**仅持 `portrait_template:create` 者可启停模板**；而按语义仅持 `portrait_template:update` 者**被拒**。
**判定**：与 DPS v2.11.0 已修的回滚端点（`TD-3027`）属**同类残留**——回滚修了，启停未修。

### 2.3 **新发现 G9**：标签管理面判定资源为 `portrait`

| 端点 | 设计声明（#22） | **实测判定** | 差异 |
|------|-----------------|--------------|------|
| `GET /labels` | `annotation_template:read` | **`portrait:read`** | ✗ 不一致 |

**机理**：`SUBPATH_RESOURCE_MAP` 无 `("portrait","labels")` 键 ⇒ 回落 `portrait`。

### 2.4 与设计一致的项（核对通过）

| 端点 | 设计声明 | 实测 | 结论 |
|------|----------|------|:----:|
| #11／#12 `templates` 读 | `portrait_template:read` | `portrait_template` + `read` | ✅ |
| #13 创建模板 | `portrait_template:create` | `portrait_template` + `create` | ✅ |
| #14 更新模板 | `portrait_template:update` | `portrait_template` + `update` | ✅ |
| #1 包导出 | `portrait_template:create` | `portrait_template` + `create` | ✅ |
| 血缘反查（#6 面） | `annotation_template:read` | `annotation_template` + `read` | ✅ |
| 版本对比（#3 面） | `portrait_template:read` | `portrait_template` + `read` | ✅ |
| 回滚（#4 面） | `portrait_template:update` | `portrait_template` + `update`（命中声明） | ✅ |

> **统计**：12 补代理端点权限映射 —— **与实测一致 4 项 ／ 不一致 3 类共 8 项**（#17~#21 五个、#15 两个、#22 一个）。
> 即 **API 设计文档 v1.2.0 §6「补代理 10/12 一致，2 项待实测」的自评口径同样失真**：实际不一致为 **3 类（涉及 8 个端点）**。

---

## 3. 影响与处置建议

| # | 影响 | 处置 | 归属 |
|:-:|------|------|------|
| 1 | 本仓 API 设计「权限动作映射」表与上游实现**逐项不符**，联调必然踩空（写操作尤其） | **按实测回写** API 设计 §3.1（标注模板 CRUD 与 `/labels` 记 `portrait:*`；启停记 `create`），并**加"以上游实测为准"的口径注** | 本仓设计（Step 2 修订） |
| 2 | **语义正确性**问题：启停按 `create` 判定属越权面；标注模板 CRUD 权限点不可达 | **跨仓派单**（扩展现有 `OB-v1.4.10-DSP-PERM-01`）：① 补键 `("portrait","annotation-templates")` ② 补声明 `("POST","/activate"｜"/deactivate") → update` ③ 补键 `("portrait","labels")`（或明确 `/labels` 归 `portrait:read` 为**有意口径**并写入契约） | **DPS 侧**（最小版本化补丁） |
| 3 | DPS 契约文档未记载上述三项判定口径 | 契约 §7 权限矩阵须补列，避免再次"文档与实现两套" | DPS 侧 |
| 4 | 本仓代理层**不自行判定权限**（透传上游裁决），故**不阻塞编码**；但**阻塞「权限对齐判据」** | 设计侧 `§6` 该判据**改为「以实测为准，差异在案」**，不得再自评一致 | 本仓设计 |

---

## 4. 固化的取证纪律（延续 C1~C4）

> **本次实测再次印证**：C1「契约核对必须『文档 ＋ 实现』双向」不可省。G6／G8／G9 三项**在 DPS 契约文档中均无异常**，**只有执行实现判定函数才暴露**。
> 追加固化 **C5**：**权限／动作映射类判据，必须以「执行实现的判定函数或端到端调用」取证，不得以文档声明或人工阅读代码代替。**
