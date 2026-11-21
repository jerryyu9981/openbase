<template>
  <PageContainer title="画像模板" description="评分契约：定义维度、权重与打分规则，激活后参与画像计算；左侧分类仅用于治理" test-id="dps-template-list-view-page">
    <ConceptNav current="portrait-template" />
    <!-- 顶部状态概览 -->
    <div class="ob-metrics health-metrics" data-test="template-health-overview">
      <div class="metric">
        <div class="metric-num">{{ statusCounts.active }}</div>
        <div class="metric-label">已激活</div>
      </div>
      <div class="metric">
        <div class="metric-num">{{ statusCounts.draft }}</div>
        <div class="metric-label">草稿</div>
      </div>
      <div class="metric">
        <div class="metric-num">{{ statusCounts.inactive }}</div>
        <div class="metric-label">已停用</div>
      </div>
      <div class="metric">
        <div class="metric-num danger">{{ statusCounts.block }}</div>
        <div class="metric-label">存在阻断（BLOCK）</div>
      </div>
    </div>

    <div class="template-layout">
      <!-- 分类侧栏树 -->
      <aside class="category-pane" data-test="template-category-tree">
        <div class="category-head">
          <span>模板分类</span>
          <el-button link type="primary" size="small" data-test="category-create-root" @click="openCategoryDialog('create', null)">
            ＋新增
          </el-button>
        </div>
        <el-tree
          :data="categoryTree"
          node-key="id"
          default-expand-all
          :expand-on-click-node="false"
          empty-text="暂无分类"
          @node-click="onCategoryClick"
        >
          <template #default="scope">
            <div class="category-node">
              <span class="category-name" :class="{ active: categoryFilter === String(scope.data.id) }">{{ scope.data.name }}</span>
              <span class="category-actions" @click.stop>
                <el-button
                  link
                  size="small"
                  title="新增子分类"
                  :disabled="Number(scope.data.level) >= 3"
                  @click="openCategoryDialog('create', scope.data)"
                >
                  ＋
                </el-button>
                <el-button link size="small" title="改名" @click="openCategoryDialog('rename', scope.data)">✎</el-button>
                <el-button link size="small" title="移动" @click="openCategoryDialog('move', scope.data)">⇄</el-button>
              </span>
            </div>
          </template>
        </el-tree>
        <div class="muted sm category-tip">最多 3 层；模板只能绑定第 3 层分类。</div>
      </aside>

      <section class="template-main">
        <div class="page-toolbar">
          <el-input v-model="keyword" placeholder="搜索模板族名称 / code" clearable style="width: 220px" data-test="template-search" />
          <el-select v-model="statusFilter" placeholder="状态：全部" clearable style="width: 130px" data-test="template-status-filter">
            <el-option label="active" value="active" />
            <el-option label="inactive" value="inactive" />
            <el-option label="draft" value="draft" />
          </el-select>
          <el-select v-model="kindFilter" placeholder="类型：全部" clearable style="width: 140px" data-test="template-kind-filter">
            <el-option label="复合模板" value="composite" />
            <el-option label="子模板" value="component" />
          </el-select>
          <el-tag v-if="categoryFilter" closable size="small" data-test="template-category-active" @close="clearCategoryFilter">
            分类：{{ categoryFilterName }}
          </el-tag>
          <el-button type="primary" data-test="template-query" @click="load">查询</el-button>
          <el-button data-test="template-reset" @click="resetFilters">重置</el-button>

          <el-select
            v-model="activeViewId"
            placeholder="保存视图"
            clearable
            style="width: 160px"
            data-test="template-saved-view"
            @change="applySavedView"
          >
            <el-option v-for="view in savedViews" :key="view.id" :label="view.name" :value="view.id">
              <span>{{ view.name }}</span>
              <el-button link type="danger" size="small" class="view-remove" @click.stop="removeView(view.id)">删除</el-button>
            </el-option>
          </el-select>
          <el-button plain data-test="template-save-view" @click="saveCurrentView">保存视图</el-button>
          <el-popover trigger="click" placement="bottom-end" :width="180">
            <template #reference>
              <el-button plain data-test="template-columns">列设置</el-button>
            </template>
            <el-checkbox
              v-for="column in columns"
              :key="column.key"
              :model-value="column.visible"
              class="column-option"
              @change="toggleColumn(column.key)"
            >
              {{ column.label }}
            </el-checkbox>
          </el-popover>
          <el-button type="primary" plain data-test="template-new" @click="router.push('/portrait/dps/templates/new')">
            新建模板
          </el-button>
        </div>

        <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
          <template #title>{{ error.title }}</template>
          <div>{{ error.detail }}</div>
          <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
          <el-button v-if="error.retryable" link type="primary" size="small" data-test="dps-retry" @click="load">点击重试</el-button>
          <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
        </el-alert>

        <el-card header="模板族">
          <div class="ob-table-scroll">
            <el-table
              v-loading="loading"
              :data="filteredItems"
              stripe
              empty-text="暂无模板族"
              data-test="template-table"
            >
              <el-table-column label="画像模板" min-width="220">
                <template #default="{ row }">
                  <NameCodeLabel :name="row.name" :code="row.code" layout="stack" />
                </template>
              </el-table-column>
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="statusTagType(row.status)" size="small">{{ row.status || 'draft' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column v-if="columnVisible('category')" label="分类" width="150">
                <template #default="{ row }">
                  <span>{{ categoryNameMap[String(row.category_id || '')] || '未分类' }}</span>
                </template>
              </el-table-column>
              <el-table-column v-if="columnVisible('kind')" label="类型" width="100">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.template_kind === 'component' ? 'warning' : 'success'" effect="plain">
                    {{ row.template_kind === 'component' ? '子模板' : '复合模板' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column v-if="columnVisible('version')" label="版本" width="80">
                <template #default="{ row }">{{ formatVersion(row.version) }}</template>
              </el-table-column>
              <el-table-column label="健康度" width="210">
                <template #default="{ row }">
                  <div class="health-cell" data-test="template-health" @click="openDetail(row.code, 'overview')">
                    <el-tag v-if="healthFor(row.code).block" size="small" type="danger" data-test="template-health-block">
                      {{ healthFor(row.code).block }} BLOCK
                    </el-tag>
                    <el-tag v-if="healthFor(row.code).warn" size="small" type="warning" data-test="template-health-warn">
                      {{ healthFor(row.code).warn }} 告警
                    </el-tag>
                    <el-tag v-if="healthFor(row.code).gap" size="small" type="info" data-test="template-health-gap">
                      {{ healthFor(row.code).gap }} 缺口
                    </el-tag>
                    <el-tag v-if="healthFor(row.code).level === 'ok'" size="small" type="success" data-test="template-health-ok">健康</el-tag>
                    <span v-if="healthFor(row.code).level === 'unknown'" class="muted sm">—（待加载）</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column v-if="columnVisible('updated')" label="更新时间" width="160">
                <template #default="{ row }">{{ formatTime(row) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="150" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" data-test="template-detail" @click="openDetail(row.code, 'lineage')">
                    打开
                  </el-button>
                  <el-dropdown trigger="click" @command="(command: string) => handleRowCommand(command, row)">
                    <el-button link type="primary" size="small" data-test="template-more">更多</el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="workbench" data-test="template-workbench">工作台</el-dropdown-item>
                        <el-dropdown-item command="versions" data-test="template-versions">版本对比</el-dropdown-item>
                        <el-dropdown-item command="preflight" data-test="template-preflight">预检与影响面</el-dropdown-item>
                        <el-dropdown-item command="raw">JSON 编辑</el-dropdown-item>
                        <el-dropdown-item command="toggle" divided data-test="template-toggle">
                          {{ row.status === 'active' ? '停用' : '启用' }}
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </template>
              </el-table-column>
              <template #empty>
                <el-empty description="暂无模板族" :image-size="60" data-test="template-empty">
                  <el-button type="primary" size="small" @click="router.push('/portrait/dps/templates/new')">新建模板</el-button>
                </el-empty>
              </template>
            </el-table>
          </div>
        </el-card>
      </section>
    </div>

    <!-- 分类管理弹窗 -->
    <el-dialog v-model="categoryDialog.open" :title="categoryDialogTitle" width="520px" data-test="category-dialog">
      <el-form label-width="90px">
        <el-form-item v-if="categoryDialog.mode !== 'move'" label="名称 *">
          <el-input v-model="categoryDialog.name" placeholder="如：人物画像" data-test="category-name" />
        </el-form-item>
        <el-form-item v-if="categoryDialog.mode === 'create'" label="编码 *">
          <el-input v-model="categoryDialog.code" placeholder="如：person-profile" data-test="category-code" />
        </el-form-item>
        <el-form-item v-if="categoryDialog.mode !== 'rename'" label="父分类">
          <el-select v-model="categoryDialog.parent_id" clearable placeholder="留空 = 根节点" style="width: 260px" data-test="category-parent">
            <el-option
              v-for="item in parentCandidates"
              :key="item.id"
              :label="`${'　'.repeat(Math.max(0, Number(item.level) - 1))}${item.name}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <p class="muted sm">最多 3 层；编码创建后不可修改；模板只能绑定第 3 层分类。</p>
      <template #footer>
        <el-button @click="categoryDialog.open = false">取消</el-button>
        <el-button type="primary" data-test="category-submit" @click="submitCategory">确认</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉（概览 / 族谱 / 标注模板 / 标签产出 / 评分项 / 版本与预检） -->
    <el-drawer v-model="detailOpen" title="模板族详情" size="880px" data-test="template-detail-drawer">
      <div class="detail-head">
        <NameCodeLabel :name="detail?.name" :code="detail?.code" layout="stack" />
        <el-tag size="small" :type="statusTagType(detail?.status)">{{ detail?.status || 'draft' }}</el-tag>
        <el-tag v-if="detailHealth?.block" size="small" type="danger">{{ detailHealth.block }} BLOCK</el-tag>
        <el-tag v-if="detailHealth?.warn" size="small" type="warning">{{ detailHealth.warn }} 告警</el-tag>
        <el-tag v-if="detailHealth?.gap" size="small" type="info">{{ detailHealth.gap }} 缺口</el-tag>
      </div>

      <div v-loading="lineageLoading" class="mt-12">
        <el-alert
          v-if="lineage?.gaps?.items?.length"
          type="warning"
          show-icon
          :closable="false"
          class="mb-12"
          data-test="template-lineage-gaps"
        >
          <template #title>发现 {{ (lineage?.gaps?.items || []).length }} 项配置缺口</template>
          <div v-for="item in lineage?.gaps?.items || []" :key="`${item.type}-${item.code || ''}`" class="gap-line">
            {{ item.message }}
          </div>
        </el-alert>

        <el-tabs v-model="detailTab" data-test="template-lineage-tabs" @tab-change="onDetailTabChange">
          <!-- ① 概览 + 健康度问题清单 -->
          <el-tab-pane label="概览" name="overview" data-test="template-tab-overview">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="模板名称">{{ detail?.name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="模板码">{{ detail?.code || '-' }}</el-descriptions-item>
              <el-descriptions-item label="状态">{{ detail?.status || '-' }}</el-descriptions-item>
              <el-descriptions-item label="version">{{ formatVersion(detail?.version) }}</el-descriptions-item>
              <el-descriptions-item label="profile_type">{{ detail?.profile_type || '-' }}</el-descriptions-item>
              <el-descriptions-item label="subject_type">{{ detail?.subject_type || '-' }}</el-descriptions-item>
              <el-descriptions-item label="extends">{{ detail?.extends || '—（无继承）' }}</el-descriptions-item>
              <el-descriptions-item label="description">{{ detail?.description || '-' }}</el-descriptions-item>
            </el-descriptions>

            <div class="mt-16">
              <div class="section-title">健康度问题（{{ detailHealth?.issues.length || 0 }} 项）</div>
              <el-empty v-if="!detailHealth?.issues.length" description="未发现健康度问题" :image-size="48" />
              <div v-for="(issue, index) in detailHealth?.issues || []" :key="index" class="health-issue" data-test="template-health-issue">
                <el-tag size="small" :type="issue.level === 'block' ? 'danger' : 'warning'">
                  {{ issue.level === 'block' ? 'BLOCK' : 'WARN' }}
                </el-tag>
                <el-tag size="small" type="info" effect="plain">{{ issue.source === 'scoring' ? '口径' : '缺口' }}</el-tag>
                <span class="health-issue-text">{{ issue.message }}</span>
                <el-button link type="primary" size="small" data-test="template-health-fix" @click="goFixIssue(issue.source, issue.code)">
                  去修复
                </el-button>
              </div>
            </div>

            <div class="mt-16 detail-actions">
              <el-button size="small" data-test="template-edit" @click="router.push(`/portrait/dps/templates/${detail?.code}/edit`)">工作台</el-button>
              <el-button size="small" @click="router.push(`/portrait/dps/templates/${detail?.code}/versions`)">版本对比</el-button>
              <el-button size="small" @click="router.push(`/portrait/dps/templates/${detail?.code}/preflight`)">预检页</el-button>
              <el-button size="small" @click="router.push(`/portrait/dps/templates/${detail?.code}/raw`)">JSON 编辑</el-button>
            </div>
          </el-tab-pane>

          <!-- ② 族谱 -->
          <el-tab-pane label="族谱" name="lineage" data-test="template-tab-lineage">
            <el-empty v-if="!lineage?.lineage?.length" description="暂无族谱数据" :image-size="48" />
            <div v-else class="lineage-chain">
              <div
                v-for="node in lineage?.lineage || []"
                :key="node.code"
                class="lineage-node"
                :class="{ current: node.current }"
                data-test="template-lineage-node"
              >
                <el-tag size="small" :type="node.current ? 'success' : 'info'">
                  {{ node.current ? '当前模板' : `父级 ${node.depth}` }}
                </el-tag>
                <NameCodeLabel :name="node.name" :code="node.code" />
                <el-tag size="small" :type="statusTagType(node.status)">{{ node.status || 'draft' }}</el-tag>
              </div>
              <div class="muted sm mt-8">
                继承口径：父维度先入 → 子覆盖同名 → 追加新维度；深度上限 2 层。
              </div>
            </div>
          </el-tab-pane>

          <!-- ③ 标注模板 -->
          <el-tab-pane label="标注模板" name="annotations" data-test="template-tab-annotations">
            <el-table :data="lineage?.annotation_templates || []" size="small" empty-text="暂无标注模板">
              <el-table-column label="标注模板" min-width="200">
                <template #default="{ row }">
                  <NameCodeLabel :name="row.name" :code="row.code" layout="stack" />
                </template>
              </el-table-column>
              <el-table-column label="归属画像模板" min-width="170">
                <template #default="{ row }">
                  <NameCodeLabel :name="templateNameMap[row.owned_by || '']" :code="row.owned_by" />
                  <el-tag
                    v-if="row.owned_by && row.owned_by !== lineage?.template_code"
                    size="small"
                    type="warning"
                    class="ml-6"
                    data-test="template-ownership-mismatch-tag"
                  >
                    归属不一致
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="当前模板绑定维度" min-width="150">
                <template #default="{ row }">
                  <span v-if="row.bound_to_current">{{ (row.bound_dimensions || []).join('、') || '-' }}</span>
                  <span v-else class="muted">未绑定</span>
                </template>
              </el-table-column>
              <el-table-column label="标签产出" width="100">
                <template #default="{ row }">{{ (row.tag_outputs || []).length }}</template>
              </el-table-column>
              <el-table-column label="缺口" width="120">
                <template #default="{ row }">
                  <el-tag v-if="row.unbound" size="small" type="danger" data-test="template-unbound-tag">未绑定</el-tag>
                  <span v-else class="muted sm">—</span>
                </template>
              </el-table-column>
            </el-table>
            <div v-if="lineage?.gaps?.bound_annotation_templates_missing?.length" class="muted sm mt-8">
              绑定了不存在的标注模板：{{ (lineage?.gaps?.bound_annotation_templates_missing || []).join('、') }}
            </div>
          </el-tab-pane>

          <!-- ④ 标签产出 -->
          <el-tab-pane label="标签产出" name="tags" data-test="template-tab-tags">
            <el-table :data="tagRows" size="small" empty-text="当前模板绑定的标注模板没有标签产出">
              <el-table-column label="标注模板" min-width="190">
                <template #default="{ row }">
                  <NameCodeLabel :name="row.annotation_name" :code="row.annotation" />
                </template>
              </el-table-column>
              <el-table-column prop="tag_code" label="标签（dimension:tag_key）" min-width="190" />
              <el-table-column prop="field_key" label="字段" min-width="140" />
              <el-table-column label="评分项命中" min-width="240">
                <template #default="{ row }">
                  <span v-if="row.hits.length" class="hit-text">
                    <span v-for="hit in row.hits" :key="hit.rule_key" class="hit-item">
                      {{ hit.rule_key }}（权重 {{ hit.weight }}）
                    </span>
                  </span>
                  <el-tag v-else size="small" type="warning" data-test="template-tag-only-tag">仅标签·不影响评分</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- ⑤ 评分项 -->
          <el-tab-pane label="评分项" name="scoring" data-test="template-tab-scoring">
            <div class="policy-summary mb-12" data-test="template-policy-summary">
              <el-tag
                size="small"
                :type="evidencePolicy?.require_source ? 'warning' : 'info'"
                data-test="template-evidence-policy"
              >
                证据来源：{{ evidencePolicy?.require_source ? '审核前必填' : '可选' }}
              </el-tag>
              <el-tag size="small" type="info" data-test="template-review-levels">
                审核级数：{{ reviewLevels }}
              </el-tag>
              <el-tag size="small" type="info" data-test="template-anomaly-rule-count">
                异常规则：{{ anomalyRuleCount }} 条
              </el-tag>
            </div>
            <el-empty v-if="!scoring" description="模板未激活，无运行时评分口径" :image-size="48" />
            <template v-else>
              <div class="muted sm mb-8">
                共 {{ scoring?.dimension_count }} 个维度 / {{ scoring?.rule_count }} 条规则；缺值按 50 分计。
              </div>
              <el-alert
                v-if="scoring?.dimensions_without_annotation_source?.length"
                type="warning"
                show-icon
                :closable="false"
                class="mb-12"
                data-test="template-scoring-gap"
                :title="`以下维度暂无标注来源：${(scoring?.dimensions_without_annotation_source || []).join('、')}`"
              />
              <div v-for="dim in scoring?.dimensions || []" :key="dim.code" class="scoring-dim">
                <div class="scoring-dim-head">
                  <strong>{{ dim.name }}</strong>
                  <span class="muted sm">{{ dim.code }} · 权重 {{ dim.weight }}</span>
                  <el-tag v-if="dim.source_gap" size="small" type="danger" data-test="template-dimension-gap-tag">无标注来源</el-tag>
                  <el-tag v-for="source in dim.annotation_sources || []" :key="source" size="small" type="success">
                    来源 {{ source }}
                  </el-tag>
                </div>
                <el-table :data="dim.rules" size="small">
                  <el-table-column prop="tag_key" label="tag_key" min-width="150" />
                  <el-table-column prop="description" label="说明" min-width="160" show-overflow-tooltip />
                  <el-table-column prop="type" label="类型" width="120" />
                  <el-table-column prop="weight" label="权重" width="80" />
                  <el-table-column label="缺值" width="80">
                    <template #default>50</template>
                  </el-table-column>
                </el-table>
              </div>
            </template>
          </el-tab-pane>

          <!-- ⑥ 版本与预检 -->
          <el-tab-pane label="版本与预检" name="preflight" data-test="template-tab-preflight">
            <el-descriptions :column="2" border size="small" class="mb-12">
              <el-descriptions-item label="当前版本">{{ formatVersion(detail?.version) }}</el-descriptions-item>
              <el-descriptions-item label="extends">{{ detail?.extends || '—（无继承）' }}</el-descriptions-item>
            </el-descriptions>
            <div class="detail-actions mb-12">
              <el-button size="small" @click="router.push(`/portrait/dps/templates/${detail?.code}/versions`)">版本对比与回滚</el-button>
              <el-button size="small" :loading="preflightLoading" data-test="template-preflight-run" @click="loadPreflight">执行预检</el-button>
            </div>

            <div v-loading="preflightLoading">
              <el-empty v-if="!preflight" description="尚未执行预检" :image-size="48" />
              <template v-else>
                <div class="section-title">校验项</div>
                <el-table :data="preflightChecks" size="small" :empty-text="'无校验项'">
                  <el-table-column prop="item" label="校验项" min-width="200" />
                  <el-table-column label="结果" width="100">
                    <template #default="{ row }">
                      <el-tag size="small" :type="row.passed ? 'success' : 'danger'">{{ row.passed ? '通过' : '未通过' }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="detail" label="说明" min-width="220" show-overflow-tooltip />
                </el-table>

                <div class="section-title mt-12">
                  口径一致性（{{ preflightBlock }} BLOCK / {{ preflightWarn }} WARN）
                </div>
                <el-table :data="preflightIssues" size="small" empty-text="评分口径一致">
                  <el-table-column label="级别" width="80">
                    <template #default="{ row }">
                      <el-tag size="small" :type="row.severity === 'BLOCK' ? 'danger' : 'warning'">{{ row.severity }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="code" label="问题码" min-width="180" show-overflow-tooltip />
                  <el-table-column prop="tag_code" label="标签" min-width="140" show-overflow-tooltip />
                  <el-table-column prop="message" label="说明" min-width="220" show-overflow-tooltip />
                </el-table>

                <div class="section-title mt-12">影响面</div>
                <div class="ob-metrics">
                  <div class="metric">
                    <div class="metric-num">{{ preflightImpact.annotation_template_count ?? '—' }}</div>
                    <div class="metric-label">受影响标注模板</div>
                  </div>
                  <div class="metric">
                    <div class="metric-num">{{ preflightImpact.annotation_count ?? '—' }}</div>
                    <div class="metric-label">受影响标注</div>
                  </div>
                  <div class="metric">
                    <div class="metric-num">{{ preflightImpact.tag_count ?? '—' }}</div>
                    <div class="metric-label">受影响标签</div>
                  </div>
                </div>
              </template>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import ConceptNav from '../components/ConceptNav.vue'
import NameCodeLabel from '@/components/common/NameCodeLabel.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  dpsApi,
  type DpsPortraitTemplate,
  type DpsPreflightResult,
  type DpsScoringIssue,
  type DpsTemplateCategory,
  type DpsTemplateLineage,
} from '@/core/api/dps'
import { describeDpsError } from '@/core/api/error'
import { useAsyncState } from '@/core/composables/useAsyncState'
import { formatVersion } from '@/modules/portrait/version'
import { useDpsListView } from '../composables/useDpsListView'
import {
  buildTemplateHealth,
  groupScoringIssuesByTemplate,
  type TemplateHealth,
  type TemplateHealthIssue,
} from '../templates/health'

type CategoryDialogMode = 'create' | 'rename' | 'move'

const route = useRoute()
const router = useRouter()
const keyword = ref('')
const statusFilter = ref('')
const categoryFilter = ref('')
const kindFilter = ref('')
const categories = ref<DpsTemplateCategory[]>([])
const categoryTree = ref<DpsTemplateCategory[]>([])
const detailOpen = ref(false)
const detail = ref<DpsPortraitTemplate | null>(null)
/** 默认族谱页签，保持既有深链与 e2e 行为不变 */
const detailTab = ref('lineage')
const lineage = ref<DpsTemplateLineage | null>(null)
const lineageLoading = ref(false)
const preflight = ref<DpsPreflightResult | null>(null)
const preflightLoading = ref(false)
const scoringIssuesByTemplate = ref<Record<string, DpsScoringIssue[]>>({})
const lineageByCode = ref<Record<string, DpsTemplateLineage | null>>({})

const categoryDialog = reactive({
  open: false,
  mode: 'create' as CategoryDialogMode,
  target: null as DpsTemplateCategory | null,
  name: '',
  code: '',
  parent_id: '',
})

const {
  savedViews,
  activeViewId,
  columns,
  saveView,
  removeView,
  applyView,
  toggleColumn,
  columnVisible,
} = useDpsListView({
  pageKey: 'templates',
  columns: [
    { key: 'category', label: '分类' },
    { key: 'kind', label: '类型' },
    { key: 'version', label: '版本' },
    { key: 'updated', label: '更新时间' },
  ],
})

const { data, loading, error, run } = useAsyncState<{ items: DpsPortraitTemplate[]; total?: number }>()

const filteredItems = computed(() => data.value?.items || [])

const categoryNameMap = computed<Record<string, string>>(() => {
  const map: Record<string, string> = {}
  for (const item of categories.value) map[item.id] = item.name
  return map
})

const categoryFilterName = computed(() => categoryNameMap.value[categoryFilter.value] || categoryFilter.value)

const parentCandidates = computed(() => {
  const target = categoryDialog.target
  return categories.value.filter((item) => {
    if (Number(item.level) >= 3) return false
    if (!target) return true
    if (item.id === target.id) return false
    const path = String(item.path || '')
    const targetPath = String(target.path || '')
    if (path === targetPath) return false
    if (targetPath && path.startsWith(`${targetPath}/`)) return false
    return true
  })
})

const categoryDialogTitle = computed(() => {
  if (categoryDialog.mode === 'rename') return `重命名分类：${categoryDialog.target?.name || ''}`
  if (categoryDialog.mode === 'move') return `移动分类：${categoryDialog.target?.name || ''}`
  return categoryDialog.target ? `新增子分类（父：${categoryDialog.target.name}）` : '新增根分类'
})

const templateNameMap = computed<Record<string, string>>(() => {
  const map: Record<string, string> = {}
  for (const item of data.value?.items || []) {
    if (item.code && item.name) map[item.code] = item.name
  }
  return map
})

const scoring = computed(() => lineage.value?.scoring || null)
const evidencePolicy = computed(() => detail.value?.evidence_policy || null)
const reviewLevels = computed(() => evidencePolicy.value?.review_levels ?? 1)
const anomalyRuleCount = computed(() => {
  const rules = detail.value?.anomaly_rules
  return Array.isArray(rules) ? rules.length : 0
})
const tagRows = computed(() =>
  (lineage.value?.annotation_templates || []).flatMap((view) =>
    view.tag_outputs.map((output) => ({
      annotation: view.code,
      annotation_name: view.name,
      tag_code: output.tag_code,
      field_key: output.field_key,
      hits: view.scoring_hits.filter((hit) => hit.tag_code === output.tag_code),
    })),
  ),
)

const statusCounts = computed(() => {
  const counts = { active: 0, draft: 0, inactive: 0, block: 0 }
  for (const item of data.value?.items || []) {
    const status = String(item.status || 'draft')
    if (status === 'active') counts.active += 1
    else if (status === 'inactive') counts.inactive += 1
    else counts.draft += 1
    if (healthFor(item.code).block > 0) counts.block += 1
  }
  return counts
})

const detailHealth = computed<TemplateHealth | null>(() => {
  if (!detail.value) return null
  return buildTemplateHealth({
    scoringIssues: scoringIssuesByTemplate.value[detail.value.code] || [],
    lineage: lineage.value,
    loaded: !!lineage.value,
  })
})

const preflightChecks = computed(() => preflight.value?.checks || [])
const preflightIssues = computed(() => preflight.value?.scoring_consistency?.issues || [])
const preflightBlock = computed(() => Number(preflight.value?.scoring_consistency?.block || 0))
const preflightWarn = computed(() => Number(preflight.value?.scoring_consistency?.warn || 0))
const preflightImpact = computed(() => preflight.value?.impact || {})

function statusTagType(status?: string | null): 'success' | 'info' | 'warning' {
  if (status === 'active') return 'success'
  if (status === 'inactive') return 'info'
  return 'warning'
}

function formatTime(row: DpsPortraitTemplate): string {
  const raw = row.updated_at ?? row.update_time ?? row.updated_time
  if (!raw) return '—'
  const date = new Date(String(raw))
  return Number.isNaN(date.getTime()) ? String(raw) : date.toLocaleString()
}

function healthFor(code: string): TemplateHealth {
  const loaded = Object.prototype.hasOwnProperty.call(lineageByCode.value, code)
  return buildTemplateHealth({
    scoringIssues: scoringIssuesByTemplate.value[code] || [],
    lineage: lineageByCode.value[code] || null,
    loaded,
  })
}

async function runWithConcurrency<T>(items: T[], limit: number, task: (item: T) => Promise<void>) {
  let cursor = 0
  const size = Math.min(limit, items.length)
  const workers = Array.from({ length: size }, async () => {
    while (cursor < items.length) {
      const index = cursor
      cursor += 1
      await task(items[index])
    }
  })
  await Promise.all(workers)
}

/** 健康度 = 口径问题（治理报告按模板归组）+ 血缘缺口（逐模板拉取，失败保持未知） */
async function loadHealth() {
  const items = filteredItems.value.slice(0, 30)
  const report = await dpsApi.getScoringConsistency({ limit: 100 }).catch(() => null)
  scoringIssuesByTemplate.value = groupScoringIssuesByTemplate(report?.issues || [])
  const codes = items.map((item) => item.code).filter(Boolean)
  await runWithConcurrency(codes, 4, async (code) => {
    if (Object.prototype.hasOwnProperty.call(lineageByCode.value, code)) return
    const result = await dpsApi.getTemplateLineage(code).catch(() => null)
    if (result) lineageByCode.value = { ...lineageByCode.value, [code]: result }
  })
}

async function load() {
  await run(() =>
    dpsApi.listTemplates({
      status: statusFilter.value || undefined,
      keyword: keyword.value.trim() || undefined,
      category_id: categoryFilter.value || undefined,
      template_kind: kindFilter.value || undefined,
    }),
  )
  await loadHealth()
}

async function loadCategories() {
  try {
    const [flat, tree] = await Promise.all([dpsApi.listTemplateCategories(), dpsApi.getTemplateCategoryTree()])
    categories.value = flat
    categoryTree.value = tree
  } catch {
    categories.value = []
    categoryTree.value = []
  }
}

function currentFilters(): Record<string, string> {
  return {
    keyword: keyword.value,
    status: statusFilter.value,
    category: categoryFilter.value,
    kind: kindFilter.value,
  }
}

async function saveCurrentView() {
  try {
    const { value } = await ElMessageBox.prompt('为当前筛选条件命名（同名覆盖）', '保存视图', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputPattern: /\S+/,
      inputErrorMessage: '名称不能为空',
    })
    saveView(value, currentFilters())
    ElMessage.success('视图已保存')
  } catch {
    // 用户取消
  }
}

function applySavedView(id?: string) {
  if (!id) return
  const filters = applyView(id)
  if (!filters) return
  keyword.value = filters.keyword || ''
  statusFilter.value = filters.status || ''
  categoryFilter.value = filters.category || ''
  kindFilter.value = filters.kind || ''
  void load()
}

function onCategoryClick(node: DpsTemplateCategory) {
  categoryFilter.value = String(node.id)
  void load()
}

function clearCategoryFilter() {
  categoryFilter.value = ''
  void load()
}

function resetFilters() {
  keyword.value = ''
  statusFilter.value = ''
  categoryFilter.value = ''
  kindFilter.value = ''
  activeViewId.value = ''
  void load()
}

function openCategoryDialog(mode: CategoryDialogMode, node: DpsTemplateCategory | null) {
  categoryDialog.mode = mode
  categoryDialog.target = node
  categoryDialog.name = node?.name || ''
  categoryDialog.code = ''
  categoryDialog.parent_id = mode === 'create' ? node?.id || '' : node?.parent_id || ''
  categoryDialog.open = true
}

async function submitCategory() {
  try {
    if (categoryDialog.mode === 'create') {
      if (!categoryDialog.name.trim() || !categoryDialog.code.trim()) {
        ElMessage.warning('名称与编码必填')
        return
      }
      await dpsApi.createTemplateCategory({
        code: categoryDialog.code.trim(),
        name: categoryDialog.name.trim(),
        parent_id: categoryDialog.parent_id || null,
      })
      ElMessage.success('分类已创建')
    } else if (categoryDialog.mode === 'rename') {
      if (!categoryDialog.target || !categoryDialog.name.trim()) {
        ElMessage.warning('名称必填')
        return
      }
      await dpsApi.updateTemplateCategory(categoryDialog.target.id, { name: categoryDialog.name.trim() })
      ElMessage.success('分类已重命名')
    } else {
      if (!categoryDialog.target) return
      await dpsApi.moveTemplateCategory(categoryDialog.target.id, categoryDialog.parent_id || null)
      ElMessage.success('分类已移动')
    }
    categoryDialog.open = false
    await Promise.all([loadCategories(), load()])
  } catch (caught) {
    const presentation = describeDpsError(caught)
    ElMessage.error(presentation.hint || presentation.title)
  }
}

async function openDetail(code: string, tab = 'lineage') {
  detailOpen.value = true
  detail.value = null
  lineage.value = null
  preflight.value = null
  detailTab.value = tab
  lineageLoading.value = true
  try {
    const [template, lineageData] = await Promise.all([
      dpsApi.getTemplate(code),
      dpsApi.getTemplateLineage(code).catch(() => null),
    ])
    detail.value = template
    lineage.value = lineageData
    if (lineageData) lineageByCode.value = { ...lineageByCode.value, [code]: lineageData }
    if (tab === 'preflight') await loadPreflight()
  } catch (caught) {
    error.value = describeDpsError(caught)
  } finally {
    lineageLoading.value = false
  }
}

async function loadPreflight() {
  const code = detail.value?.code
  if (!code) return
  preflightLoading.value = true
  try {
    preflight.value = await dpsApi.preflightTemplate(code)
  } catch (caught) {
    preflight.value = null
    ElMessage.error(describeDpsError(caught).title)
  } finally {
    preflightLoading.value = false
  }
}

function onDetailTabChange(name: string | number) {
  if (name === 'preflight' && detail.value?.code && !preflight.value) void loadPreflight()
}

function goFixIssue(source: TemplateHealthIssue['source'], code?: string) {
  if (source === 'scoring') {
    router.push(`/portrait/dps/scoring-consistency?template=${encodeURIComponent(detail.value?.code || '')}`)
    return
  }
  if (code) {
    router.push(`/portrait/dps/annotation-templates/${encodeURIComponent(code)}/fields`)
    return
  }
  router.push(`/portrait/dps/templates/${detail.value?.code}/edit`)
}

function handleRowCommand(command: string, row: DpsPortraitTemplate) {
  if (command === 'workbench') router.push(`/portrait/dps/templates/${row.code}/edit`)
  else if (command === 'versions') router.push(`/portrait/dps/templates/${row.code}/versions`)
  else if (command === 'preflight') router.push(`/portrait/dps/templates/${row.code}/preflight`)
  else if (command === 'raw') router.push(`/portrait/dps/templates/${row.code}/raw`)
  else if (command === 'toggle') void toggleStatus(row)
}

async function toggleStatus(row: DpsPortraitTemplate) {
  const next = row.status === 'active' ? 'inactive' : 'active'
  const action = next === 'active' ? '启用' : '停用'
  try {
    await ElMessageBox.confirm(`确认${action}模板 ${row.code}？`, '启停确认', {
      type: 'warning',
      confirmButtonText: `确认${action}`,
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    if (row.status === 'active') {
      // T-DM-01：停用后回显受影响标注模板数 / 门禁状态
      const deactivated = await dpsApi.deactivateTemplate(row.code)
      const affected = Number(deactivated.affected_annotation_templates ?? 0)
      ElMessage.success(`模板已${action}`)
      if (affected > 0) {
        ElMessage.warning(`将影响 ${affected} 个标注模板的提交（父模板停用门禁）`)
      }
      if (deactivated.parent_gate_enforced === false) {
        ElMessage.info('父模板停用门禁当前已关闭（DPS_ENFORCE_ACTIVE_PARENT=false）')
      }
    } else {
      await dpsApi.activateTemplate(row.code)
      ElMessage.success(`模板已${action}`)
    }
    await load()
    if (detailOpen.value && detail.value?.code === row.code) await openDetail(row.code, detailTab.value)
  } catch (caught) {
    const presentation = describeDpsError(caught)
    ElMessage.error(presentation.hint || presentation.title)
    // 幂等：失败后就地刷新，保持列表与实际状态一致
    await load()
  }
}

onMounted(() => {
  void load()
  void loadCategories()
  const openCode = String(route.query.open || '')
  if (openCode) void openDetail(openCode, String(route.query.tab || 'overview'))
})
</script>

<style scoped>
.health-metrics { margin-bottom: 16px; }
.health-metrics .metric-num.danger { color: var(--ob-danger); }
.template-layout { display: flex; gap: 16px; align-items: flex-start; }
.category-pane {
  flex: 0 0 230px;
  border: 1px solid var(--ob-border);
  border-radius: var(--ob-radius-md);
  padding: 10px;
  position: sticky;
  top: 12px;
}
.category-head { display: flex; align-items: center; justify-content: space-between; font-weight: 600; margin-bottom: 8px; }
.category-node { display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 6px; }
.category-name { font-size: 13px; }
.category-name.active { color: var(--ob-primary); font-weight: 600; }
.category-actions { display: none; gap: 0; }
.category-node:hover .category-actions { display: inline-flex; }
.category-tip { margin-top: 8px; line-height: 1.6; }
.template-main { flex: 1 1 auto; min-width: 0; }
.view-remove { margin-left: 8px; }
.column-option { display: flex; margin: 4px 0; }
.health-cell { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; cursor: pointer; }
.detail-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.detail-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.section-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.health-issue { display: flex; align-items: center; gap: 6px; padding: 6px 0; border-bottom: 1px dashed var(--ob-border); }
.health-issue-text { flex: 1 1 auto; font-size: 13px; }
.mb-16 { margin-bottom: 16px; }
.mb-12 { margin-bottom: 12px; }
.mb-8 { margin-bottom: 8px; }
.mt-12 { margin-top: 12px; }
.mt-16 { margin-top: 16px; }
.mt-8 { margin-top: 8px; }
.ml-6 { margin-left: 6px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; }
.gap-line { font-size: 12px; line-height: 1.7; color: var(--ob-text-secondary); }
.lineage-chain { display: flex; flex-direction: column; gap: 8px; }
.lineage-node { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border: 1px solid var(--ob-border, #e5e7eb); border-radius: 8px; }
.lineage-node.current { border-color: var(--ob-primary); background: var(--ob-primary-lighter, #f8fbff); }
.scoring-dim { margin-bottom: 14px; }
.policy-summary { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.scoring-dim-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.hit-text { display: inline-flex; flex-direction: column; gap: 2px; font-size: 12px; }
</style>
