# OpenBase 部署执行报告 - v1.4.4

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.4 |
| 文档版本 | v1.0.0 |
| 状态 | [Final] |
| 作者 | DO-OpenBase-Dev |
| 部署日期 | 2026-08-31 |
| 存放 | doc/operation/ |

---

## 1. 部署概况

| 项 | 内容 |
|----|------|
| 目标环境 | Dev（本机 127.0.0.1） |
| 发布版本 | v1.4.4（commit 2dde2c6，tag v1.4.4） |
| 部署方式 | 源码更新 + 服务重启（Dev 直接部署） |
| 部署结果 | ✅ 成功 |

## 2. 部署执行记录

| 步骤 | 命令/操作 | 结果 | 证据 |
|------|-----------|:---:|------|
| 1. 版本配置更新 | 更新 .devflow/project-config.json（version 1.4.4/lastRelease v1.4.4）+ state.json Step 5 | ✅ | commit 2dde2c6 |
| 2. 打 tag | `git tag v1.4.4` | ✅ | `git tag -l v1.4.4` → v1.4.4 |
| 3. 推 origin | `git push origin main --tags` | ✅ | `e6e6a1e..2dde2c6 main -> main` + `[new tag] v1.4.4` |
| 4. 推 backup | `git push backup main --tags` | ✅ | `850b2b6..2dde2c6 main -> main` + `[new tag] v1.4.4` |
| 5. 环境核验 | OpenBase 8000 / OpenRAG 8010 / 前端 5173 | ✅ | 三服务运行中 |
| 6. 服务重启 | OpenBase demo_app 重启（内存降级 admin/admin123） | ✅ | `Uvicorn running on http://127.0.0.1:8000` |

## 3. 环境核验记录（5.2）

| 项 | 结果 |
|----|:---:|
| 端口占用（8000/8010/5173） | ✅ 无冲突（OpenBase 8000 + OpenRAG 8010 + vite 5173） |
| OpenRAG 启动参数 | ✅ OPENRAG_API_PORT=8010 + 临时 SQLite 库（沙箱写限制规避） |
| 数据库迁移 | N/A（本版本无 DB 变更） |
| 环境变量 | ✅ 无真实密钥入 git（.env* 排除；rag 无 api_key） |

## 4. 构建与制品

| 项 | 结果 |
|----|:---:|
| 后端静态检查 | ✅ ruff 0 错 |
| 后端测试 | ✅ 全量通过 |
| 前端构建 | ✅ vite build 通过（dist 产物生成） |
| 制品校验 | ✅ 源码 tag v1.4.4 可追溯 |

## 5. 部署后动作

| 项 | 结果 |
|----|:---:|
| 上线验证 | ✅ 6/6（见上线检查报告） |
| 监控检查 | ✅ 服务日志无 ERROR；结构化日志（logging + extra） |
| 回滚就绪 | ✅ tag v1.4.3 可回滚（见回滚方案） |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | DO-OpenBase-Dev | 初始创建：v1.4.4 部署执行（tag 双远程推送成功 + 三服务就绪） |
