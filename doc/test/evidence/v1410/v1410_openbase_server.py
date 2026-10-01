"""OpenBase v1.4.10 Step 4 联调用最小服务启动器（真实上游 DPS）。

用途：以真实 DPS（``127.0.0.1:8030``，v2.12.0）为上游，启动 OpenBase 应用
（``127.0.0.1:8000``），供 ``/api/v1/dps-proxy/*`` 真实上游集成检查使用。

要点：
- 仅启用联调必需模块（auth/proxy/dps_proxy/audit/tenant/config），与
  ``tests/test_dps_proxy_v1410_contract.py`` 夹具同口径；
- 上游地址与 org/tenant 映射由环境变量注入（``OPENBASE_DPS_UPSTREAM_BASE`` /
  ``OPENBASE_DPS_ORG_MAP`` / ``OPENBASE_DPS_TENANT_MAP`` / ``OPENBASE_DPS_CODE_MAP``）；
- 不发起任何 DB 迁移（不触库）；dps-proxy 出站链路不依赖本仓 DB。
"""
from __future__ import annotations

import os
from pathlib import Path

import uvicorn

REPO_ROOT = Path(__file__).resolve().parents[4]
os.chdir(REPO_ROOT)

# 默认值（可被外部环境覆盖）：真实 DPS v2.12.0 上游 + org/tenant 映射
os.environ.setdefault("OPENBASE_DPS_UPSTREAM_BASE", "http://127.0.0.1:8030")
os.environ.setdefault(
    "OPENBASE_DPS_ORG_MAP", '{"tenant-1":"dps-org-001","org-1":"dps-org-001"}'
)
os.environ.setdefault(
    "OPENBASE_DPS_TENANT_MAP", '{"tenant-1":"dps-tenant-001","org-1":"dps-tenant-001"}'
)
os.environ.setdefault(
    "OPENBASE_DPS_CODE_MAP",
    '{"schema_version":1,"source_of_truth":"openbase.tenants.code",'
    '"last_reconciled_at":"2026-10-01","entries":[{"tenant_code":"tenant-1",'
    '"dps_org_id":"dps-org-001","dps_tenant_id":"dps-tenant-001",'
    '"reconciled_at":"2026-10-01","status":"verified"}]}',
)

import openbase.settings as settings_module  # noqa: E402
from openbase import init_app  # noqa: E402
from openbase.settings import Settings  # noqa: E402

settings = Settings()
for module_name in ("auth", "proxy", "dps_proxy", "audit", "tenant", "config"):
    settings.enable_module(module_name)

# 显式绑定（防止 .env / 进程环境差异导致回落到默认上游 8000 自环）：
settings.dps_upstream_base = os.environ["OPENBASE_DPS_UPSTREAM_BASE"]
settings.dps_org_map = os.environ["OPENBASE_DPS_ORG_MAP"]
settings.dps_tenant_map = os.environ["OPENBASE_DPS_TENANT_MAP"]
settings.dps_code_map = os.environ["OPENBASE_DPS_CODE_MAP"]
settings.dps_health_check_enabled = True
settings.dps_degrade_threshold = 3

# 以本实例覆盖全局单例，供各模块 get_settings() 读取
settings_module._settings = settings

app = init_app(settings)

# 启动自证：把生效上游写入日志，便于证据核对
import logging  # noqa: E402

logging.getLogger("openbase.dps_proxy").info(
    "v1410 integration server ready: dps_upstream_base=%s org_map=%s code_map=%s",
    settings.dps_upstream_base,
    settings.dps_org_map,
    settings.dps_code_map,
)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
