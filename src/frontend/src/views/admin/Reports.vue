<template>
  <div class="admin-page">
    <h1 class="page-header">{{ $t('admin.reports.title') }}</h1>

    <div class="reports-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        :class="['tab-btn', { 'tab-btn-active': activeTab === tab.id }]"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="report-filters">
      <div class="filter-row">
        <div class="filter-group">
          <label>{{ $t('admin.reports.filters.dateFrom') }}</label>
          <input v-model="filters.date_from" type="date" />
        </div>
        <div class="filter-group">
          <label>{{ $t('admin.reports.filters.dateTo') }}</label>
          <input v-model="filters.date_to" type="date" />
        </div>
        
        <!-- Audit-specific filters -->
        <template v-if="activeTab === 'audit'">
          <div class="filter-group">
            <label>{{ $t('admin.reports.filters.actor') }}</label>
            <select v-model.number="filters.actor_id">
              <option :value="null">{{ $t('admin.reports.filterOptions.allUsers') }}</option>
              <option v-for="user in users" :key="user.id" :value="user.id">
                {{ user.name }}
              </option>
            </select>
          </div>
          <div class="filter-group">
            <label>{{ $t('admin.reports.filters.action') }}</label>
            <select v-model="filters.action">
              <option value="">{{ $t('admin.reports.filterOptions.allActions') }}</option>
              <option value="create">{{ $t('admin.reports.filterOptions.create') }}</option>
              <option value="update">{{ $t('admin.reports.filterOptions.update') }}</option>
              <option value="delete">{{ $t('admin.reports.filterOptions.delete') }}</option>
              <option value="share">{{ $t('admin.reports.filterOptions.share') }}</option>
              <option value="view">{{ $t('admin.reports.filterOptions.view') }}</option>
              <option value="search">{{ $t('admin.reports.filterOptions.search') }}</option>
              <option value="vector_search">{{ $t('admin.reports.filterOptions.vectorSearch') }}</option>
            </select>
          </div>
          <div class="filter-group">
            <label>{{ $t('admin.reports.filters.pageSize') }}</label>
            <select v-model.number="filters.page_size">
              <option :value="25">25</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </div>
        </template>

        <!-- Usage-specific filters -->
        <template v-if="activeTab === 'usage'">
          <div class="filter-group">
            <label>{{ $t('admin.reports.filters.rollup') }}</label>
            <select v-model="filters.rollup">
              <option value="hour">{{ $t('admin.reports.filterOptions.hour') }}</option>
              <option value="day">{{ $t('admin.reports.filterOptions.day') }}</option>
              <option value="week">{{ $t('admin.reports.filterOptions.week') }}</option>
            </select>
          </div>
          <div class="filter-group">
            <label>{{ $t('admin.reports.filters.topN') }}</label>
            <select v-model.number="filters.top_n">
              <option :value="5">{{ $t('admin.reports.filterOptions.top5') }}</option>
              <option :value="10">{{ $t('admin.reports.filterOptions.top10') }}</option>
              <option :value="20">{{ $t('admin.reports.filterOptions.top20') }}</option>
            </select>
          </div>
        </template>

        <!-- Workflow-specific filters -->
        <template v-if="activeTab === 'workflow'">
          <div class="filter-group">
            <label>{{ $t('admin.reports.filters.template') }}</label>
            <input v-model="filters.template" type="text" :placeholder="$t('admin.reports.filterByTemplate')" />
          </div>
          <div class="filter-group">
            <label>{{ $t('admin.reports.filters.assignee') }}</label>
            <select v-model.number="filters.assignee_id">
              <option :value="null">{{ $t('admin.reports.filterOptions.allAssignees') }}</option>
              <option v-for="user in users" :key="user.id" :value="user.id">
                {{ user.name }}
              </option>
            </select>
          </div>
        </template>

        <div class="filter-actions">
          <button @click="applyDatePreset('today')" class="btn-secondary btn-sm">{{ $t('admin.reports.buttons.today') }}</button>
          <button @click="applyDatePreset('7d')" class="btn-secondary btn-sm">{{ $t('admin.reports.buttons.last7Days') }}</button>
          <button @click="applyDatePreset('30d')" class="btn-secondary btn-sm">{{ $t('admin.reports.buttons.last30Days') }}</button>
          <button @click="generateReport" class="btn-primary" :disabled="loading">
            <RefreshCw v-if="loading" :size="16" class="spinning" />
            {{ $t('admin.reports.buttons.generate') }}
          </button>
          <button 
            v-if="activeTab === 'audit' && reportData" 
            @click="exportReport" 
            class="btn-secondary"
            :disabled="!reportData"
          >
            <Download :size="16" />
            {{ $t('admin.reports.buttons.export') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">{{ $t('admin.reports.messages.generatingReport') }}</div>
    <div v-else-if="reportData" class="report-content">
      <!-- Audit Report -->
      <div v-if="activeTab === 'audit'" class="report-section">
        <div class="report-summary">
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.totalEvents') }}</div>
            <div class="summary-value">{{ reportData.total || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.uniqueUsers') }}</div>
            <div class="summary-value">{{ reportData.unique_users || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.uniqueDocuments') }}</div>
            <div class="summary-value">{{ reportData.unique_documents || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.actionTypes') }}</div>
            <div class="summary-value">{{ Object.keys(reportData.action_counts || {}).length }}</div>
          </div>
        </div>

        <!-- Charts -->
        <div class="charts-grid">
          <div class="chart-card">
            <h3>{{ $t('admin.reports.charts.eventsTimeline') }}</h3>
            <LineChart 
              v-if="auditTimelineData" 
              :data="auditTimelineData" 
              :options="timelineChartOptions"
            />
          </div>
          <div class="chart-card">
            <h3>{{ $t('admin.reports.charts.actionDistribution') }}</h3>
            <PieChart 
              v-if="auditActionData" 
              :data="auditActionData" 
              :options="pieChartOptions"
            />
          </div>
          <div class="chart-card">
            <h3>{{ $t('admin.reports.charts.topActors') }}</h3>
            <BarChart 
              v-if="auditTopActorsData" 
              :data="auditTopActorsData" 
              :options="barChartOptions"
            />
          </div>
        </div>

        <!-- Table with pagination -->
        <div class="report-table-container">
          <table class="report-table">
            <thead>
              <tr>
                <th>{{ $t('admin.reports.tableHeaders.timestamp') }}</th>
                <th>{{ $t('admin.reports.tableHeaders.actor') }}</th>
                <th>{{ $t('admin.reports.tableHeaders.action') }}</th>
                <th>{{ $t('admin.reports.tableHeaders.resourceType') }}</th>
                <th>{{ $t('admin.reports.tableHeaders.resourceId') }}</th>
                <th>{{ $t('admin.reports.tableHeaders.document') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in reportData.items" :key="item.id">
                <td>{{ formatDate(item.timestamp) }}</td>
                <td>{{ item.actor_name || $t('common.unknown') }}</td>
                <td><StatusBadge :status="item.action" /></td>
                <td>{{ item.subject_type }}</td>
                <td>{{ item.subject_id || $t('common.na') }}</td>
                <td>{{ item.document_title || $t('common.na') }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="reportData.pagination" class="pagination-controls">
            <button 
              @click="changePage(reportData.pagination.page - 1)"
              :disabled="reportData.pagination.page <= 1"
              class="btn-secondary"
            >
              {{ $t('admin.reports.buttons.previous') }}
            </button>
            <span class="page-info">
              {{ $t('admin.reports.pagination.pageOf', { page: reportData.pagination.page, totalPages: reportData.pagination.total_pages }) }}
              {{ $t('admin.reports.pagination.total', { total: reportData.pagination.total }) }}
            </span>
            <button 
              @click="changePage(reportData.pagination.page + 1)"
              :disabled="reportData.pagination.page >= reportData.pagination.total_pages"
              class="btn-secondary"
            >
              {{ $t('admin.reports.buttons.next') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Usage Report -->
      <div v-if="activeTab === 'usage'" class="report-section">
        <div class="report-summary">
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.totalDocuments') }}</div>
            <div class="summary-value">{{ reportData.total_documents || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.totalStorage') }}</div>
            <div class="summary-value">{{ formatSize(reportData.total_storage || 0) }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.uploads') }}</div>
            <div class="summary-value">{{ reportData.uploads_count || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.searchQueries') }}</div>
            <div class="summary-value">{{ reportData.search_queries || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.vectorQueries') }}</div>
            <div class="summary-value">{{ reportData.vector_queries || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.chatbotSessions') }}</div>
            <div class="summary-value">{{ reportData.chatbot_sessions || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.queueDepth') }}</div>
            <div class="summary-value">{{ reportData.queue_depth || 0 }}</div>
          </div>
        </div>

        <!-- Charts -->
        <div class="charts-grid">
          <div class="chart-card">
            <h3>{{ $t('admin.reports.charts.uploadsOverTime') }}</h3>
            <LineChart 
              v-if="usageUploadsData" 
              :data="usageUploadsData" 
              :options="timelineChartOptions"
            />
          </div>
          <div class="chart-card">
            <h3>{{ $t('admin.reports.charts.storageByFolder') }}</h3>
            <BarChart 
              v-if="usageFoldersData" 
              :data="usageFoldersData" 
              :options="barChartOptions"
            />
          </div>
          <div class="chart-card">
            <h3>{{ $t('admin.reports.charts.storageByTag') }}</h3>
            <PieChart 
              v-if="usageTagsData" 
              :data="usageTagsData" 
              :options="pieChartOptions"
            />
          </div>
          <div class="chart-card">
            <h3>{{ $t('admin.reports.charts.searchVsVectorQueries') }}</h3>
            <DualLineChart 
              v-if="usageSearchData" 
              :data="usageSearchData" 
              :options="dualLineChartOptions"
            />
          </div>
        </div>

        <!-- Breakdown Tables -->
        <div class="breakdown-grid">
          <div class="breakdown-section">
            <h3>{{ $t('admin.reports.charts.storageByFolder') }}</h3>
            <table class="breakdown-table">
              <thead>
                <tr>
                  <th>{{ $t('admin.reports.tableHeaders.folder') }}</th>
                  <th>{{ $t('admin.reports.tableHeaders.documents') }}</th>
                  <th>{{ $t('admin.reports.tableHeaders.size') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in reportData.breakdown?.folders || []" :key="item.folder_id">
                  <td>{{ item.name || $t('admin.reports.messages.root') }}</td>
                  <td>{{ item.count }}</td>
                  <td>{{ formatSize(item.size) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="breakdown-section">
            <h3>{{ $t('admin.reports.charts.storageByTag') }}</h3>
            <table class="breakdown-table">
              <thead>
                <tr>
                  <th>{{ $t('admin.reports.tableHeaders.tag') }}</th>
                  <th>{{ $t('admin.reports.tableHeaders.documents') }}</th>
                  <th>{{ $t('admin.reports.tableHeaders.size') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in reportData.breakdown?.tags || []" :key="item.tag_id">
                  <td>{{ item.name }}</td>
                  <td>{{ item.count }}</td>
                  <td>{{ formatSize(item.size) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="breakdown-section">
            <h3>{{ $t('admin.reports.tableHeaders.group') }}</h3>
            <table class="breakdown-table">
              <thead>
                <tr>
                  <th>{{ $t('admin.reports.tableHeaders.group') }}</th>
                  <th>{{ $t('admin.reports.tableHeaders.documents') }}</th>
                  <th>{{ $t('admin.reports.tableHeaders.size') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in reportData.breakdown?.groups || []" :key="item.group_id">
                  <td>{{ item.name }}</td>
                  <td>{{ item.count }}</td>
                  <td>{{ formatSize(item.size) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="breakdown-section">
            <h3>{{ $t('admin.reports.tableHeaders.user') }}</h3>
            <table class="breakdown-table">
              <thead>
                <tr>
                  <th>{{ $t('admin.reports.tableHeaders.user') }}</th>
                  <th>{{ $t('admin.reports.tableHeaders.uploads') }}</th>
                  <th>{{ $t('admin.reports.tableHeaders.size') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in reportData.breakdown?.users || []" :key="item.user_id">
                  <td>{{ item.name }}</td>
                  <td>{{ item.uploads }}</td>
                  <td>{{ formatSize(item.size) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Workflow Report -->
      <div v-if="activeTab === 'workflow'" class="report-section">
        <div class="report-summary">
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.totalWorkflows') }}</div>
            <div class="summary-value">{{ reportData.total_workflows || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.completed') }}</div>
            <div class="summary-value">{{ reportData.completed || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.pending') }}</div>
            <div class="summary-value">{{ reportData.pending || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.overdue') }}</div>
            <div class="summary-value">{{ reportData.overdue || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.avgDuration') }}</div>
            <div class="summary-value">{{ reportData.avg_duration_hours?.toFixed(1) || '0' }}h</div>
          </div>
        </div>

        <!-- Charts -->
        <div class="charts-grid">
          <div class="chart-card">
            <h3>{{ $t('admin.reports.charts.approvalRatesByTemplate') }}</h3>
            <BarChart 
              v-if="workflowTemplateData" 
              :data="workflowTemplateData" 
              :options="barChartOptions"
            />
          </div>
          <div class="chart-card">
            <h3>{{ $t('admin.reports.charts.approvalRatesByAssignee') }}</h3>
            <BarChart 
              v-if="workflowAssigneeData" 
              :data="workflowAssigneeData" 
              :options="barChartOptions"
            />
          </div>
          <div class="chart-card">
            <h3>{{ $t('admin.reports.charts.workflowStateDistribution') }}</h3>
            <PieChart 
              v-if="workflowStateData" 
              :data="workflowStateData" 
              :options="pieChartOptions"
            />
          </div>
          <div class="chart-card">
            <h3>{{ $t('admin.reports.charts.durationDistribution') }}</h3>
            <BarChart 
              v-if="workflowDurationData" 
              :data="workflowDurationData" 
              :options="barChartOptions"
            />
          </div>
        </div>

        <!-- Tables -->
        <div class="breakdown-grid">
          <div class="breakdown-section">
            <h3>{{ $t('admin.reports.summary.overdue') }}</h3>
            <table class="breakdown-table">
              <thead>
                <tr>
                  <th>{{ $t('admin.reports.tableHeaders.assignee') }}</th>
                  <th>{{ $t('admin.reports.filters.template') }}</th>
                  <th>{{ $t('admin.reports.tableHeaders.dueDate') }}</th>
                  <th>{{ $t('admin.reports.tableHeaders.daysOverdue') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="task in reportData.overdue_tasks || []" :key="task.task_id">
                  <td>{{ task.assignee_name }}</td>
                  <td>{{ task.template || $t('common.na') }}</td>
                  <td>{{ formatDate(task.due_at) }}</td>
                  <td>{{ task.days_overdue }}</td>
                </tr>
                <tr v-if="!reportData.overdue_tasks || reportData.overdue_tasks.length === 0">
                  <td colspan="4" class="text-center">{{ $t('admin.reports.messages.noOverdueTasks') }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Quality Report -->
      <div v-if="activeTab === 'quality'" class="report-section">
        <div class="report-summary">
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.indexFailures') }}</div>
            <div class="summary-value">{{ reportData.index_failures || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.embeddingFailures') }}</div>
            <div class="summary-value">{{ reportData.embedding_failures || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.ocrFailures') }}</div>
            <div class="summary-value">{{ reportData.ocr_failures || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.staleDocuments') }}</div>
            <div class="summary-value">{{ reportData.stale_documents || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.purgeBacklog') }}</div>
            <div class="summary-value">{{ reportData.purge_backlog || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">{{ $t('admin.reports.summary.virusScanFailures') }}</div>
            <div class="summary-value">{{ reportData.virus_scan_failures || 0 }}</div>
          </div>
        </div>

        <!-- Charts -->
        <div class="charts-grid">
          <div class="chart-card">
            <h3>{{ $t('admin.reports.charts.failureTypesDistribution') }}</h3>
            <PieChart 
              v-if="qualityFailureTypesData" 
              :data="qualityFailureTypesData" 
              :options="pieChartOptions"
            />
          </div>
          <div class="chart-card">
            <h3>{{ $t('admin.reports.charts.failuresOverTime') }}</h3>
            <LineChart 
              v-if="qualityFailureTimelineData" 
              :data="qualityFailureTimelineData" 
              :options="timelineChartOptions"
            />
          </div>
          <div class="chart-card">
            <h3>{{ $t('admin.reports.charts.jobStatusBreakdown') }}</h3>
            <PieChart 
              v-if="qualityJobStatusData" 
              :data="qualityJobStatusData" 
              :options="pieChartOptions"
            />
          </div>
        </div>

        <!-- Recent Failures Table -->
        <div class="failures-section">
          <h3>{{ $t('admin.reports.messages.recentFailures') }}</h3>
          <table class="report-table">
            <thead>
              <tr>
                <th>{{ $t('admin.reports.tableHeaders.jobType') }}</th>
                <th>{{ $t('admin.reports.tableHeaders.documentId') }}</th>
                <th>{{ $t('admin.reports.tableHeaders.error') }}</th>
                <th>{{ $t('admin.reports.tableHeaders.timestamp') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="failure in reportData.recent_failures || []" :key="failure.id">
                <td>{{ failure.job_type }}</td>
                <td>{{ failure.document_id || $t('common.na') }}</td>
                <td class="error-text">{{ failure.error }}</td>
                <td>{{ formatDate(failure.created_at) }}</td>
              </tr>
              <tr v-if="!reportData.recent_failures || reportData.recent_failures.length === 0">
                <td colspan="4" class="text-center">{{ $t('admin.reports.messages.noRecentFailures') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    <div v-else-if="!loading" class="empty-state">
      {{ $t('admin.reports.messages.selectFiltersAndGenerate') }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { reportsAPI, usersAPI } from '../../services/api'
import { StatusBadge, LineChart, BarChart, PieChart, DualLineChart } from '../../components'
import { RefreshCw, Download } from 'lucide-vue-next'

const { t } = useI18n()

const activeTab = ref('audit')
const loading = ref(false)
const reportData = ref(null)
const users = ref([])
const currentPage = ref(1)

const tabs = computed(() => [
  { id: 'audit', label: t('admin.reports.tabs.auditLog') },
  { id: 'usage', label: t('admin.reports.tabs.usageStatistics') },
  { id: 'workflow', label: t('admin.reports.tabs.workflowSla') },
  { id: 'quality', label: t('admin.reports.tabs.dataQuality') }
])

const filters = ref({
  date_from: null,
  date_to: null,
  actor_id: null,
  action: '',
  page_size: 50,
  rollup: 'day',
  top_n: 10,
  template: '',
  assignee_id: null
})

// Chart data computed properties
const auditTimelineData = computed(() => {
  if (!reportData.value?.timeline_data) return null
  return {
    labels: reportData.value.timeline_data.map(d => d.date),
    datasets: [{
      label: t('admin.reports.chartLabels.events'),
      data: reportData.value.timeline_data.map(d => d.count),
      borderColor: 'rgb(75, 192, 192)',
      backgroundColor: 'rgba(75, 192, 192, 0.2)',
      tension: 0.1
    }]
  }
})

const auditActionData = computed(() => {
  if (!reportData.value?.action_counts) return null
  const counts = reportData.value.action_counts
  return {
    labels: Object.keys(counts),
    datasets: [{
      data: Object.values(counts),
      backgroundColor: [
        'rgba(255, 99, 132, 0.6)',
        'rgba(54, 162, 235, 0.6)',
        'rgba(255, 206, 86, 0.6)',
        'rgba(75, 192, 192, 0.6)',
        'rgba(153, 102, 255, 0.6)',
        'rgba(255, 159, 64, 0.6)'
      ]
    }]
  }
})

const auditTopActorsData = computed(() => {
  if (!reportData.value?.top_actors) return null
  return {
    labels: reportData.value.top_actors.map(a => a.name),
    datasets: [{
      label: t('admin.reports.chartLabels.events'),
      data: reportData.value.top_actors.map(a => a.count),
      backgroundColor: 'rgba(54, 162, 235, 0.6)'
    }]
  }
})

const usageUploadsData = computed(() => {
  if (!reportData.value?.time_series) return null
  return {
    labels: reportData.value.time_series.map(d => d.date),
    datasets: [{
      label: t('admin.reports.chartLabels.uploads'),
      data: reportData.value.time_series.map(d => d.uploads),
      borderColor: 'rgb(75, 192, 192)',
      backgroundColor: 'rgba(75, 192, 192, 0.2)',
      tension: 0.1
    }]
  }
})

const usageFoldersData = computed(() => {
  if (!reportData.value?.breakdown?.folders) return null
  const folders = reportData.value.breakdown.folders.slice(0, 10)
  return {
    labels: folders.map(f => f.name || t('admin.reports.messages.root')),
    datasets: [{
      label: t('admin.reports.chartLabels.sizeBytes'),
      data: folders.map(f => f.size),
      backgroundColor: 'rgba(54, 162, 235, 0.6)'
    }]
  }
})

const usageTagsData = computed(() => {
  if (!reportData.value?.breakdown?.tags) return null
  return {
    labels: reportData.value.breakdown.tags.map(t => t.name),
    datasets: [{
      data: reportData.value.breakdown.tags.map(t => t.size),
      backgroundColor: [
        'rgba(255, 99, 132, 0.6)',
        'rgba(54, 162, 235, 0.6)',
        'rgba(255, 206, 86, 0.6)',
        'rgba(75, 192, 192, 0.6)',
        'rgba(153, 102, 255, 0.6)'
      ]
    }]
  }
})

const usageSearchData = computed(() => {
  // This would need to be calculated from time series if available
  // For now, return null as we don't have search query time series
  return null
})

const workflowTemplateData = computed(() => {
  if (!reportData.value?.approval_rates?.by_template) return null
  return {
    labels: reportData.value.approval_rates.by_template.map(t => t.template),
    datasets: [{
      label: t('admin.reports.chartLabels.approvalRate'),
      data: reportData.value.approval_rates.by_template.map(t => (t.rate * 100).toFixed(1)),
      backgroundColor: 'rgba(75, 192, 192, 0.6)'
    }]
  }
})

const workflowAssigneeData = computed(() => {
  if (!reportData.value?.approval_rates?.by_assignee) return null
  return {
    labels: reportData.value.approval_rates.by_assignee.map(a => a.name),
    datasets: [{
      label: t('admin.reports.chartLabels.approvalRate'),
      data: reportData.value.approval_rates.by_assignee.map(a => (a.rate * 100).toFixed(1)),
      backgroundColor: 'rgba(54, 162, 235, 0.6)'
    }]
  }
})

const workflowStateData = computed(() => {
  if (!reportData.value) return null
  return {
    labels: [
      t('admin.reports.workflowStates.completed'),
      t('admin.reports.workflowStates.pending'),
      t('admin.reports.workflowStates.rejected')
    ],
    datasets: [{
      data: [
        reportData.value.completed || 0,
        reportData.value.pending || 0,
        reportData.value.rejected || 0
      ],
      backgroundColor: [
        'rgba(75, 192, 192, 0.6)',
        'rgba(255, 206, 86, 0.6)',
        'rgba(255, 99, 132, 0.6)'
      ]
    }]
  }
})

const workflowDurationData = computed(() => {
  if (!reportData.value?.duration_distribution) return null
  return {
    labels: reportData.value.duration_distribution.map(d => d.range),
    datasets: [{
      label: t('admin.reports.chartLabels.count'),
      data: reportData.value.duration_distribution.map(d => d.count),
      backgroundColor: 'rgba(153, 102, 255, 0.6)'
    }]
  }
})

const qualityFailureTypesData = computed(() => {
  if (!reportData.value) return null
  return {
    labels: [
      t('admin.reports.failureTypes.embedding'),
      t('admin.reports.failureTypes.ocr'),
      t('admin.reports.failureTypes.virusScan')
    ],
    datasets: [{
      data: [
        reportData.value.embedding_failures || 0,
        reportData.value.ocr_failures || 0,
        reportData.value.virus_scan_failures || 0
      ],
      backgroundColor: [
        'rgba(255, 99, 132, 0.6)',
        'rgba(54, 162, 235, 0.6)',
        'rgba(255, 206, 86, 0.6)'
      ]
    }]
  }
})

const qualityFailureTimelineData = computed(() => {
  if (!reportData.value?.failure_timeline) return null
  // Group by date
  const grouped = {}
  reportData.value.failure_timeline.forEach(item => {
    if (!grouped[item.date]) {
      grouped[item.date] = 0
    }
    grouped[item.date] += item.count
  })
  return {
    labels: Object.keys(grouped),
    datasets: [{
      label: t('admin.reports.chartLabels.failures'),
      data: Object.values(grouped),
      borderColor: 'rgb(255, 99, 132)',
      backgroundColor: 'rgba(255, 99, 132, 0.2)',
      tension: 0.1
    }]
  }
})

const qualityJobStatusData = computed(() => {
  if (!reportData.value?.job_status_breakdown) return null
  return {
    labels: Object.keys(reportData.value.job_status_breakdown),
    datasets: [{
      data: Object.values(reportData.value.job_status_breakdown),
      backgroundColor: [
        'rgba(75, 192, 192, 0.6)',
        'rgba(255, 206, 86, 0.6)',
        'rgba(255, 99, 132, 0.6)',
        'rgba(153, 102, 255, 0.6)'
      ]
    }]
  }
})

// Chart options
const timelineChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: true }
  },
  scales: {
    y: { beginAtZero: true }
  }
}

const barChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false }
  },
  scales: {
    y: { beginAtZero: true }
  }
}

const pieChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'right' }
  }
}

const dualLineChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: true }
  },
  scales: {
    y: { position: 'left', beginAtZero: true },
    y1: { position: 'right', beginAtZero: true, grid: { drawOnChartArea: false } }
  }
}

onMounted(async () => {
  await loadUsers()
})

const loadUsers = async () => {
  try {
    const res = await usersAPI.list()
    if (res.is_success) {
      users.value = res.data || []
    }
  } catch (e) {
    console.error('Failed to load users', e)
  }
}

const applyDatePreset = (preset) => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  
  switch (preset) {
    case 'today':
      filters.value.date_from = today.toISOString().split('T')[0]
      filters.value.date_to = today.toISOString().split('T')[0]
      break
    case '7d':
      const sevenDaysAgo = new Date(today)
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
      filters.value.date_from = sevenDaysAgo.toISOString().split('T')[0]
      filters.value.date_to = today.toISOString().split('T')[0]
      break
    case '30d':
      const thirtyDaysAgo = new Date(today)
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
      filters.value.date_from = thirtyDaysAgo.toISOString().split('T')[0]
      filters.value.date_to = today.toISOString().split('T')[0]
      break
  }
}

const changePage = (page) => {
  currentPage.value = page
  generateReport()
}

const generateReport = async () => {
  loading.value = true
  reportData.value = null
  try {
    const params = {}
    if (filters.value.date_from) {
      params.from_date = filters.value.date_from
    }
    if (filters.value.date_to) {
      params.to_date = filters.value.date_to
    }

    switch (activeTab.value) {
      case 'audit':
        if (filters.value.actor_id) params.actor_id = filters.value.actor_id
        if (filters.value.action) params.action = filters.value.action
        params.page = currentPage.value
        params.size = filters.value.page_size
        break
      case 'usage':
        params.rollup = filters.value.rollup
        params.top_n = filters.value.top_n
        break
      case 'workflow':
        if (filters.value.template) params.template = filters.value.template
        if (filters.value.assignee_id) params.assignee_id = filters.value.assignee_id
        break
    }

    let res
    switch (activeTab.value) {
      case 'audit':
        res = await reportsAPI.audit(params)
        break
      case 'usage':
        res = await reportsAPI.usage(params)
        break
      case 'workflow':
        res = await reportsAPI.workflow(params)
        break
      case 'quality':
        res = await reportsAPI.quality(params)
        break
    }

    if (res.is_success) {
      reportData.value = res.data
    }
  } catch (e) {
    console.error('Failed to generate report', e)
    if (window.$toast) {
      window.$toast.show(t('admin.reports.failedToGenerateReport'), 'error')
    }
  } finally {
    loading.value = false
  }
}

const exportReport = async () => {
  if (!reportData.value || activeTab.value !== 'audit') return
  try {
    const params = {
      from_date: filters.value.date_from,
      to_date: filters.value.date_to,
      actor_id: filters.value.actor_id,
      action: filters.value.action,
      format: 'csv'
    }

    const res = await reportsAPI.exportAudit(params)
    
    const url = window.URL.createObjectURL(new Blob([res]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `audit_report_${Date.now()}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    
    if (window.$toast) {
      window.$toast.show(t('admin.reports.reportExported'), 'success')
    }
  } catch (e) {
    console.error('Failed to export report', e)
    if (window.$toast) {
      window.$toast.show(t('admin.reports.failedToExportReport'), 'error')
    }
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB'
  return (bytes / 1024 / 1024 / 1024).toFixed(1) + ' GB'
}

// Reset page when tab changes
watch(activeTab, () => {
  currentPage.value = 1
  reportData.value = null
})
</script>

<style scoped>
.admin-page {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.reports-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  border-bottom: 2px solid #eee;
}

.tab-btn {
  padding: 0.75rem 1.5rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-weight: 500;
  color: #666;
  transition: all 0.2s;
  margin-bottom: -2px;
}

.tab-btn:hover {
  color: var(--primary);
}

.tab-btn-active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.report-filters {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid #eee;
}

.filter-row {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  flex-direction: column;
  min-width: 150px;
}

.filter-group label {
  margin-bottom: 0.5rem;
  font-weight: 500;
  font-size: 0.9rem;
}

.filter-group input,
.filter-group select {
  padding: var(--space-md) var(--space-lg);
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-lg);
  background: var(--bg-white);
  font-size: 0.95rem;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.filter-group input:focus,
.filter-group select:focus {
  outline: none;
  border-color: var(--ai-cyan);
  box-shadow: var(--shadow-md), 0 0 0 3px rgba(0, 217, 255, 0.1);
}

.filter-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.btn-sm {
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.report-content {
  margin-top: 2rem;
}

.report-section {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.report-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.summary-card {
  background: var(--bg-light);
  padding: 1.5rem;
  border-radius: 8px;
  text-align: center;
}

.summary-label {
  font-size: 0.9rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.summary-value {
  font-size: 2rem;
  font-weight: bold;
  color: var(--primary);
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.5rem;
}

.chart-card {
  background: var(--bg-light);
  padding: 1.5rem;
  border-radius: 8px;
}

.chart-card h3 {
  margin: 0 0 1rem 0;
  color: var(--primary);
  font-size: 1.1rem;
}

.report-table-container {
  overflow-x: auto;
  background: var(--bg-light);
  padding: 1.5rem;
  border-radius: 8px;
}

.report-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.report-table th,
.report-table td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.report-table th {
  background: var(--bg-light);
  font-weight: 600;
  color: var(--primary);
}

.report-table tr:hover {
  background: var(--bg-light);
}

.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
}

.page-info {
  font-size: 0.9rem;
  color: #666;
}

.breakdown-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.breakdown-section {
  background: var(--bg-light);
  padding: 1.5rem;
  border-radius: 8px;
}

.breakdown-section h3 {
  margin: 0 0 1rem 0;
  color: var(--primary);
}

.breakdown-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 6px;
  overflow: hidden;
}

.breakdown-table th,
.breakdown-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #eee;
  font-size: 0.9rem;
}

.breakdown-table th {
  background: var(--bg-light);
  font-weight: 600;
  color: var(--primary);
}

.failures-section {
  background: var(--bg-light);
  padding: 1.5rem;
  border-radius: 8px;
}

.failures-section h3 {
  margin: 0 0 1rem 0;
  color: var(--primary);
}

.error-text {
  font-family: monospace;
  font-size: 0.85rem;
  color: #ef4444;
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.text-center {
  text-align: center;
}

.loading,
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #666;
}
</style>
