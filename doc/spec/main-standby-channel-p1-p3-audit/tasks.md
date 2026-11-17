# Tasks：P0~P4 主备通道影响核查与 P1 读侧收口

- [x] T0（DPS）复核 P0 默认计算口径：`_execute_calc(person_id, None)` 回落常量、`weights=None` 回落默认权重，并在文档登记后缀匹配为有意数据面变化
- [x] T1（DPS）在 `src/engines/query_engine.py` 新增 `_prefer_unique_tags` 并接入 `get_portrait` / `get_portraits`
- [x] T2（DPS）新建 `src/tests/test_p1_read_side_tag_preference.py`，实现 3 条单测
- [x] T3（DPS）运行 P0/P1 定向测试与 `ruff`，确认无新增失败
- [x] T4（OpenLLM）运行 `tests/unit/test_real_contract_profile.py` 验证 B 通道兼容（25 passed / 1 既有基线失败）
- [x] T5（OpenBase）治理方案升 v1.4.3，新增 §16 主备通道核查结论（P0~P4）与证据
- [ ] T6（双仓）提交并推送 origin/backup/github
