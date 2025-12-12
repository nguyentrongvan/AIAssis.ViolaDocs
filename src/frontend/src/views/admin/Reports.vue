<template>
  <div class="admin-page">
    <h1 class="page-header">Reports</h1>

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
          <label>Date From</label>
          <input v-model="filters.date_from" type="date" />
        </div>
        <div class="filter-group">
          <label>Date To</label>
          <input v-model="filters.date_to" type="date" />
        </div>
        <div v-if="activeTab === 'audit'" class="filter-group">
          <label>Actor</label>
          <select v-model.number="filters.actor_id">
            <option :value="null">All Users</option>
            <option v-for="user in users" :key="user.id" :value="user.id">
              {{ user.name }}
            </option>
          </select>
        </div>
        <div v-if="activeTab === 'audit'" class="filter-group">
          <label>Action</label>
          <select v-model="filters.action">
            <option value="">All Actions</option>
            <option value="create">Create</option>
            <option value="update">Update</option>
            <option value="delete">Delete</option>
            <option value="share">Share</option>
            <option value="view">View</option>
          </select>
        </div>
        <div class="filter-actions">
          <button @click="generateReport" class="btn-primary" :disabled="loading">
            <RefreshCw v-if="loading" :size="16" class="spinning" />
            Generate
          </button>
          <button @click="exportReport" class="btn-secondary" :disabled="!reportData">
            <Download :size="16" />
            Export
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">Generating report...</div>
    <div v-else-if="reportData" class="report-content">
      <!-- Audit Report -->
      <div v-if="activeTab === 'audit'" class="report-section">
        <div class="report-summary">
          <div class="summary-card">
            <div class="summary-label">Total Events</div>
            <div class="summary-value">{{ reportData.total || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">Unique Users</div>
            <div class="summary-value">{{ reportData.unique_users || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">Unique Documents</div>
            <div class="summary-value">{{ reportData.unique_documents || 0 }}</div>
          </div>
        </div>
        <div class="report-table-container">
          <table class="report-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in reportData.items" :key="item.id">
                <td>{{ formatDate(item.created_at) }}</td>
                <td>{{ item.actor?.name || 'Unknown' }}</td>
                <td><StatusBadge :status="item.action" /></td>
                <td>{{ item.resource_type }} #{{ item.resource_id }}</td>
                <td>{{ item.details || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Usage Report -->
      <div v-if="activeTab === 'usage'" class="report-section">
        <div class="report-summary">
          <div class="summary-card">
            <div class="summary-label">Total Documents</div>
            <div class="summary-value">{{ reportData.total_documents || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">Total Storage</div>
            <div class="summary-value">{{ formatSize(reportData.total_storage || 0) }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">Uploads</div>
            <div class="summary-value">{{ reportData.uploads_count || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">Search Queries</div>
            <div class="summary-value">{{ reportData.search_queries || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">Chatbot Sessions</div>
            <div class="summary-value">{{ reportData.chatbot_sessions || 0 }}</div>
          </div>
        </div>
        <div v-if="reportData.breakdown" class="breakdown-section">
          <h3>Breakdown by Folder</h3>
          <div class="breakdown-list">
            <div
              v-for="item in reportData.breakdown.folders"
              :key="item.folder_id"
              class="breakdown-item"
            >
              <span class="breakdown-label">{{ item.folder_name || 'Root' }}</span>
              <span class="breakdown-value">{{ item.count }} documents</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Workflow Report -->
      <div v-if="activeTab === 'workflow'" class="report-section">
        <div class="report-summary">
          <div class="summary-card">
            <div class="summary-label">Total Tasks</div>
            <div class="summary-value">{{ reportData.total_tasks || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">Pending</div>
            <div class="summary-value">{{ reportData.pending_tasks || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">Overdue</div>
            <div class="summary-value">{{ reportData.overdue_tasks || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">Avg Duration</div>
            <div class="summary-value">{{ reportData.avg_duration || 'N/A' }}</div>
          </div>
        </div>
        <div v-if="reportData.approval_rates" class="approval-section">
          <h3>Approval Rates</h3>
          <div class="approval-list">
            <div
              v-for="(rate, template) in reportData.approval_rates"
              :key="template"
              class="approval-item"
            >
              <span class="approval-label">{{ template }}</span>
              <div class="approval-bar">
                <div
                  class="approval-fill"
                  :style="{ width: (rate * 100) + '%' }"
                ></div>
                <span class="approval-value">{{ (rate * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Quality Report -->
      <div v-if="activeTab === 'quality'" class="report-section">
        <div class="report-summary">
          <div class="summary-card">
            <div class="summary-label">Failed Jobs</div>
            <div class="summary-value">{{ reportData.failed_jobs || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">Stale Index Count</div>
            <div class="summary-value">{{ reportData.stale_index_count || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">Purge Backlog</div>
            <div class="summary-value">{{ reportData.purge_backlog || 0 }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">Virus Scan Failures</div>
            <div class="summary-value">{{ reportData.virus_scan_failures || 0 }}</div>
          </div>
        </div>
        <div v-if="reportData.job_failures" class="failures-section">
          <h3>Recent Job Failures</h3>
          <div class="failures-list">
            <div
              v-for="failure in reportData.job_failures"
              :key="failure.id"
              class="failure-item"
            >
              <div class="failure-header">
                <span class="failure-type">{{ failure.job_type }}</span>
                <span class="failure-date">{{ formatDate(failure.created_at) }}</span>
              </div>
              <div class="failure-error">{{ failure.error }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-else-if="!loading" class="empty-state">
      Select filters and click Generate to view report
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { reportsAPI, usersAPI } from '../../services/api'
import { StatusBadge } from '../../components'
import { RefreshCw, Download } from 'lucide-vue-next'

const activeTab = ref('audit')
const loading = ref(false)
const reportData = ref(null)
const users = ref([])

const tabs = [
  { id: 'audit', label: 'Audit Log' },
  { id: 'usage', label: 'Usage Statistics' },
  { id: 'workflow', label: 'Workflow SLA' },
  { id: 'quality', label: 'Data Quality' }
]

const filters = ref({
  date_from: null,
  date_to: null,
  actor_id: null,
  action: ''
})

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
    if (filters.value.actor_id) {
      params.actor_id = filters.value.actor_id
    }
    if (filters.value.action) {
      params.action = filters.value.action
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
      window.$toast.show('Failed to generate report', 'error')
    }
  } finally {
    loading.value = false
  }
}

const exportReport = async () => {
  if (!reportData.value) return
  try {
    const params = {
      from_date: filters.value.date_from,
      to_date: filters.value.date_to,
      actor_id: filters.value.actor_id,
      action: filters.value.action
    }

    let res
    switch (activeTab.value) {
      case 'audit':
        res = await reportsAPI.exportAudit(params)
        break
      default:
        if (window.$toast) {
          window.$toast.show('Export not available for this report type', 'info')
        }
        return
    }

    const url = window.URL.createObjectURL(new Blob([res]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `report_${activeTab.value}_${Date.now()}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    if (window.$toast) {
      window.$toast.show('Report exported', 'success')
    }
  } catch (e) {
    console.error('Failed to export report', e)
    if (window.$toast) {
      window.$toast.show('Failed to export report', 'error')
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

.filter-group input[type="date"] {
  padding-right: var(--space-xl);
  cursor: pointer;
  position: relative;
}

.filter-group input[type="date"]::-webkit-calendar-picker-indicator {
  cursor: pointer;
  opacity: 0.6;
  filter: grayscale(1);
  transition: all var(--transition-base);
  padding: var(--space-xs);
  border-radius: var(--radius-sm);
}

.filter-group input[type="date"]::-webkit-calendar-picker-indicator:hover {
  opacity: 1;
  filter: grayscale(0);
  background: var(--gradient-ai-soft);
}

.filter-group input:focus,
.filter-group select:focus {
  outline: none;
  border-color: var(--ai-cyan);
  box-shadow: var(--shadow-md), 0 0 0 3px rgba(0, 217, 255, 0.1);
}

.filter-group input[type="date"]:focus::-webkit-calendar-picker-indicator {
  opacity: 1;
  filter: grayscale(0);
}

.filter-actions {
  display: flex;
  gap: 0.5rem;
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

.report-table-container {
  overflow-x: auto;
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

.breakdown-section,
.approval-section,
.failures-section {
  background: var(--bg-light);
  padding: 1.5rem;
  border-radius: 8px;
}

.breakdown-section h3,
.approval-section h3,
.failures-section h3 {
  margin: 0 0 1rem 0;
  color: var(--primary);
}

.breakdown-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.breakdown-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem;
  background: white;
  border-radius: 6px;
}

.breakdown-label {
  font-weight: 500;
}

.breakdown-value {
  color: #666;
}

.approval-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.approval-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.approval-label {
  font-weight: 500;
}

.approval-bar {
  position: relative;
  height: 24px;
  background: white;
  border-radius: 12px;
  overflow: hidden;
}

.approval-fill {
  height: 100%;
  background: var(--primary);
  transition: width 0.3s;
}

.approval-value {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.85rem;
  font-weight: 600;
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.failures-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.failure-item {
  background: white;
  padding: 1rem;
  border-radius: 6px;
  border-left: 4px solid #ef4444;
}

.failure-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.failure-type {
  font-weight: 600;
  color: #ef4444;
}

.failure-date {
  font-size: 0.85rem;
  color: #666;
}

.failure-error {
  font-size: 0.9rem;
  color: #666;
  font-family: monospace;
}

.loading,
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #666;
}
</style>
