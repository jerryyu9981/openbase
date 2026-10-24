# OpenBase 生产环境配置下发单 - XR-OPS-07 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）跨仓生产治理 |
| 下发单编号 | XR-OPS-07-ENV-001 |
| 文档版本 | v1.0.0 |
| 状态 | **[Draft] 待 OPS 执行**（本环境无生产主机访问权，不代替生产执行） |
| 创建日期 | 2026-10-24 |
| 编制 | 研发（AI 辅助） |
| 执行方 | OPS（生产环境） |
| 上游依据 | 《OpenBase-发布强制核验执行记录-v1.0.0》§5；《OpenBase-主备双通道生产上线必办事项清单-v2.2.0》S4 |
| 唯一事实源 | `config/production_switch_matrix.json`（v1.1.0，`OpenMemory` 条目） |

---

## 1. 下发目标

| 项 | 内容 |
|----|------|
| 目标系统 | OpenMemory（生产 M2 部署） |
| 目标文件 | `<OpenMemory 生产部署目录>/.env`（**由 OPS 填写绝对路径**；源码部署默认与启动脚本同目录） |
| 变更项 | `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=true` |
| 变更原因 | 生产 M2 未置真时 `validate_identity_trust_policy` 拒绝启动；该开关是「生产强制租户域」的机械门禁 |
| 容器路径（如使用 compose） | `deployments/docker/.env`，并确认 compose 服务 `environment` 透传同名变量 |
| 影响面 | 仅 M2 生产部署；本地/单租户开发态保持模板默认 `false` 不变 |

> **禁则**：不得修改 `OpenMemory/.env.example` 的默认值（刻意保留 `false`）；不得在非生产环境强制置真。

---

## 2. 执行前检查

```bash
# 1) 确认部署模式为 M2（多租户强制）
grep -n '^OPENMEMORY_IDENTITY_MODE=' .env

# 2) 备份（必须）
cp .env ".env.bak-xrops07-$(date +%Y%m%d-%H%M%S)"

# 3) 查看当前键（可能不存在）
grep -n '^OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=' .env || echo "KEY_ABSENT"
```

---

## 3. 下发步骤

### 3.1 源码部署

```bash
# 键存在 → 覆盖值；不存在 → 追加
if grep -q '^OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=' .env; then
  sed -i 's/^OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=.*/OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=true/' .env
else
  printf '\n# XR-OPS-07: 生产 M2 强制租户域\nOPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=true\n' >> .env
fi

# 确认唯一且为 true（重复键以最后一条为准，必须只保留一条）
grep -c '^OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=' .env
grep -n '^OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=' .env
```

### 3.2 容器部署（可选路径）

1. 在 `deployments/docker/.env` 执行与 3.1 相同的追加/覆盖；
2. 确认 `docker-compose.yml` 的 OpenMemory 服务 `environment` 透传 `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=${OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE}`；
3. `docker compose up -d openmemory` 重建容器。

---

## 4. 下发核验（机械门禁，必做）

在 OpenBase 仓库检出目录执行（要求脚本与矩阵为 v1.1.0 及以上）：

```bash
python scripts/verify_production_switches.py \
  --env-file <OpenMemory 生产绝对路径>/.env \
  --repo OpenMemory \
  --json doc/test/evidence/release/switch-envfile-production-<日期>.json
```

**通过判据**：

- 控制台输出 `[PASS] OpenMemory · OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE · ...=true`；
- `合计 1 项：PASS 1 / FAIL 0`；
- 退出码 `0`。

同时建议并行核验 OpenLLM 生产 5 项（同脚本 `--repo OpenLLM`），确保整条生产门禁矩阵无缺口。

---

## 5. 服务重启与运行态确认

```bash
# 重启（按实际部署方式二选一）
systemctl restart openmemory        # systemd
# docker compose up -d openmemory   # 容器

# 健康与启动日志
curl -fsS http://127.0.0.1:<port>/health
journalctl -u openmemory -n 100 --no-pager | grep -Ei 'tenant_scope|identity_trust|refus|reject'
```

**通过判据**：`/health` 200；启动日志无 `validate_identity_trust_policy` 拒绝记录；租户域读写正常。

---

## 6. 回滚

```bash
cp ".env.bak-xrops07-<时间戳>" .env
systemctl restart openmemory        # 或 docker compose up -d openmemory
curl -fsS http://127.0.0.1:<port>/health
```

回滚后重新执行第 4 节核验，预期 `FAIL`（值为 `false`/缺失），以证明回滚生效；随后由 OPS 决定是否重新下发。

---

## 7. 执行回执（OPS 填写）

| 项 | 填写 |
|----|------|
| 执行人 / 时间 |  |
| 目标 `.env` 绝对路径 |  |
| 部署方式（源码 / 容器） |  |
| `grep` 结果（键唯一且 `true`） |  |
| `--env-file` 核验输出（含退出码） |  |
| 证据 JSON 路径 |  |
| 服务重启与 `/health` 结果 |  |
| 启动日志检查结果 |  |
| 回滚备份路径 |  |

---

## 8. 本地演练结果（非生产，已执行）

| 项 | 命令 | 结果 |
|----|------|------|
| 生产形态演练 | `verify_production_switches.py --env-file doc/test/evidence/release/openmemory.production.rehearsal.env --repo OpenMemory` | **PASS 1 / FAIL 0，exit 0**；证据 `doc/test/evidence/release/switch-envfile-rehearsal-20261024.json` |
| 本机开发 `.env` 现状 | 同上，指向 `OpenMemory/.env` | **FAIL 1（未下发该开关），exit 1**；证据 `doc/test/evidence/release/switch-envfile-local-20261024.json` |

> 演练证明「脚本 `--env-file` 模式可用 + 当前生产值尚未下发」，**不代替**生产主机执行；生产回执以第 7 节为准。

---

## 9. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-10-24 | 研发（AI 辅助） | 初始创建：OpenMemory 生产开关下发单（备份/覆盖/核验/重启/回滚/回执）；登记本地演练 PASS 与开发 `.env` 未下发 FAIL 证据；状态待 OPS 执行 |
