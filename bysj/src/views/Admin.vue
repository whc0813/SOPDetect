<template>
  <div class="admin-layout">
    <AppBlobs />

    <!-- Sidebar backdrop (mobile) -->
    <div :class="['sidebar-backdrop', { 'is-open': sidebarOpen }]" @click="sidebarOpen = false"></div>

    <!-- Sidebar -->
    <aside :class="['sidebar', { 'is-open': sidebarOpen }]">
      <div class="brand">
        <div class="brand-logo">
          <el-icon><Monitor /></el-icon>
        </div>
        <span>标准行为识别</span>
      </div>

      <nav class="nav-menu">
        <button :class="['nav-item', { active: activeMenu === 'manage' }]" @click="handleMenuSelect('manage')">
          <span class="nav-icon-wrap icon-blue"><el-icon><Document /></el-icon></span>
          <span>SOP 管理</span>
        </button>
        <button :class="['nav-item', { active: activeMenu === 'users' }]" @click="handleMenuSelect('users')">
          <span class="nav-icon-wrap icon-purple"><el-icon><SwitchButton /></el-icon></span>
          <span>用户管理</span>
        </button>
        <button :class="['nav-item', { active: activeMenu === 'stats' }]" @click="handleMenuSelect('stats')">
          <span class="nav-icon-wrap icon-orange"><el-icon><DataLine /></el-icon></span>
          <span>数据统计</span>
        </button>
      </nav>

      <div class="sidebar-bottom">
        <div class="user-card">
          <div class="avatar">{{ userInitials }}</div>
          <span class="username">{{ currentUserName }}</span>
        </div>
        <button class="logout-btn" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          退出登录
        </button>
      </div>
    </aside>

    <!-- Main Area -->
    <div class="main-container">
      <header class="top-header">
        <button class="hamburger-btn" @click="sidebarOpen = !sidebarOpen">
          <el-icon><Fold /></el-icon>
        </button>
        <div class="header-left">
          <h2>{{ panelHeaderTitle }}</h2>
          <p class="header-subtitle">{{ panelHeaderSubtitle }}</p>
        </div>
        <div class="header-right">
          <button class="pill-btn" @click="openConfigDialog">API 配置</button>
          <button v-if="activeMenu === 'stats' || activeMenu === 'users'" class="pill-btn" @click="reloadCurrentView">刷新数据</button>
          <button v-if="activeMenu === 'manage'" class="pill-btn primary-pill" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>
            新建 SOP
          </button>
        </div>
      </header>

      <main class="content-area">

        <!-- SOP 管理 -->
        <GroupedList
          v-if="activeMenu === 'manage'"
          :columns="sopColumns"
          :data="sopList"
          empty-text="暂无 SOP"
        >
          <template #cell-stepCount="{ value }">
            <StatusBadge type="default">{{ value }}</StatusBadge>
          </template>
          <template #cell-actions="{ row }">
            <button class="text-btn" @click="openDebugSop(row)">查看</button>
            <button class="text-btn danger" @click="deleteCurrentSop(row)">删除</button>
          </template>
        </GroupedList>

        <!-- 用户管理 -->
        <GroupedList
          v-else-if="activeMenu === 'users'"
          :columns="userColumns"
          :data="userList"
          empty-text="暂无用户"
        >
          <template #cell-role="{ row }">
            <StatusBadge :type="row.role === 'admin' ? 'danger' : 'default'">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </StatusBadge>
          </template>
          <template #cell-status="{ row }">
            <StatusBadge :type="row.status === 'active' ? 'success' : 'warning'">
              {{ row.status === 'active' ? '启用' : '禁用' }}
            </StatusBadge>
          </template>
          <template #cell-actions="{ row }">
            <button
              class="text-btn"
              :disabled="row.role === 'admin' && row.id === currentUser?.id"
              @click="toggleUserStatus(row)"
            >{{ row.status === 'active' ? '禁用' : '启用' }}</button>
          </template>
        </GroupedList>

        <!-- 数据统计 -->
        <div v-else class="stats-view">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon icon-blue"><el-icon><Document /></el-icon></div>
              <div class="stat-label">SOP 总数</div>
              <div class="stat-value">{{ summaryStats.totalSops }}</div>
              <div class="stat-desc">当前已发布流程数量</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon icon-green"><el-icon><DataLine /></el-icon></div>
              <div class="stat-label">执行记录</div>
              <div class="stat-value">{{ summaryStats.totalExecutions }}</div>
              <div class="stat-desc">累计采集到的用户执行记录</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon icon-orange"><el-icon><DataLine /></el-icon></div>
              <div class="stat-label">通过率</div>
              <div class="stat-value">{{ formatRate(summaryStats.passRate) }}</div>
              <div class="stat-desc">当前自动评测整体通过表现</div>
            </div>
            <div class="stat-card highlight-card">
              <div class="stat-icon icon-red"><el-icon><DataLine /></el-icon></div>
              <div class="stat-label">待复核</div>
              <div class="stat-value">{{ summaryStats.pendingReviewCount }}</div>
              <div class="stat-desc">还需要人工确认的记录</div>
            </div>
          </div>

          <div class="section-block">
            <SectionHeader title="SOP 维度统计" subtitle="按流程查看执行次数、通过率和平均得分" />
            <GroupedList
              :columns="sopStatsColumns"
              :data="sopStatsList"
              empty-text="暂无统计数据"
            >
              <template #cell-passRate="{ value }">{{ formatRate(value) }}</template>
              <template #cell-averageScore="{ value }">{{ formatAverageScore(value) }}</template>
            </GroupedList>
          </div>

          <div class="section-block">
            <SectionHeader title="问题类型统计" subtitle="查看模型命中的主要问题类型" />
            <GroupedList :columns="issueTypeColumns" :data="issueTypeStats" empty-text="暂无问题类型统计" />
          </div>

          <div class="section-block">
            <SectionHeader title="执行记录列表" subtitle="从这里查看明细并处理人工复核" />
            <div class="filter-toolbar">
              <div class="filter-form">
                <el-input
                  v-model="historyFilters.keyword"
                  class="filter-input"
                  clearable
                  placeholder="按 SOP 名称搜索"
                  @keyup.enter="applyHistoryFilters"
                />
                <el-select v-model="historyFilters.aiStatus" class="filter-select" placeholder="AI 结论" clearable>
                  <el-option label="全部 AI 结论" value="" />
                  <el-option label="通过" value="passed" />
                  <el-option label="异常" value="failed" />
                </el-select>
                <el-select v-model="historyFilters.reviewStatus" class="filter-select" placeholder="人工复核" clearable>
                  <el-option label="全部复核状态" value="" />
                  <el-option label="待复核" value="pending" />
                  <el-option label="复核通过" value="approved" />
                  <el-option label="复核不通过" value="rejected" />
                  <el-option label="需要整改" value="needs_attention" />
                </el-select>
                <el-select v-model="historyFilters.sortOrder" class="filter-select filter-sort" placeholder="时间排序">
                  <el-option label="按时间倒序" value="desc" />
                  <el-option label="按时间正序" value="asc" />
                </el-select>
              </div>
              <div class="filter-actions">
                <button
                  type="button"
                  :class="['pill-btn', 'filter-pill', { active: historyFilters.reviewStatus === 'pending' }]"
                  @click="togglePendingReviewFilter"
                >
                  只看待复核
                </button>
                <button
                  type="button"
                  :class="['pill-btn', 'filter-pill', { active: historyFilters.aiStatus === 'failed' }]"
                  @click="toggleAiAbnormalFilter"
                >
                  只看 AI 判定异常
                </button>
                <el-button class="filter-action-btn" type="primary" @click="applyHistoryFilters">查询</el-button>
                <el-button class="filter-action-btn" @click="resetHistoryFilters">重置</el-button>
              </div>
            </div>
            <GroupedList
              v-loading="historyLoading"
              :columns="historyColumns"
              :data="historyList"
              :empty-text="historyEmptyText"
            >
              <template #cell-userName="{ row }">{{ row.userDisplayName || row.userName || '未知用户' }}</template>
              <template #cell-aiStatus="{ row }">
                <StatusBadge :type="row.status === 'passed' ? 'success' : 'danger'">
                  {{ getStatusText(row.status) }}
                </StatusBadge>
              </template>
              <template #cell-reviewStatus="{ row }">
                <StatusBadge :type="getReviewBadgeType(row.manualReview?.status)">
                  {{ getReviewStatusText(row.manualReview?.status) }}
                </StatusBadge>
              </template>
              <template #cell-actions="{ row }">
                <button class="text-btn" @click="openHistoryDetail(row)">详情</button>
                <button class="text-btn" @click="openReviewDialog(row)">复核</button>
              </template>
            </GroupedList>
          </div>
        </div>

      </main>
    </div>

    <!-- ─── 新建 SOP 对话框 ─────────────────────────────────── -->
    <el-dialog v-model="dialogVisible" title="新建标准操作流程 (SOP)" width="640px" class="apple-dialog" destroy-on-close>
      <el-form :model="sopForm" label-position="top" class="apple-form">
        <div class="form-row">
          <el-form-item label="SOP 名称" class="flex-1">
            <el-input v-model="sopForm.name" placeholder="例如：实验室安全操作规范" />
          </el-form-item>
          <el-form-item label="适用场景" class="flex-1">
            <el-input v-model="sopForm.scene" placeholder="例如：化学实验室" />
          </el-form-item>
        </div>

        <el-form-item label="步骤数量">
          <el-input-number v-model="sopForm.stepCount" :min="1" :max="20" @change="handleStepCountChange" />
        </el-form-item>

        <el-form-item label="流程完整示范视频">
          <el-upload action="#" :auto-upload="false" :show-file-list="false" accept="video/*" :on-change="handleWorkflowVideoChange">
            <el-button class="upload-btn">{{ sopForm.workflowVideo ? sopForm.workflowVideo.name : '上传整个流程的完整示范视频' }}</el-button>
          </el-upload>
          <div class="step-hint">管理员先定义全部步骤说明，再上传一条覆盖整个流程的完整示范视频。系统会根据整条流程视频自动为每一步切帧、定位关键时刻并生成 ROI 提示。</div>
        </el-form-item>

        <div class="steps-section">
          <div class="section-title">步骤详情</div>
          <div v-for="(step, index) in sopForm.steps" :key="index" class="step-card">
            <div class="step-header">步骤 {{ index + 1 }}</div>
            <el-input v-model="step.description" type="textarea" :rows="2" resize="none" placeholder="请描述该步骤的标准动作，大模型将以此为比对依据..." />
            <div class="form-row">
              <el-form-item label="步骤类型" class="flex-1">
                <el-select v-model="step.stepType" @change="handleStepTypeChange(step)">
                  <el-option v-for="option in STEP_TYPE_OPTIONS" :key="option.value" :label="option.label" :value="option.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="步骤权重" class="flex-1">
                <el-input-number v-model="step.stepWeight" :min="0.5" :max="5" :step="0.5" />
              </el-form-item>
            </div>
            <div class="form-row">
              <el-form-item label="最短耗时(秒)" class="flex-1">
                <el-input-number v-model="step.minDurationSec" :min="0" :max="3600" :step="1" placeholder="不限制" />
              </el-form-item>
              <el-form-item label="最长耗时(秒)" class="flex-1">
                <el-input-number v-model="step.maxDurationSec" :min="0" :max="3600" :step="1" placeholder="不限制" />
              </el-form-item>
            </div>
            <el-form-item v-if="step.stepType === 'conditional'" label="条件触发说明">
              <el-input v-model="step.conditionText" type="textarea" :rows="2" resize="none" placeholder="说明什么情况下该步骤需要执行" />
            </el-form-item>
            <el-form-item label="前置依赖步骤">
              <el-select v-model="step.prerequisiteStepNos" multiple collapse-tags collapse-tags-tooltip placeholder="可不选">
                <el-option
                  v-for="stepNo in index"
                  :key="`pre-${index}-${stepNo}`"
                  :label="`步骤 ${stepNo}`"
                  :value="stepNo"
                />
              </el-select>
            </el-form-item>
          </div>
        </div>

        <!-- ─── 罚分参数配置 ─────────────────────────── -->
        <div class="penalty-section">
          <button type="button" class="penalty-toggle" @click="showPenaltyConfig = !showPenaltyConfig">
            <span class="penalty-toggle-left">
              <svg class="penalty-chevron" :class="{ open: showPenaltyConfig }" width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3 5l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span>自定义罚分参数</span>
              <span v-if="customizedPenaltyCount > 0" class="penalty-modified-badge">{{ customizedPenaltyCount }} 项已调整</span>
            </span>
            <span class="penalty-optional-tag">可选</span>
          </button>
          <Transition name="penalty-expand">
            <div v-if="showPenaltyConfig" class="penalty-grid">
              <div class="penalty-hint">
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style="flex-shrink:0;margin-top:1px"><circle cx="6.5" cy="6.5" r="6" stroke="currentColor" stroke-width="1"/><path d="M6.5 5.5v4M6.5 3.5v1" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
                默认使用系统内置罚分权重，可按场景需求调整。修改后仅对本 SOP 生效。
              </div>
              <div class="penalty-columns">
                <div
                  v-for="item in PENALTY_ISSUE_TYPES"
                  :key="item.key"
                  class="penalty-item"
                  :class="{ 'is-modified': sopForm.penaltyConfig[item.key] !== undefined }"
                >
                  <span class="severity-dot" :style="{ background: getPenaltySeverityColor(DEFAULT_PENALTY_VALUES[item.key]) }"></span>
                  <div class="penalty-label">
                    <span class="penalty-name">{{ item.label }}</span>
                    <span class="penalty-desc">{{ item.description }}</span>
                  </div>
                  <div class="penalty-control">
                    <el-input-number
                      :model-value="sopForm.penaltyConfig[item.key] ?? DEFAULT_PENALTY_VALUES[item.key]"
                      @update:model-value="val => { if (val !== DEFAULT_PENALTY_VALUES[item.key]) sopForm.penaltyConfig[item.key] = val; else delete sopForm.penaltyConfig[item.key] }"
                      :min="0" :max="100" :step="5" size="small"
                    />
                    <button
                      v-if="sopForm.penaltyConfig[item.key] !== undefined"
                      type="button"
                      class="penalty-reset-btn"
                      title="还原默认值"
                      @click="delete sopForm.penaltyConfig[item.key]"
                    >↺</button>
                  </div>
                </div>
              </div>
              <div v-if="customizedPenaltyCount > 0" class="penalty-footer">
                <button type="button" class="penalty-reset-all" @click="sopForm.penaltyConfig = {}">还原全部默认值</button>
              </div>
            </div>
          </Transition>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button text @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" class="submit-btn" :loading="isSaving" @click="saveSop">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- ─── API 配置对话框 ────────────────────────────────────── -->
    <el-dialog v-model="configVisible" title="后端 API 配置" width="640px" class="apple-dialog">
      <el-alert type="info" :closable="false" show-icon title="当前配置保存到后端，管理员创建 SOP 和用户执行评估都会共用这份配置。" />
      <el-form label-position="top" class="apple-form config-form">
        <el-form-item label="API Key">
          <el-input v-model="apiConfig.apiKey" type="password" show-password />
        </el-form-item>
        <div class="form-row">
          <el-form-item label="Base URL" class="flex-1">
            <el-input v-model="apiConfig.baseURL" />
          </el-form-item>
          <el-form-item label="模型名称" class="flex-1">
            <el-input v-model="apiConfig.model" />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="fps" class="flex-1">
            <el-input-number v-model="apiConfig.fps" :min="0.1" :max="10" :step="0.5" />
          </el-form-item>
          <el-form-item label="temperature" class="flex-1">
            <el-input-number v-model="apiConfig.temperature" :min="0" :max="2" :step="0.1" />
          </el-form-item>
          <el-form-item label="timeout(ms)" class="flex-1">
            <el-input-number v-model="apiConfig.timeoutMs" :min="10000" :max="300000" :step="10000" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="resetApiConfig">恢复默认</el-button>
          <el-button type="primary" class="submit-btn" @click="saveApiConfig">保存配置</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- ─── SOP 预处理详情对话框 ─────────────────────────────── -->
    <el-dialog v-model="debugVisible" title="SOP 预处理详情" width="900px" class="apple-dialog">
      <div v-loading="debugLoading" class="detail-wrap">
        <div v-if="selectedSopDebug">
          <div class="summary debug-summary">{{ selectedSopDebug.name }} / {{ selectedSopDebug.scene }}</div>
          <div v-for="step in selectedSopDebug.steps" :key="step.stepNo" class="detail-box debug-step-box">
            <div class="detail-title">步骤 {{ step.stepNo }}: {{ step.description }}</div>
            <div class="detail-text">摘要：{{ step.referenceSummary || '暂无' }}</div>
            <div class="detail-text">预处理 Token：{{ formatTokenUsage(step.tokenUsage) }}</div>
            <div class="detail-text">ROI：{{ step.roiHint || '暂无' }}</div>
            <div class="detail-text">关键时刻：{{ formatSubsteps(step.substeps) }}</div>
            <div class="detail-text">参考模式：{{ step.referenceMode === 'text' ? '仅文字 SOP' : '完整步骤视频自动抽帧' }}</div>
            <div v-if="step.demoVideo?.url" class="manual-segmentation-box">
              <div class="manual-title">手动修正关键帧</div>
              <div class="manual-subtitle">系统会先基于完整步骤视频自动生成关键帧、关键时刻和 ROI。若结果不理想，可输入秒数手动重建关键帧。</div>
              <el-input v-model="step.manualTimestampInput" placeholder="输入时间点，例如：0.8, 1.6, 3.2" />
              <el-button type="primary" plain class="manual-btn" :loading="step.manualSegmentationLoading" @click="applyManualSegmentation(step)">按时间点重建关键帧</el-button>
            </div>
            <div v-else class="detail-text muted-text">该步骤当前缺少完整示范视频，建议补传后再由系统自动生成参考关键帧、关键时刻和 ROI。</div>
            <div class="demo-video-box">
              <div class="manual-title">{{ step.demoVideo?.url ? '替换流程示范视频' : '上传流程示范视频' }}</div>
              <div class="manual-subtitle">上传后系统会重新基于整条流程完整视频分析当前步骤，并自动生成参考关键帧、关键时刻和 ROI 信息。</div>
              <el-upload action="#" :auto-upload="false" :show-file-list="false" accept="video/*" :on-change="(file) => handleDebugStepVideoChange(step, file)">
                <el-button class="upload-btn">{{ step.reuploadVideo ? step.reuploadVideo.name : (step.demoVideo?.url ? '重新选择整条流程视频' : '选择整条流程视频') }}</el-button>
              </el-upload>
              <el-button type="primary" plain class="manual-btn" :loading="step.demoVideoUploadLoading" @click="replaceStepDemoVideo(step)">上传并自动重建参考</el-button>
            </div>
            <div class="preprocess-editor-box">
              <div class="manual-title">编辑预处理信息</div>
              <div class="manual-subtitle">可手动修正该步骤的摘要、ROI 提示和关键时刻，保存后会直接覆盖当前预处理结果。</div>
              <el-form-item label="参考摘要">
                <el-input v-model="step.referenceSummaryDraft" type="textarea" :rows="2" resize="none" />
              </el-form-item>
              <el-form-item label="ROI 提示">
                <el-input v-model="step.roiHintDraft" type="textarea" :rows="2" resize="none" />
              </el-form-item>
              <el-form-item label="关键时刻">
                <el-input v-model="step.substepsDraft" type="textarea" :rows="3" resize="none" placeholder="每行一条，格式：标题@秒数" />
              </el-form-item>
              <el-button type="primary" plain class="manual-btn" :loading="step.referenceMetadataSaving" @click="saveStepReferenceMetadata(step)">保存预处理信息</el-button>
            </div>
            <div class="detail-text">步骤类型：{{ formatStepType(step.stepType) }}</div>
            <div class="detail-text">步骤权重：{{ Number(step.stepWeight || 1).toFixed(1) }}</div>
            <div class="detail-text">耗时限制：{{ formatDurationLimit(step) }}</div>
            <div class="detail-text">条件说明：{{ step.conditionText || '无' }}</div>
            <div class="detail-text">前置依赖：{{ (step.prerequisiteStepNos || []).length ? step.prerequisiteStepNos.join(', ') : '无' }}</div>
            <div class="frame-grid">
              <img v-for="(frame, index) in step.referenceFrames || []" :key="`${step.stepNo}-${index}`" :src="frame" class="frame" />
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- ─── 执行记录详情对话框 ────────────────────────────────── -->
    <el-dialog v-model="historyDetailVisible" title="执行记录详情" width="820px" class="apple-dialog">
      <div v-if="selectedHistoryRecord" class="detail-wrap">
        <div class="summary">{{ selectedHistoryRecord.taskName }} / {{ selectedHistoryRecord.userDisplayName || selectedHistoryRecord.userName || '未知用户' }} / {{ selectedHistoryRecord.finishTime }}</div>
        <div class="detail-box">
          <div class="detail-title">综合反馈</div>
          <div class="detail-text">{{ selectedHistoryRecord.detail.feedback || '暂无反馈' }}</div>
        </div>
        <div class="detail-box">
          <div class="detail-title">上传视频</div>
          <video v-if="historyVideoUrl" :src="historyVideoUrl" controls class="video" />
          <el-empty v-else description="未记录上传视频" />
        </div>
        <div class="detail-box" v-if="selectedHistoryRecord.detail.issues?.length">
          <div class="detail-title">问题列表</div>
          <div class="tag-list">
            <el-tag v-for="(item, index) in selectedHistoryRecord.detail.issues" :key="index">{{ item }}</el-tag>
          </div>
        </div>
        <div class="detail-box step-results-box" v-if="selectedHistoryRecord.detail.stepResults?.length">
          <div class="detail-title">步骤结果</div>
          <EvalTimeline
            :step-results="selectedHistoryRecord.detail.stepResults"
            :video-duration-sec="selectedHistoryRecord.detail.overviewPreview?.durationSec || 0"
          />
          <div v-if="selectedHistoryRecord.detail.stepResults.length >= 3" class="viz-row">
            <ScoreRadar :step-results="selectedHistoryRecord.detail.stepResults" :size="200" />
          </div>
          <div v-for="item in selectedHistoryRecord.detail.stepResults" :key="item.stepNo" class="step-result-item">
            <div class="step-result-top">
              <div class="step-result-title">步骤 {{ item.stepNo }}: {{ item.description }}</div>
              <StatusBadge :type="item.includedInScore === false ? 'default' : (item.passed ? 'success' : 'danger')">{{ item.includedInScore === false ? '未计分' : (item.passed ? '通过' : '异常') }}</StatusBadge>
            </div>
            <div class="step-result-meta">类型 {{ formatStepType(item.stepType) }} / 权重 {{ Number(item.stepWeight || 1).toFixed(1) }}</div>
            <div class="step-result-meta">适用 {{ item.applicable === false ? '否' : '是' }} / 前置依赖 {{ item.prerequisiteViolated ? '违反' : '正常' }}</div>
            <div class="step-result-meta">检测区间 {{ item.detectedStartSec ?? '-' }}s ~ {{ item.detectedEndSec ?? '-' }}s / 得分 {{ item.score ?? '-' }}</div>
            <div class="detail-text">{{ item.evidence || '暂无证据说明' }}</div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- ─── 人工复核对话框 ─────────────────────────────────────── -->
    <el-dialog v-model="reviewDialogVisible" title="人工复核" width="560px" class="apple-dialog">
      <div v-if="reviewTarget" class="detail-wrap">
        <div class="summary">{{ reviewTarget.taskName }} / {{ reviewTarget.userDisplayName || reviewTarget.userName || '未知用户' }} / {{ reviewTarget.finishTime }}</div>
        <video v-if="reviewVideoUrl" :src="reviewVideoUrl" controls class="video" />
        <el-form :model="reviewForm" label-position="top" class="apple-form">
          <el-form-item label="复核结论">
            <el-radio-group v-model="reviewForm.status" class="review-radio-group">
              <el-radio-button label="approved">复核通过</el-radio-button>
              <el-radio-button label="rejected">复核不通过</el-radio-button>
              <el-radio-button label="needs_attention">需要整改</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="复核意见">
            <el-input v-model="reviewForm.note" type="textarea" :rows="4" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button text @click="reviewDialogVisible = false">取消</el-button>
          <el-button type="primary" class="submit-btn" @click="saveManualReview">保存</el-button>
        </div>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataLine, Document, Fold, Monitor, Plus, SwitchButton } from '@element-plus/icons-vue'
import { clearAuthSession, createSop, fetchAuthorizedMediaBlobUrl, fileToDataUrl, getConfig, getCurrentUser, getHistoryDetail, getSopDetail, getStats, isAuthSessionError, listHistory, listSops, listUsers, logout, removeSop, reviewHistory, updateConfig, updateSopStepDemoVideo, updateSopStepReferenceMetadata, updateSopStepSegmentation, updateUserStatus } from '../api/client'
import AppBlobs from '../components/AppBlobs.vue'
import GroupedList from '../components/GroupedList.vue'
import SectionHeader from '../components/SectionHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'
import EvalTimeline from '../components/EvalTimeline.vue'
import ScoreRadar from '../components/ScoreRadar.vue'

const router = useRouter()
const sidebarOpen = ref(false)
const activeMenu = ref('manage')
const sopList = ref([])
const userList = ref([])
const historyList = ref([])
const historyLoading = ref(false)
const summaryStats = ref({ totalSops: 0, totalExecutions: 0, pendingReviewCount: 0, passRate: 0 })
const sopStatsList = ref([])
const issueTypeStats = ref([])
const dialogVisible = ref(false)
const isSaving = ref(false)
const configVisible = ref(false)
const debugVisible = ref(false)
const debugLoading = ref(false)
const selectedSopDebug = ref(null)
const historyDetailVisible = ref(false)
const selectedHistoryRecord = ref(null)
const historyVideoUrl = ref('')
const reviewDialogVisible = ref(false)
const reviewTarget = ref(null)
const reviewVideoUrl = ref('')
const reviewForm = reactive({ status: 'approved', note: '' })
const historyFilters = reactive({
  keyword: '',
  aiStatus: '',
  reviewStatus: '',
  sortOrder: 'desc'
})
const sopForm = reactive({ name: '', scene: '', stepCount: 1, workflowVideo: null, steps: [], penaltyConfig: {} })
const currentUser = ref(getCurrentUser())
const DEFAULT_API_CONFIG = {
  apiKey: '',
  baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  model: 'qwen3.5-plus',
  fps: 6,
  temperature: 0.1,
  timeoutMs: 120000
}
const STEP_TYPE_OPTIONS = [
  { label: '必做', value: 'required' },
  { label: '可选', value: 'optional' },
  { label: '条件触发', value: 'conditional' }
]

const PENALTY_ISSUE_TYPES = [
  { key: '正常', label: '正常', description: '操作符合标准' },
  { key: '证据不足', label: '证据不足', description: '操作存在但画面不清晰' },
  { key: '重复操作', label: '重复操作', description: '同一步骤多次执行' },
  { key: '部分完成', label: '部分完成', description: '步骤仅完成一部分' },
  { key: '过早执行', label: '过早执行', description: '在规定时机之前执行' },
  { key: '延后执行', label: '延后执行', description: '在规定时机之后执行' },
  { key: '过快完成', label: '过快完成', description: '未达到规定持续时间' },
  { key: '超时完成', label: '超时完成', description: '超过步骤规定完成时限' },
  { key: '动作错误', label: '动作错误', description: '执行了错误的操作' },
  { key: '顺序颠倒', label: '顺序颠倒', description: '步骤执行顺序错误' },
  { key: '前置条件缺失', label: '前置条件缺失', description: '前置步骤未完成即执行' },
  { key: '缺失', label: '缺失', description: '该步骤未被执行' }
]
const DEFAULT_PENALTY_VALUES = {
  '正常': 0, '证据不足': 15, '重复操作': 10, '部分完成': 20,
  '过早执行': 25, '延后执行': 25, '过快完成': 25, '超时完成': 25, '动作错误': 35,
  '顺序颠倒': 40, '前置条件缺失': 45, '缺失': 60
}

const showPenaltyConfig = ref(false)
const customizedPenaltyCount = computed(() => Object.keys(sopForm.penaltyConfig).length)

function getPenaltySeverityColor(value) {
  if (value === 0) return 'var(--system-green)'
  if (value <= 15) return 'var(--system-yellow)'
  if (value <= 30) return 'var(--system-orange)'
  return 'var(--system-red)'
}
const apiConfig = reactive({ ...DEFAULT_API_CONFIG })

const currentUserName = computed(() => currentUser.value?.displayName || currentUser.value?.username || '管理员')
const userInitials = computed(() => {
  const name = currentUser.value?.displayName || currentUser.value?.username || 'A'
  return name.charAt(0).toUpperCase()
})
const panelHeaderTitle = computed(() => {
  if (activeMenu.value === 'manage') return 'SOP 管理'
  if (activeMenu.value === 'users') return '用户管理'
  return '数据统计'
})
const panelHeaderSubtitle = computed(() => {
  if (activeMenu.value === 'manage') return '统一管理 SOP 内容、步骤说明和示范视频'
  if (activeMenu.value === 'users') return '查看已注册账号，并启用或禁用普通用户'
  return '查看整体执行情况，并处理需要人工确认的记录'
})

const hasActiveHistoryFilters = computed(() => {
  return !!(
    String(historyFilters.keyword || '').trim() ||
    historyFilters.aiStatus ||
    historyFilters.reviewStatus ||
    historyFilters.sortOrder !== 'desc'
  )
})
const historyEmptyText = computed(() => hasActiveHistoryFilters.value ? '当前筛选条件下暂无记录' : '暂无执行记录')

const sopColumns = [
  { key: 'name', label: 'SOP 名称' },
  { key: 'scene', label: '适用场景' },
  { key: 'stepCount', label: '步骤数', align: 'center' },
  { key: 'createTime', label: '创建时间' },
  { key: 'actions', label: '操作', align: 'right' }
]
const userColumns = [
  { key: 'displayName', label: '昵称' },
  { key: 'username', label: '账号' },
  { key: 'role', label: '角色', align: 'center' },
  { key: 'status', label: '状态', align: 'center' },
  { key: 'lastLoginAt', label: '最近登录' },
  { key: 'createdAt', label: '创建时间' },
  { key: 'actions', label: '操作', align: 'center' }
]
const sopStatsColumns = [
  { key: 'taskName', label: 'SOP 名称' },
  { key: 'scene', label: '适用场景' },
  { key: 'totalCount', label: '执行次数', align: 'center' },
  { key: 'passedCount', label: '通过次数', align: 'center' },
  { key: 'passRate', label: '通过率', align: 'center' },
  { key: 'averageScore', label: '平均得分', align: 'center' }
]
const historyColumns = [
  { key: 'taskName', label: 'SOP 名称' },
  { key: 'userName', label: '所属用户' },
  { key: 'finishTime', label: '完成时间' },
  { key: 'aiStatus', label: 'AI 结论', align: 'center' },
  { key: 'reviewStatus', label: '人工复核', align: 'center' },
  { key: 'actions', label: '操作', align: 'right' }
]

function showErrorMessage(error, fallback) {
  if (isAuthSessionError(error)) return
  ElMessage.error(error.message || fallback)
}


const issueTypeColumns = [
  { key: 'issueType', label: '问题类型' },
  { key: 'count', label: '命中次数', align: 'center' }
]

function createEmptyStep() {
  return {
    description: '',
    video: { __workflowPlaceholder: true },
    stepType: 'required',
    stepWeight: 1,
    conditionText: '',
    prerequisiteStepNos: [],
    minDurationSec: null,
    maxDurationSec: null
  }
}

async function loadApiConfig() {
  const config = (await getConfig()).data || {}
  Object.assign(apiConfig, DEFAULT_API_CONFIG, config)
}

async function openConfigDialog() {
  try {
    await loadApiConfig()
    configVisible.value = true
  } catch (error) {
    showErrorMessage(error, '加载配置失败')
  }
}

async function saveApiConfig() {
  try {
    await updateConfig({ ...apiConfig })
    configVisible.value = false
    ElMessage.success('配置已保存')
  } catch (error) {
    showErrorMessage(error, '保存配置失败')
  }
}

function resetApiConfig() {
  Object.assign(apiConfig, DEFAULT_API_CONFIG)
}

function revokeVideoUrl(targetRef) {
  if (targetRef.value) {
    URL.revokeObjectURL(targetRef.value)
    targetRef.value = ''
  }
}

function normalizeHistory(record = {}) {
  return {
    ...record,
    detail: {
      feedback: record.detail?.feedback || '',
      issues: Array.isArray(record.detail?.issues) ? record.detail.issues : [],
      uploadedVideo: record.detail?.uploadedVideo || null,
      stepResults: Array.isArray(record.detail?.stepResults) ? record.detail.stepResults : [],
      overviewPreview: record.detail?.overviewPreview || null,
      segmentPreview: record.detail?.segmentPreview || null
    },
    manualReview: record.manualReview || null
  }
}

async function loadSopList() {
  sopList.value = (await listSops()).data || []
}

async function loadHistoryList() {
  historyLoading.value = true
  try {
    historyList.value = ((await listHistory({
      keyword: historyFilters.keyword,
      aiStatus: historyFilters.aiStatus,
      reviewStatus: historyFilters.reviewStatus,
      sortOrder: historyFilters.sortOrder
    })).data || []).map(normalizeHistory)
  } finally {
    historyLoading.value = false
  }
}

async function loadUserList() {
  userList.value = (await listUsers()).data || []
}

async function loadStats() {
  const result = await getStats()
  summaryStats.value = result.data?.summaryStats || summaryStats.value
  sopStatsList.value = result.data?.sopStatsList || []
  issueTypeStats.value = result.data?.issueTypeStats || []
}

function applyHistoryFilters() {
  loadHistoryList().catch((error) => showErrorMessage(error, '加载执行记录失败'))
}

function resetHistoryFilters() {
  historyFilters.keyword = ''
  historyFilters.aiStatus = ''
  historyFilters.reviewStatus = ''
  historyFilters.sortOrder = 'desc'
  applyHistoryFilters()
}

function togglePendingReviewFilter() {
  historyFilters.reviewStatus = historyFilters.reviewStatus === 'pending' ? '' : 'pending'
  applyHistoryFilters()
}

function toggleAiAbnormalFilter() {
  historyFilters.aiStatus = historyFilters.aiStatus === 'failed' ? '' : 'failed'
  applyHistoryFilters()
}

async function reloadCurrentView() {
  await loadSopList()
  if (activeMenu.value === 'users') {
    await loadUserList()
  } else if (activeMenu.value === 'stats') {
    await Promise.all([loadHistoryList(), loadStats()])
  }
}

function handleMenuSelect(index) {
  activeMenu.value = index
  sidebarOpen.value = false
  reloadCurrentView().catch((error) => showErrorMessage(error, '加载失败'))
}

async function handleLogout() {
  try {
    await logout()
  } catch (_error) {
    // 即使后端会话已失效，也允许前端本地退出
  } finally {
    clearAuthSession()
    router.push('/login')
  }
}

function openCreateDialog() {
  sopForm.name = ''
  sopForm.scene = ''
  sopForm.stepCount = 1
  sopForm.workflowVideo = null
  sopForm.steps = [createEmptyStep()]
  sopForm.penaltyConfig = {}
  showPenaltyConfig.value = false
  dialogVisible.value = true
}

function handleStepCountChange(value) {
  while (sopForm.steps.length < value) sopForm.steps.push(createEmptyStep())
  if (sopForm.steps.length > value) sopForm.steps.splice(value)
  if (sopForm.workflowVideo) {
    sopForm.steps.forEach((item) => {
      item.video = sopForm.workflowVideo
    })
  }
}

function handleWorkflowVideoChange(file) {
  sopForm.workflowVideo = file?.raw || file
  sopForm.steps.forEach((item) => {
    item.video = sopForm.workflowVideo
  })
}

function handleStepTypeChange(step) {
  if (step.stepType !== 'conditional') {
    step.conditionText = ''
  }
}

function validateStepConfig(step, index) {
  const stepNo = index + 1
  const weight = Number(step.stepWeight)
  if (!Number.isFinite(weight) || weight < 0.5 || weight > 5) {
    return `步骤 ${stepNo} 的权重必须在 0.5 到 5.0 之间`
  }
  if (step.stepType === 'conditional' && !String(step.conditionText || '').trim()) {
    return `步骤 ${stepNo} 是条件触发步骤，必须填写触发说明`
  }
  const invalidPrerequisite = (step.prerequisiteStepNos || []).some((value) => Number(value) >= stepNo || Number(value) <= 0)
  if (invalidPrerequisite) {
    return `步骤 ${stepNo} 的前置依赖只能选择前面的步骤`
  }
  const minDuration = normalizeOptionalDuration(step.minDurationSec)
  const maxDuration = normalizeOptionalDuration(step.maxDurationSec)
  if (minDuration != null && maxDuration != null && minDuration > maxDuration) {
    return `步骤 ${stepNo} 的最短耗时不能大于最长耗时`
  }
  return ''
}

function normalizeOptionalDuration(value) {
  const number = Number(value)
  return Number.isFinite(number) && number > 0 ? number : null
}

async function saveSop() {
  if (!sopForm.name.trim()) return ElMessage.warning('请输入 SOP 名称')
  if (sopForm.steps.some((item) => !item.description.trim())) return ElMessage.warning('请补全步骤描述')

  if (sopForm.steps.some((item) => !item.video)) return ElMessage.warning('请为每个步骤上传完整示范视频')
  if (!sopForm.workflowVideo) return ElMessage.warning('请上传整个流程的完整示范视频')
  sopForm.steps.forEach((item) => {
    item.video = sopForm.workflowVideo
  })
  const stepConfigError = sopForm.steps.map((item, index) => validateStepConfig(item, index)).find(Boolean)
  if (stepConfigError) return ElMessage.warning(stepConfigError)

  isSaving.value = true
  try {
    const steps = await Promise.all(sopForm.steps.map(async (item) => ({
      description: item.description.trim(),
      stepType: item.stepType,
      stepWeight: Number(item.stepWeight),
      conditionText: String(item.conditionText || '').trim(),
      prerequisiteStepNos: (item.prerequisiteStepNos || []).map((value) => Number(value)).filter((value) => Number.isFinite(value)),
      minDurationSec: normalizeOptionalDuration(item.minDurationSec),
      maxDurationSec: normalizeOptionalDuration(item.maxDurationSec),
      videoDataUrl: item.video ? await fileToDataUrl(item.video) : '',
      videoMeta: item.video ? {
        name: item.video.name || '',
        type: item.video.type || '',
        size: item.video.size ?? null,
        lastModified: item.video.lastModified ?? null
      } : null
    })))
    const result = await createSop({
      name: sopForm.name.trim(),
      scene: sopForm.scene.trim(),
      steps,
      workflowVideoDataUrl: await fileToDataUrl(sopForm.workflowVideo),
      workflowVideoMeta: {
        name: sopForm.workflowVideo.name || '',
        type: sopForm.workflowVideo.type || '',
        size: sopForm.workflowVideo.size ?? null,
        lastModified: sopForm.workflowVideo.lastModified ?? null
      },
      penaltyConfig: Object.keys(sopForm.penaltyConfig).length > 0 ? sopForm.penaltyConfig : null
    })
    dialogVisible.value = false
    await reloadCurrentView()
    ElMessage.success('SOP 已保存')
    if (result.warnings?.length) ElMessage.warning(result.warnings[0])
  } catch (error) {
    showErrorMessage(error, '保存失败')
  } finally {
    isSaving.value = false
  }
}

async function openDebugSop(row) {
  debugVisible.value = true
  debugLoading.value = true
  try {
    selectedSopDebug.value = buildDebugSopState((await getSopDetail(row.id)).data)
  } catch (error) {
    showErrorMessage(error, '加载详情失败')
    debugVisible.value = false
  } finally {
    debugLoading.value = false
  }
}

async function deleteCurrentSop(row) {
  try {
    await ElMessageBox.confirm('确定删除该 SOP 吗？', '提示', { type: 'warning', customClass: 'apple-msgbox' })
    await removeSop(row.id)
    await Promise.all([reloadCurrentView(), loadStats()])
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') showErrorMessage(error, '删除失败')
  }
}

async function openHistoryDetail(row) {
  try {
    selectedHistoryRecord.value = normalizeHistory((await getHistoryDetail(row.id)).data)
    revokeVideoUrl(historyVideoUrl)
    const mediaPath = selectedHistoryRecord.value?.detail?.uploadedVideo?.url || ''
    if (mediaPath) {
      historyVideoUrl.value = await fetchAuthorizedMediaBlobUrl(mediaPath)
    }
    historyDetailVisible.value = true
  } catch (error) {
    showErrorMessage(error, '加载详情失败')
  }
}

async function openReviewDialog(row) {
  try {
    reviewTarget.value = normalizeHistory((await getHistoryDetail(row.id)).data)
    revokeVideoUrl(reviewVideoUrl)
    const mediaPath = reviewTarget.value?.detail?.uploadedVideo?.url || ''
    if (mediaPath) {
      reviewVideoUrl.value = await fetchAuthorizedMediaBlobUrl(mediaPath)
    }
    reviewForm.status = reviewTarget.value.manualReview?.status || (reviewTarget.value.status === 'passed' ? 'approved' : 'needs_attention')
    reviewForm.note = reviewTarget.value.manualReview?.note || ''
    reviewDialogVisible.value = true
  } catch (error) {
    showErrorMessage(error, '加载复核对象失败')
  }
}

async function saveManualReview() {
  if (!reviewTarget.value) return
  try {
    await reviewHistory(reviewTarget.value.id, { status: reviewForm.status, note: reviewForm.note.trim() })
    reviewDialogVisible.value = false
    await Promise.all([loadHistoryList(), loadStats()])
    ElMessage.success('复核已保存')
  } catch (error) {
    showErrorMessage(error, '保存复核失败')
  }
}

async function toggleUserStatus(row) {
  if (!row?.id) return
  const nextStatus = row.status === 'active' ? 'disabled' : 'active'
  try {
    await updateUserStatus(row.id, { status: nextStatus })
    await loadUserList()
    ElMessage.success(nextStatus === 'active' ? '用户已启用' : '用户已禁用')
  } catch (error) {
    showErrorMessage(error, '更新用户状态失败')
  }
}

function buildDebugSopState(data) {
  return {
    ...data,
    steps: (data.steps || []).map((step) => ({
      ...step,
      prerequisiteStepNos: Array.isArray(step.prerequisiteStepNos) ? step.prerequisiteStepNos : [],
      referenceSummaryDraft: step.referenceSummary || '',
      roiHintDraft: step.roiHint || '',
      substepsDraft: Array.isArray(step.substeps) ? step.substeps.map((item) => `${item.title || '关键时刻'}@${Number(item.timestampSec || 0)}`).join('\n') : '',
      manualTimestampInput: Array.isArray(step.referenceFeatures?.sampleTimestamps) ? step.referenceFeatures.sampleTimestamps.join(', ') : '',
      manualSegmentationLoading: false,
      reuploadVideo: null,
      demoVideoUploadLoading: false,
      referenceMetadataSaving: false
    }))
  }
}

function handleDebugStepVideoChange(step, file) {
  step.reuploadVideo = file?.raw || file
}

function parseTimestampInput(value) {
  return String(value || '')
    .split(/[\s,，、;；]+/)
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item) && item >= 0)
}

function parseSubstepsDraft(value) {
  return String(value || '')
    .split(/\r?\n+/)
    .map((line) => String(line || '').trim())
    .filter(Boolean)
    .map((line, index) => {
      const parts = line.split('@')
      const timestamp = Number(parts.pop())
      const title = parts.join('@').trim() || `关键时刻 ${index + 1}`
      return Number.isFinite(timestamp) && timestamp >= 0 ? { title, timestampSec: timestamp } : null
    })
    .filter(Boolean)
}

function formatTokenUsage(usage) {
  if (!usage) return '暂无'
  const input = Number.isFinite(Number(usage.inputTokens)) ? Number(usage.inputTokens) : '-'
  const output = Number.isFinite(Number(usage.outputTokens)) ? Number(usage.outputTokens) : '-'
  const total = Number.isFinite(Number(usage.totalTokens)) ? Number(usage.totalTokens) : '-'
  return `输入 ${input} / 输出 ${output} / 总计 ${total}`
}

function formatStepType(stepType) {
  return STEP_TYPE_OPTIONS.find((item) => item.value === stepType)?.label || stepType || '-'
}

function formatDurationLimit(step = {}) {
  const parts = []
  const minDuration = normalizeOptionalDuration(step.minDurationSec)
  const maxDuration = normalizeOptionalDuration(step.maxDurationSec)
  if (minDuration != null) parts.push(`至少 ${minDuration}s`)
  if (maxDuration != null) parts.push(`最多 ${maxDuration}s`)
  return parts.length ? parts.join(' / ') : '无'
}

async function applyManualSegmentation(step) {
  const timestamps = parseTimestampInput(step.manualTimestampInput)
  if (!timestamps.length) return ElMessage.warning('请输入至少一个有效时间点')
  if (!selectedSopDebug.value?.id) return

  step.manualSegmentationLoading = true
  try {
    const result = await updateSopStepSegmentation(selectedSopDebug.value.id, step.stepNo, { timestamps })
    selectedSopDebug.value = buildDebugSopState(result.data)
    await loadSopList()
    ElMessage.success('关键帧已按手动时间点重建')
  } catch (error) {
    showErrorMessage(error, '重建关键帧失败')
  } finally {
    step.manualSegmentationLoading = false
  }
}

async function saveStepReferenceMetadata(step) {
  if (!selectedSopDebug.value?.id) return

  const substeps = parseSubstepsDraft(step.substepsDraft)
  step.referenceMetadataSaving = true
  try {
    const result = await updateSopStepReferenceMetadata(selectedSopDebug.value.id, step.stepNo, {
      referenceSummary: String(step.referenceSummaryDraft || '').trim(),
      roiHint: String(step.roiHintDraft || '').trim(),
      substeps
    })
    selectedSopDebug.value = buildDebugSopState(result.data)
    await loadSopList()
    ElMessage.success('预处理信息已更新')
  } catch (error) {
    showErrorMessage(error, '更新预处理信息失败')
  } finally {
    step.referenceMetadataSaving = false
  }
}

async function replaceStepDemoVideo(step) {
  if (!step?.reuploadVideo) return ElMessage.warning('请先选择示范视频')
  if (!selectedSopDebug.value?.id) return

  step.demoVideoUploadLoading = true
  try {
    const file = step.reuploadVideo
    const result = await updateSopStepDemoVideo(selectedSopDebug.value.id, step.stepNo, {
      videoDataUrl: await fileToDataUrl(file),
      videoMeta: {
        name: file.name || '',
        type: file.type || '',
        size: file.size ?? null,
        lastModified: file.lastModified ?? null
      }
    })
    selectedSopDebug.value = buildDebugSopState(result.data)
    await loadSopList()
    ElMessage.success('示范视频已更新，并重新生成参考结果')
  } catch (error) {
    showErrorMessage(error, '更新示范视频失败')
  } finally {
    step.demoVideoUploadLoading = false
  }
}

function formatAverageScore(value) {
  const num = Number(value)
  return Number.isFinite(num) ? `${num.toFixed(1)} / 100` : '-'
}

function formatRate(value) {
  const num = Number(value)
  return Number.isFinite(num) ? `${num.toFixed(0)}%` : '0%'
}

function getStatusText(status) {
  return status === 'passed' ? '通过' : '异常'
}

function getReviewStatusText(status) {
  if (status === 'approved') return '复核通过'
  if (status === 'rejected') return '复核不通过'
  if (status === 'needs_attention') return '需要整改'
  return '待复核'
}

function getReviewBadgeClass(status) {
  if (status === 'approved') return 'badge-success'
  if (status === 'rejected') return 'badge-danger'
  if (status === 'needs_attention') return 'badge-warning'
  return 'badge-default'
}

function getReviewBadgeType(status) {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  if (status === 'needs_attention') return 'warning'
  return 'default'
}

function formatSubsteps(list) {
  return Array.isArray(list) && list.length ? list.map((item) => `${item.title}@${Number(item.timestampSec).toFixed(2)}s`).join(' / ') : '暂无'
}

onMounted(() => {
  reloadCurrentView().catch((error) => showErrorMessage(error, '初始化失败'))
})

onUnmounted(() => {
  revokeVideoUrl(historyVideoUrl)
  revokeVideoUrl(reviewVideoUrl)
})
</script>

<style scoped>
/* ── Layout Shell ────────────────────────────────────────── */

.admin-layout {
  position: relative;
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-base);
  font-family: var(--font-family);
}

/* ── Sidebar ─────────────────────────────────────────────── */

.sidebar {
  position: relative;
  z-index: 10;
  width: var(--sidebar-width);
  flex-shrink: 0;
  background: var(--material-regular);
  border-right: 1px solid var(--separator);
  backdrop-filter: blur(var(--blur-lg)) saturate(160%);
  -webkit-backdrop-filter: blur(var(--blur-lg)) saturate(160%);
  display: flex;
  flex-direction: column;
  padding: var(--sp-4) 0 var(--sp-5);
  overflow-y: auto;
}

@media (prefers-color-scheme: dark) {
  .sidebar {
    box-shadow: 1px 0 0 rgba(0, 0, 0, 0.3);
  }
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: var(--sp-1) var(--sp-4) var(--sp-5);
  padding: 10px var(--sp-3);
  font-size: var(--fs-headline);
  font-weight: 700;
  color: var(--text-main);
  border-radius: 14px;
  background: var(--fill-quaternary);
}

.brand-logo {
  width: 30px;
  height: 30px;
  background: linear-gradient(150deg, var(--accent), var(--accent-deep));
  border-radius: var(--radius-sm);
  display: flex;
  justify-content: center;
  align-items: center;
  color: #fff;
  font-size: 15px;
  flex-shrink: 0;
}

/* ── Nav Menu ────────────────────────────────────────────── */

.nav-menu {
  flex: 1;
  padding: 0 10px;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  width: 100%;
  height: 44px;
  padding: 0 var(--sp-3);
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--text-soft);
  font-size: var(--fs-subheadline);
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  transition:
    background-color var(--duration-short) var(--ease-standard),
    color var(--duration-short) var(--ease-standard),
    transform var(--duration-micro) var(--ease-standard);
}

.nav-item:hover {
  background: var(--fill-quaternary);
  color: var(--text-main);
}

.nav-item.active {
  background: rgba(0, 122, 255, 0.12);
  color: var(--accent);
  font-weight: 600;
}

@media (prefers-color-scheme: dark) {
  .nav-item.active {
    background: rgba(10, 132, 255, 0.18);
  }
}

.nav-item:active {
  transform: scale(0.97);
}

.nav-icon-wrap {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  flex-shrink: 0;
}

.icon-blue   { background: linear-gradient(140deg, #1D9BF0, #007AFF); }
.icon-purple { background: linear-gradient(140deg, #BF5AF2, #9B59F5); }
.icon-orange { background: linear-gradient(140deg, #FF9F0A, #FF6B00); }
.icon-green  { background: linear-gradient(140deg, #34C759, #28A745); }
.icon-red    { background: linear-gradient(140deg, #FF6B6B, #FF3B30); }

/* ── Sidebar Bottom ──────────────────────────────────────── */

.sidebar-bottom {
  margin: var(--sp-4) 10px 0;
  padding-top: var(--sp-4);
  border-top: 1px solid var(--line-soft);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: var(--sp-2) var(--sp-2) 14px;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.username {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  width: 100%;
  height: var(--touch-target);
  padding: 0 14px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-soft);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  transition:
    background-color var(--duration-short) var(--ease-standard),
    color var(--duration-short) var(--ease-standard);
}

.logout-btn:hover {
  background: var(--fill-quaternary);
  color: var(--text-main);
}

.logout-btn:active {
  transform: scale(0.97);
}

/* ── Main Container ──────────────────────────────────────── */

.main-container {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── Top Header ──────────────────────────────────────────── */

.top-header {
  height: 64px;
  background: var(--material-regular);
  border-bottom: 1px solid var(--separator);
  backdrop-filter: blur(var(--blur-lg)) saturate(160%);
  -webkit-backdrop-filter: blur(var(--blur-lg)) saturate(160%);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 var(--sp-8);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: var(--sp-3);
}

.header-left h2 {
  margin: 0;
  font-size: var(--fs-title2);
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.header-subtitle {
  margin: 0;
  font-size: var(--fs-footnote);
  color: var(--text-faint);
  line-height: 1.4;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* ── Content Area ────────────────────────────────────────── */

.content-area {
  flex: 1;
  padding: var(--sp-6);
  overflow-y: auto;
}

/* ── Stats ───────────────────────────────────────────────── */

.stats-view {
  display: flex;
  flex-direction: column;
  gap: var(--sp-8);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sp-4);
}

.stat-card {
  position: relative;
  background: var(--material-chrome);
  backdrop-filter: blur(var(--blur-md)) saturate(150%);
  -webkit-backdrop-filter: blur(var(--blur-md)) saturate(150%);
  border: 1px solid rgba(255, 255, 255, 0.60);
  border-radius: var(--radius-xl);
  padding: var(--sp-5) var(--sp-6) var(--sp-6);
  min-height: 160px;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: box-shadow var(--duration-short) ease, transform var(--duration-short) ease;
}

@media (prefers-color-scheme: dark) {
  .stat-card {
    border-color: rgba(84, 84, 88, 0.4);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  }
}

.stat-card:hover {
  box-shadow: 0 10px 36px rgba(0, 0, 0, 0.10), 0 4px 12px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
}

.stat-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  margin-bottom: var(--sp-1);
}

.highlight-card {
  border-color: rgba(255, 59, 48, 0.22);
  background: linear-gradient(160deg, rgba(255, 59, 48, 0.04) 0%, transparent 60%), var(--material-chrome);
}

.stat-label {
  font-size: var(--fs-caption1);
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 44px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.04em;
  line-height: 1;
}

.stat-desc {
  font-size: var(--fs-footnote);
  color: var(--text-soft);
  line-height: 1.5;
}

/* ── Filter ──────────────────────────────────────────────── */

.filter-input {
  min-width: 220px;
  flex: 1 1 260px;
}

.filter-select {
  width: 160px;
}

.filter-sort {
  width: 150px;
}

/* ── Debug Dialog ────────────────────────────────────────── */

.debug-summary {
  font-size: var(--fs-subheadline);
  line-height: 1.6;
  margin-bottom: var(--sp-1);
}

.debug-step-box {
  border-radius: var(--radius-lg);
  padding: var(--sp-5) 22px;
}

/* ─── Penalty Config Section ──────────────────────── */
.penalty-section {
  margin-top: var(--sp-5);
}

.penalty-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 11px var(--sp-4);
  background: var(--fill-quaternary);
  border: 1px solid var(--separator);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--fs-callout);
  color: var(--text-main);
  font-weight: 500;
  font-family: inherit;
  transition: background 0.15s, border-color 0.15s;
}

.penalty-toggle:hover {
  background: var(--fill-tertiary);
  border-color: var(--accent);
}

.penalty-toggle-left {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.penalty-chevron {
  color: var(--text-soft);
  transition: transform 0.2s var(--ease-standard);
  flex-shrink: 0;
}

.penalty-chevron.open {
  transform: rotate(180deg);
}

.penalty-modified-badge {
  padding: 2px 8px;
  background: rgba(0, 122, 255, 0.12);
  color: var(--accent);
  border-radius: var(--radius-full);
  font-size: var(--fs-footnote);
  font-weight: 600;
}

.penalty-optional-tag {
  font-size: var(--fs-footnote);
  color: var(--text-soft);
  background: var(--fill-tertiary);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-weight: 400;
}

.penalty-grid {
  margin-top: var(--sp-2);
  padding: var(--sp-4) var(--sp-4) var(--sp-3);
  background: var(--fill-quaternary);
  border-radius: var(--radius-md);
  border: 1px solid var(--separator);
  overflow: hidden;
}

.penalty-hint {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: var(--fs-footnote);
  color: var(--text-soft);
  margin-bottom: var(--sp-4);
  line-height: 1.6;
  padding: var(--sp-2) var(--sp-3);
  background: var(--fill-tertiary);
  border-radius: var(--radius-sm);
}

.penalty-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px var(--sp-4);
}

.penalty-item {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: 7px var(--sp-2);
  border-radius: var(--radius-sm);
  transition: background 0.12s;
}

.penalty-item:hover {
  background: var(--fill-tertiary);
}

.penalty-item.is-modified {
  background: rgba(0, 122, 255, 0.06);
}

.severity-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 1.5px rgba(0, 0, 0, 0.06);
}

.penalty-label {
  display: flex;
  flex-direction: column;
  gap: 1px;
  flex: 1;
  min-width: 0;
}

.penalty-name {
  font-size: var(--fs-subheadline);
  font-weight: 500;
  color: var(--text-main);
  white-space: nowrap;
}

.penalty-desc {
  font-size: 11px;
  color: var(--text-soft);
  line-height: 1.45;
  word-break: break-all;
}

.penalty-control {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  min-width: 122px;
  justify-content: flex-end;
}

.penalty-control :deep(.el-input-number) {
  width: 98px;
  flex: 0 0 98px;
}

.penalty-control :deep(.el-input-number__decrease),
.penalty-control :deep(.el-input-number__increase) {
  width: 24px;
}

.penalty-control :deep(.el-input-number .el-input__wrapper) {
  padding-left: 28px;
  padding-right: 28px;
}

.penalty-control :deep(.el-input-number .el-input__inner) {
  font-variant-numeric: tabular-nums;
  text-align: center;
}

.penalty-reset-btn {
  width: 22px;
  height: 22px;
  border: none;
  background: var(--fill-secondary);
  border-radius: var(--radius-xs);
  cursor: pointer;
  color: var(--text-soft);
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: background 0.12s, color 0.12s;
  padding: 0;
}

.penalty-reset-btn:hover {
  background: var(--fill-primary);
  color: var(--text-main);
}

.penalty-footer {
  margin-top: var(--sp-3);
  padding-top: var(--sp-3);
  border-top: 1px solid var(--separator);
  display: flex;
  justify-content: flex-end;
}

.penalty-reset-all {
  border: none;
  background: none;
  cursor: pointer;
  font-size: var(--fs-footnote);
  color: var(--text-soft);
  font-family: inherit;
  padding: 4px var(--sp-2);
  border-radius: var(--radius-xs);
  transition: color 0.12s, background 0.12s;
}

.penalty-reset-all:hover {
  color: var(--danger);
  background: rgba(255, 59, 48, 0.08);
}

/* expand / collapse transition */
.penalty-expand-enter-active,
.penalty-expand-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
  transform-origin: top;
}

.penalty-expand-enter-from,
.penalty-expand-leave-to {
  opacity: 0;
  transform: scaleY(0.95);
}

/* ─── Viz Row ─────────────────────────────────────── */
.viz-row {
  display: flex;
  justify-content: center;
  margin: 8px 0 12px;
}

/* ─── Step Result Items ────────────────────────────── */
.step-result-item {
  padding: var(--sp-3) 0;
  border-bottom: 1px solid var(--separator-light, var(--separator));
}

.step-result-item:last-child {
  border-bottom: none;
}

.step-result-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.step-result-title {
  font-size: var(--fs-callout);
  font-weight: 600;
  color: var(--text-primary);
}

.step-result-meta {
  font-size: var(--fs-footnote);
  color: var(--text-soft);
  line-height: 1.7;
}

.debug-step-box + .debug-step-box {
  margin-top: var(--sp-1);
}

.debug-step-box .detail-title {
  font-size: var(--fs-callout);
  line-height: 1.5;
  margin-bottom: var(--sp-3);
}

.debug-step-box .detail-text + .detail-text {
  margin-top: 6px;
}

.manual-segmentation-box,
.demo-video-box,
.preprocess-editor-box {
  margin-top: var(--sp-4);
  padding: 18px var(--sp-5);
  border-radius: 14px;
  background: var(--info-fill);
  border: 1px solid rgba(0, 122, 255, 0.14);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.manual-title {
  font-weight: 600;
  color: var(--text-main);
  font-size: 14px;
}

.manual-subtitle,
.muted-text {
  font-size: var(--fs-caption1);
  color: var(--text-faint);
  line-height: 1.7;
}

.manual-btn {
  align-self: flex-start;
  border-radius: var(--radius-full) !important;
}

.frame-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: var(--sp-3);
  margin-top: var(--sp-4);
}

.frame {
  width: 100%;
  height: 100px;
  object-fit: cover;
  border-radius: 10px;
  background: var(--surface-secondary);
}

/* ── Config Form ─────────────────────────────────────────── */

.config-form {
  margin-top: var(--sp-4);
}

/* ── Review Radio — segmented control style ──────────────── */

:deep(.review-radio-group) {
  background: var(--fill-tertiary);
  border-radius: 11px;
  padding: 3px;
  display: inline-flex;
  gap: 3px;
}

:deep(.review-radio-group .el-radio-button) {
  flex: 1;
}

:deep(.review-radio-group .el-radio-button__inner) {
  border: none !important;
  border-radius: var(--radius-sm) !important;
  background: transparent !important;
  color: var(--text-soft) !important;
  font-size: 14px;
  font-weight: 500;
  min-width: 100px;
  height: 38px;
  line-height: 38px;
  padding: 0 14px;
  transition: background var(--duration-short), color var(--duration-short), box-shadow var(--duration-short);
  box-shadow: none !important;
}

:deep(.review-radio-group .el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--accent) !important;
  color: #fff !important;
  font-weight: 600 !important;
  box-shadow: 0 1px 6px rgba(0, 122, 255, 0.35) !important;
}

/* ── Hamburger Button ────────────────────────────────────── */

.hamburger-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: var(--touch-target);
  height: var(--touch-target);
  border: none;
  background: var(--fill-quaternary);
  color: var(--text-main);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 20px;
  transition: background var(--duration-short);
}

.hamburger-btn:hover {
  background: var(--fill-secondary);
}

/* ── Sidebar Backdrop ───────────────────────────────────── */

.sidebar-backdrop {
  display: none;
}

/* ── Responsive ──────────────────────────────────────────── */

@media (max-width: 1100px) {
  .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 768px) {
  .hamburger-btn {
    display: flex;
  }

  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.3);
    z-index: 99;
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--duration-medium) var(--ease-standard);
  }

  .sidebar-backdrop.is-open {
    opacity: 1;
    pointer-events: auto;
  }

  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: var(--sidebar-width);
    z-index: 100;
    transform: translateX(-100%);
    transition: transform var(--duration-medium) var(--ease-spring);
  }

  .sidebar.is-open {
    transform: translateX(0);
  }

  .main-container { overflow: visible; margin-left: 0; }
  .content-area { padding: var(--sp-4); }

  .filter-toolbar,
  .filter-form,
  .filter-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-input,
  .filter-select,
  .filter-sort {
    width: 100%;
  }

  .top-header {
    padding: var(--sp-4);
    height: auto;
    flex-direction: row;
    flex-wrap: wrap;
    gap: var(--sp-3);
  }

  .header-left {
    flex: 1;
    flex-direction: column;
    gap: var(--sp-1);
  }

  .header-right {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .stats-grid { grid-template-columns: 1fr; }
  .form-row { flex-direction: column; }
}

@media (prefers-reduced-motion: reduce) {
  .nav-item,
  .logout-btn,
  .stat-card,
  .sidebar,
  .sidebar-backdrop {
    transition: none;
  }
}
</style>
