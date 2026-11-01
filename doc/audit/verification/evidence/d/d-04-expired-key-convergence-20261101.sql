-- =============================================================================
-- D-04 存量服务 Key（ob_k_*）到期收敛：只读导出 + 分批收敛脚本
-- 版本：v1.0.0（2026-11-01） 归属：P4 批 D
-- 适用：OpenBase 控制面库（schema openbase，表 service_api_keys）
-- 安全：仅导出标识与时间字段，不导出 key_hash / 明文；UPDATE 参数化绑定
-- 执行前提：生产/准生产 DBA 会话 + 变更单；本环境无生产主机访问权，未执行
-- =============================================================================

-- 1) 只读导出：无到期时间的存量 Key（按业务分批依据）
SELECT id,
       key_id,
       name,
       status,
       scope -> 'tenants' AS scope_tenants,
       revoked_at,
       last_used_at,
       created_at
  FROM openbase.service_api_keys
 WHERE expires_at IS NULL
 ORDER BY created_at ASC, id ASC;

-- 2) 分批收敛（每批限定单租户 + 创建时间截止点；参数由 DBA 会话绑定）
--    批次划分建议：按 scope.tenants 分组，每批不超过 200 行；先跑 1) 取截止点
UPDATE openbase.service_api_keys
   SET expires_at = :batch_expires_at,
       updated_at = now()
 WHERE expires_at IS NULL
   AND status = 'active'
   AND created_at < :batch_cutoff
   AND scope -> 'tenants' @> jsonb_build_array(:tenant_code);

-- 3) 每批执行后复核（通过标准：remaining_without_expiry = 0，或仅剩已登记豁免行）
SELECT count(*) AS remaining_without_expiry
  FROM openbase.service_api_keys
 WHERE expires_at IS NULL;

-- 4) 到期提醒面联查（复用 C-08 清单端点，确认 ≤7 天 / 已过期可见）
--    GET /api/v1/auth/service-keys 到期清单由 ServiceKeyService.list_expiring 提供
--    （openbase/modules/auth/service_keys.py:249）；本脚本不改写，仅记录核对口径。

-- =============================================================================
-- 执行记录（留空待填；每批一行）
-- 批次 | 租户码 | 行数 | 截止点 | 到期时间 | 执行人 | 复核结果 | 证据文件
-- B1   |        |      |        |          |        |          |
-- B2   |        |      |        |          |        |          |
-- 豁免 | 说明已登记豁免的 key_id（须经批准并附审计摘要）
-- =============================================================================
