# OpenBase 残余项整改与验证报告 v1.0.0

| 项 | 内容 |
|---|---|
| 项目 | OpenBase（开放底座） |
| 文档 | 残余项整改与验证报告 |
| 版本 | **v1.0.0** |
| 状态 | **[Approved]**（随跨仓残余项整改一并批准，2026-11-20） |
| 日期 | 2026-11-20 |
| 发布版本 | 1.5.0（本次仅测试与跨仓源码编码修正，不触发版本变更） |
| 来源 | 《OpenBase-DPS降级项后端能力补齐-测试报告-v1.0.0》§5 残余 OB-150-D01／D02 |
| 存放 | `doc/test/` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|---|---|---|---|
| v1.0.0 | 2026-11-20 | TE-OpenBase-Test | 首版：挂载扫描误报修正、跨仓 BOM 整改、定向与全量验证 |

---

## 1. 整改项

| 编号 | 问题 | 根因 | 处置 |
|---|---|---|---|
| OB-R01 | `test_s6_t1_2_no_frontend_artifact_mount_in_backend` 误报 `openbase/modules/dps_proxy/__init__.py` 命中 `mount(` | 扫描器以子串 `mount(` 判定，命中既有函数名 `dps_template_component_mount(`（非挂载调用，`main` HEAD 已存在） | 改为标识符边界正则 `(?<![A-Za-z0-9_])mount\s*\(`；`StaticFiles`／`dist-v` 仍按子串判定；补负向自检（函数名不误报） |
| OM-R01 | `test_no_python_source_has_utf8_bom_across_repos` 失败 | OpenMemory 仓 `scripts/graph_projection_worker.py` 带 UTF-8 BOM（`EF BB BF`） | 去除 BOM，代码零变更；见 OpenMemory《源码编码整改记录-v1.0.0》 |

关联项 DPS-R01（DPS 静态扫描器 f-string 未屏蔽）在 DPS 仓整改，见《DPS-残余项整改报告-v2.14.0》。

## 2. 变更文件

| 仓 | 文件 | 变更 |
|---|---|---|
| OpenBase | `tests/test_s6_t1_frontend_boundary.py` | `mount` 判定改边界正则；负向自检补函数名用例 |
| OpenMemory | `scripts/graph_projection_worker.py` | 移除文件头 BOM（17397 → 17394 字节） |
| OpenMemory | `doc/testing/OpenMemory-源码编码整改记录-v1.0.0.md` | 整改留痕 |

## 3. 验证

| 项 | 命令 | 结果 |
|---|---|---|
| S6 边界用例 | `pytest tests/test_s6_t1_frontend_boundary.py -q` | **9 passed** |
| 跨仓编码契约 | `pytest tests/test_source_encoding_contract.py -q` | **5 passed** |
| 后端全量 | `pytest tests -q -o addopts=""` | **1874 passed, 5 skipped, 0 failed**（789.73s） |
| OpenMemory 语法 | `python -m py_compile scripts/graph_projection_worker.py` | exit 0 |

证据：`doc/test/evidence/v1.5.0/openbase-backend-full-residual-fix.txt`。

## 4. 影响与回滚

- OB-R01 仅收紧测试扫描口径：真实 `app.mount(`／`StaticFiles`／`dist-v` 仍会命中，未放宽门禁；
- OM-R01 仅移除 BOM，无代码逻辑变化；
- 回滚：`git revert` 对应提交即可恢复原状。

## 5. 结论

OB-R01、OM-R01 闭环；连同 DPS-R01，三项残余全部闭环，OpenBase 后端全量零失败。
