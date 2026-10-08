-- rbac_seed_manifest — 由 rbac_permission_seed.py 生成（幂等；可重复执行）
-- 目标系统：openllm；方言：PostgreSQL；schema：openbase
-- 生成时间：2026-10-08T15:31:04+00:00
-- 源模型：D:\Trae CN\myproject\Dev\OpenBase\config\rbac_permission_model.json
-- 幂等语义：INSERT ... ON CONFLICT DO NOTHING
--   · roles.code / permissions.code 唯一；role_permission / user_role 复合主键；
-- 执行责任：**由目标仓（OpenLLM）执行**；本脚本不连库、不写库（默认 dry-run）。
BEGIN;

-- 1) 角色（roles）
INSERT INTO "openbase"."roles" (name, code, description, is_system, created_at, updated_at) VALUES ('系统管理员', 'admin', '内置管理员角色（持 * 通配）', true, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."roles" (name, code, description, is_system, created_at, updated_at) VALUES ('组织管理员', 'org_admin', '组织级管理角色（不含角色/权限管理，裁定 D2）', true, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."roles" (name, code, description, is_system, created_at, updated_at) VALUES ('组织成员', 'org_member', '组织成员角色（只读，裁定 D1）', true, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."roles" (name, code, description, is_system, created_at, updated_at) VALUES ('普通用户', 'user', '标准业务用户角色（只读，裁定 D1）', true, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."roles" (name, code, description, is_system, created_at, updated_at) VALUES ('只读用户', 'viewer', '只读访问角色（裁定 D1）', true, now(), now()) ON CONFLICT (code) DO NOTHING;

-- 2) 权限点（permissions）
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('*', '全部权限', 'system', 3, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('app:read', 'apps·read', 'apps', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('app:write', 'apps·write', 'apps', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('app:delete', 'apps·delete', 'apps', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('billing:read', 'billing·read', 'billing', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('billing:write', 'billing·write', 'billing', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('conversation:read', 'conversations·read', 'conversations', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('conversation:write', 'conversations·write', 'conversations', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('knowledge_base:read', 'knowledge_bases·read', 'knowledge_bases', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('knowledge_base:write', 'knowledge_bases·write', 'knowledge_bases', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('knowledge_base:delete', 'knowledge_bases·delete', 'knowledge_bases', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('model:read', 'models·read', 'models', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('model:write', 'models·write', 'models', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('model:delete', 'models·delete', 'models', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('provider:read', 'providers·read', 'providers', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('provider:write', 'providers·write', 'providers', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('provider:delete', 'providers·delete', 'providers', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('role:read', 'roles·read', 'roles', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('role:write', 'roles·write', 'roles', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('role:delete', 'roles·delete', 'roles', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('role:admin', 'roles·admin', 'roles', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('tenant:read', 'tenants·read', 'tenants', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('tenant:write', 'tenants·write', 'tenants', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('usage:read', 'usage·read', 'usage', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('user:read', 'users·read', 'users', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('user:write', 'users·write', 'users', 1, now(), now()) ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at) VALUES ('user:delete', 'users·delete', 'users', 1, now(), now()) ON CONFLICT (code) DO NOTHING;

-- 3) 角色→权限（role_permission）
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = '*' WHERE r.code = 'admin' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'app:read' WHERE r.code = 'org_admin' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'billing:read' WHERE r.code = 'org_admin' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'conversation:read' WHERE r.code = 'org_admin' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'conversation:write' WHERE r.code = 'org_admin' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'knowledge_base:delete' WHERE r.code = 'org_admin' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'knowledge_base:read' WHERE r.code = 'org_admin' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'knowledge_base:write' WHERE r.code = 'org_admin' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'model:read' WHERE r.code = 'org_admin' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'provider:read' WHERE r.code = 'org_admin' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'usage:read' WHERE r.code = 'org_admin' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'user:read' WHERE r.code = 'org_admin' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'user:write' WHERE r.code = 'org_admin' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'app:read' WHERE r.code = 'org_member' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'conversation:read' WHERE r.code = 'org_member' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'knowledge_base:read' WHERE r.code = 'org_member' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'model:read' WHERE r.code = 'org_member' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'provider:read' WHERE r.code = 'org_member' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'usage:read' WHERE r.code = 'org_member' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'user:read' WHERE r.code = 'org_member' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'app:read' WHERE r.code = 'user' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'conversation:read' WHERE r.code = 'user' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'knowledge_base:read' WHERE r.code = 'user' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'model:read' WHERE r.code = 'user' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'provider:read' WHERE r.code = 'user' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'usage:read' WHERE r.code = 'user' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'user:read' WHERE r.code = 'user' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'app:read' WHERE r.code = 'viewer' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'conversation:read' WHERE r.code = 'viewer' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'knowledge_base:read' WHERE r.code = 'viewer' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'model:read' WHERE r.code = 'viewer' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'provider:read' WHERE r.code = 'viewer' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'usage:read' WHERE r.code = 'viewer' ON CONFLICT DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id) SELECT r.id, p.id FROM "openbase"."roles" AS r JOIN "openbase"."permissions" AS p ON p.code = 'user:read' WHERE r.code = 'viewer' ON CONFLICT DO NOTHING;

-- 4) 用户→角色（user_role；绑定意图，默认空）
-- （无绑定意图：由目标仓按环境补充）

COMMIT;
