<template>
  <div class="ai-jobs-page">
    <div class="page-header">
      <h1>{{ $t('admin.aiJobs.title') }}</h1>
      <button @click="refreshJobs" class="btn-primary" :disabled="loading">
        <RefreshCw :size="20" :class="{ spinning: loading }" />
        {{ $t('common.refresh') }}
      </button>
    </div>

    <!-- Filters -->
    <div class="filters-bar glass">
      <div class="filter-group">
        <label>{{ $t('admin.aiJobs.filters.jobType') }}</label>
        <select v-model="filters.job_type">
          <option value="">{{ $t('admin.aiJobs.filterOptions.allTypes') }}</option>
          <option value="ocr">{{ $t('admin.aiJobs.filterOptions.ocr') }}</option>
          <option value="embed">{{ $t('admin.aiJobs.filterOptions.embedding') }}</option>
          <option value="classify">{{ $t('admin.aiJobs.filterOptions.classify') }}</option>
          <option value="qa">{{ $t('admin.aiJobs.filterOptions.qa') }}</option>
        </select>
      </div>
      <div class="filter-group">
        <label>{{ $t('admin.aiJobs.filters.status') }}</label>
        <select v-model="filters.status">
          <option value="">{{ $t('admin.aiJobs.filterOptions.allStatus') }}</option>
          <option value="queued">{{ $t('admin.aiJobs.filterOptions.queued') }}</option>
          <option value="processing">{{ $t('admin.aiJobs.filterOptions.processing') }}</option>
          <option value="completed">{{ $t('admin.aiJobs.filterOptions.completed') }}</option>
          <option value="failed">{{ $t('admin.aiJobs.filterOptions.failed') }}</option>
        </select>
      </div>
      <div class="filter-group">
        <label>{{ $t('admin.aiJobs.filters.provider') }}</label>
        <select v-model="filters.provider">
          <option value="">{{ $t('admin.aiJobs.filterOptions.allProviders') }}</option>
          <option value="tesseract">{{ $t('admin.aiJobs.filterOptions.tesseract') }}</option>
          <option value="ollama">{{ $t('admin.aiJobs.filterOptions.ollama') }}</option>
        </select>
      </div>
      <div class="filter-actions">
        <button @click="applyFilters" class="btn-primary">{{ $t('admin.aiJobs.buttons.apply') }}</button>
        <button @click="clearFilters" class="btn-secondary">{{ $t('admin.aiJobs.buttons.clear') }}</button>
      </div>
    </div>

    <!-- Jobs Table -->
    <div class="jobs-table-container">
      <div v-if="loading && jobs.length === 0" class="loading-state">
        <LoadingSpinner :text="$t('admin.aiJobs.messages.loadingAiJobs')" />
      </div>
      <div v-else-if="jobs.length === 0" class="empty-state">
        <div class="empty-icon">
          <Activity :size="64" />
        </div>
        <h3>{{ $t('admin.aiJobs.messages.noAiJobsFound') }}</h3>
        <p>{{ $t('admin.aiJobs.messages.noJobsMatchFilters') }}</p>
      </div>
      <div v-else class="jobs-table glass">
        <table>
          <thead>
            <tr>
              <th>{{ $t('admin.aiJobs.tableHeaders.id') }}</th>
              <th>{{ $t('admin.aiJobs.tableHeaders.jobType') }}</th>
              <th>{{ $t('admin.aiJobs.tableHeaders.target') }}</th>
              <th>{{ $t('admin.aiJobs.tableHeaders.provider') }}</th>
              <th>{{ $t('admin.aiJobs.tableHeaders.status') }}</th>
              <th>{{ $t('admin.aiJobs.tableHeaders.worker') }}</th>
              <th>{{ $t('admin.aiJobs.tableHeaders.retries') }}</th>
              <th>{{ $t('admin.aiJobs.tableHeaders.output') }}</th>
              <th>{{ $t('admin.aiJobs.tableHeaders.error') }}</th>
              <th>{{ $t('admin.aiJobs.tableHeaders.createdAt') }}</th>
              <th>{{ $t('admin.aiJobs.tableHeaders.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in jobs" :key="job.id" class="job-row">
              <td>{{ job.id }}</td>
              <td>
                <span class="job-type-badge" :class="`type-${job.job_type}`">
                  {{ job.job_type.toUpperCase() }}
                </span>
              </td>
              <td>
                <div class="target-info">
                  <span v-if="job.target?.document_id">{{ $t('admin.aiJobs.messages.document') }} {{ job.target.document_id }}</span>
                  <span v-if="job.target?.version_id">{{ $t('admin.aiJobs.messages.version') }} {{ job.target.version_id }}</span>
                </div>
              </td>
              <td>{{ job.provider || $t('common.na') }}</td>
              <td>
                <StatusBadge :status="job.status" />
              </td>
              <td>
                <div v-if="job.worker_id" class="worker-info">
                  <span class="worker-id">{{ job.worker_id }}</span>
                  <span v-if="job.claimed_at" class="claimed-time">
                    {{ formatTime(job.claimed_at) }}
                  </span>
                </div>
                <span v-else class="text-muted">-</span>
              </td>
              <td>
                <span v-if="job.retry_count > 0" class="retry-badge">
                  {{ job.retry_count }}/{{ job.max_retries }}
                </span>
                <span v-else class="text-muted">0</span>
              </td>
              <td>
                <div v-if="job.output_ref" class="output-preview">
                  <button @click="viewOutput(job)" class="btn-link-small">
                    <FileText :size="14" />
                    {{ $t('admin.aiJobs.buttons.view') }}
                  </button>
                </div>
                <span v-else class="text-muted">-</span>
              </td>
              <td>
                <div v-if="job.error" class="error-message" :title="job.error">
                  <AlertTriangle :size="14" />
                  {{ truncateText(job.error, 50) }}
                </div>
                <span v-else class="text-muted">-</span>
              </td>
              <td>
                <div class="date-time">
                  <span class="time">{{ formatTime(job.created_at) }}</span>
                  <span class="date">{{ formatDateOnly(job.created_at) }}</span>
                </div>
              </td>
              <td>
                <div class="action-buttons">
                  <button @click="viewJobDetails(job)" class="btn-action btn-details">
                    <Eye :size="16" />
                    <span>{{ $t('admin.aiJobs.buttons.details') }}</span>
                  </button>
                  <button 
                    v-if="job.status === 'queued' || job.status === 'processing'"
                    @click="cancelJob(job.id)" 
                    class="btn-action btn-cancel"
                    :disabled="cancellingJobs.includes(job.id)"
                  >
                    <X :size="16" />
                    <span>{{ $t('admin.aiJobs.buttons.cancel') }}</span>
                  </button>
                  <button 
                    v-if="job.status === 'failed' || job.status === 'completed' || job.status === 'cancelled'"
                    @click="reprocessJob(job.id)" 
                    class="btn-action btn-reprocess"
                    :disabled="reprocessingJobs.includes(job.id)"
                  >
                    <RefreshCw :size="16" />
                    <span>{{ $t('admin.aiJobs.buttons.reprocess') }}</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="total > 0" class="pagination-container">
        <div class="pagination-info">
          <span class="pagination-text">
            {{ $t('admin.aiJobs.messages.showingJobs', { 
              start: (currentPage - 1) * limit + 1, 
              end: Math.min(currentPage * limit, total), 
              total: total 
            }) }}
          </span>
        </div>
        <Pagination
          :current-page="currentPage"
          :total-items="total"
          :items-per-page="limit"
          @page-change="handlePageChange"
        />
      </div>
    </div>

    <!-- Job Details Modal -->
    <Modal v-model:show="showDetailsModal" :title="t('admin.aiJobs.aiJobTitle', { id: selectedJob?.id || '' })">
      <div v-if="selectedJob" class="job-details">
        <div class="detail-section">
          <h3>{{ $t('admin.aiJobs.basicInformation') }}</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>{{ $t('admin.aiJobs.type') }}:</label>
              <span>{{ selectedJob.job_type }}</span>
            </div>
            <div class="detail-item">
              <label>{{ $t('admin.aiJobs.status') }}:</label>
              <StatusBadge :status="selectedJob.status" />
            </div>
            <div class="detail-item">
              <label>{{ $t('admin.aiJobs.provider') }}:</label>
              <span>{{ selectedJob.provider || $t('common.na') }}</span>
            </div>
            <div class="detail-item">
              <label>{{ $t('admin.aiJobs.createdAt') }}:</label>
              <span>{{ formatDate(selectedJob.created_at) }}</span>
            </div>
            <div class="detail-item">
              <label>{{ $t('admin.aiJobs.updatedAt') }}:</label>
              <span>{{ formatDate(selectedJob.updated_at) }}</span>
            </div>
            <div v-if="selectedJob.worker_id" class="detail-item">
              <label>{{ $t('admin.aiJobs.workerId') }}:</label>
              <span>{{ selectedJob.worker_id }}</span>
            </div>
            <div v-if="selectedJob.claimed_at" class="detail-item">
              <label>{{ $t('admin.aiJobs.claimedAt') }}:</label>
              <span>{{ formatDate(selectedJob.claimed_at) }}</span>
            </div>
            <div class="detail-item">
              <label>{{ $t('admin.aiJobs.retryCount') }}:</label>
              <span>{{ selectedJob.retry_count || 0 }} / {{ selectedJob.max_retries || 3 }}</span>
            </div>
          </div>
        </div>
        
        <div class="detail-section">
          <h3>{{ $t('common.actions') }}</h3>
          <div class="action-buttons-horizontal">
            <button 
              v-if="selectedJob.status === 'queued' || selectedJob.status === 'processing'"
              @click="cancelJob(selectedJob.id); showDetailsModal = false" 
              class="btn-action btn-cancel"
              :disabled="cancellingJobs.includes(selectedJob.id)"
            >
              <X :size="16" />
              {{ $t('admin.aiJobs.cancelJob') }}
            </button>
            <button 
              v-if="selectedJob.status === 'failed' || selectedJob.status === 'completed' || selectedJob.status === 'cancelled'"
              @click="reprocessJob(selectedJob.id); showDetailsModal = false" 
              class="btn-action btn-reprocess"
              :disabled="reprocessingJobs.includes(selectedJob.id)"
            >
              <RefreshCw :size="16" />
              {{ $t('admin.aiJobs.reprocessJob') }}
            </button>
          </div>
        </div>

        <div class="detail-section">
          <h3>{{ $t('admin.aiJobs.target') }}</h3>
          <pre class="json-view">{{ JSON.stringify(selectedJob.target, null, 2) }}</pre>
        </div>

        <div v-if="selectedJob.input_ref" class="detail-section">
          <h3>{{ $t('admin.aiJobs.inputReference') }}</h3>
          <pre class="json-view">{{ JSON.stringify(selectedJob.input_ref, null, 2) }}</pre>
        </div>

        <div v-if="selectedJob.output_ref" class="detail-section">
          <h3>{{ $t('admin.aiJobs.outputReference') }}</h3>
          <pre class="json-view">{{ JSON.stringify(selectedJob.output_ref, null, 2) }}</pre>
        </div>

        <div v-if="selectedJob.error" class="detail-section">
          <h3>{{ $t('common.error') }}</h3>
          <div class="error-box">
            <AlertTriangle :size="20" />
            <pre>{{ selectedJob.error }}</pre>
          </div>
        </div>
      </div>
      <template #footer>
        <button @click="showDetailsModal = false" class="btn-secondary">{{ $t('common.close') }}</button>
      </template>
    </Modal>

    <!-- Output View Modal -->
    <Modal v-model:show="showOutputModal" :title="$t('admin.aiJobs.jobOutput')">
      <div v-if="selectedOutput" class="output-view">
        <pre class="json-view">{{ JSON.stringify(selectedOutput, null, 2) }}</pre>
      </div>
      <template #footer>
        <button @click="showOutputModal = false" class="btn-secondary">{{ $t('common.close') }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { aiAPI } from '../../services/api'
import { Modal, StatusBadge, Pagination, LoadingSpinner } from '../../components'
import { RefreshCw, Activity, FileText, AlertTriangle, Eye } from 'lucide-vue-next'

const { t } = useI18n()

const jobs = ref([])
const loading = ref(false)
const total = ref(0)
const limit = ref(20)
const offset = ref(0)
const currentPage = ref(1)
const showDetailsModal = ref(false)
const showOutputModal = ref(false)
const selectedJob = ref(null)
const selectedOutput = ref(null)
const cancellingJobs = ref([])
const reprocessingJobs = ref([])
let refreshInterval = null

const filters = ref({
  job_type: '',
  status: '',
  provider: ''
})

onMounted(async () => {
  await loadJobs()
  // Auto refresh every 5 seconds
  refreshInterval = setInterval(() => {
    if (!loading.value) {
      loadJobs()
    }
  }, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

const loadJobs = async () => {
  loading.value = true
  try {
    const params = {
      limit: limit.value,
      offset: offset.value
    }
    if (filters.value.job_type) params.job_type = filters.value.job_type
    if (filters.value.status) params.status_filter = filters.value.status
    if (filters.value.provider) params.provider = filters.value.provider

    const res = await aiAPI.listJobs(params)
    if (res.is_success) {
      jobs.value = res.data.jobs || []
      total.value = res.data.total || 0
    }
  } catch (e) {
    console.error('Failed to load AI jobs', e)
    if (window.$toast) {
      window.$toast.show(t('admin.aiJobs.failedToLoadAiJobs'), 'error')
    }
  } finally {
    loading.value = false
  }
}

const refreshJobs = async () => {
  await loadJobs()
  if (window.$toast) {
    window.$toast.show(t('admin.aiJobs.jobsRefreshed'), 'success')
  }
}

const applyFilters = async () => {
  currentPage.value = 1
  offset.value = 0
  await loadJobs()
}

const clearFilters = () => {
  filters.value = {
    job_type: '',
    status: '',
    provider: ''
  }
  applyFilters()
}

const handlePageChange = (page) => {
  currentPage.value = page
  offset.value = (page - 1) * limit.value
  loadJobs()
}

const viewJobDetails = (job) => {
  selectedJob.value = job
  showDetailsModal.value = true
}

const viewOutput = (job) => {
  selectedOutput.value = job.output_ref
  showOutputModal.value = true
}

const formatDate = (dateStr) => {
  if (!dateStr) return t('common.na')
  return new Date(dateStr).toLocaleString()
}

const formatTime = (dateStr) => {
  if (!dateStr) return t('common.na')
  return new Date(dateStr).toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit',
    hour12: false 
  })
}

const formatDateOnly = (dateStr) => {
  if (!dateStr) return t('common.na')
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: '2-digit',
    day: '2-digit',
    year: 'numeric'
  })
}

const truncateText = (text, maxLength) => {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

const cancelJob = async (jobId) => {
  if (!confirm(t('admin.aiJobs.cancelJobConfirm'))) {
    return
  }
  
  cancellingJobs.value.push(jobId)
  try {
    const res = await aiAPI.cancelJob(jobId)
    if (res.is_success) {
      if (window.$toast) {
        window.$toast.show(t('admin.aiJobs.jobCancelled'), 'success')
      }
      await loadJobs()
    }
  } catch (e) {
    console.error('Failed to cancel job', e)
    const errorMsg = e.response?.data?.message || e.message || t('admin.aiJobs.failedToCancelJob')
    if (window.$toast) {
      window.$toast.show(errorMsg, 'error')
    }
  } finally {
    cancellingJobs.value = cancellingJobs.value.filter(id => id !== jobId)
  }
}

const reprocessJob = async (jobId) => {
  if (!confirm(t('admin.aiJobs.reprocessJobConfirm'))) {
    return
  }
  
  reprocessingJobs.value.push(jobId)
  try {
    const res = await aiAPI.reprocessJob(jobId)
    if (res.is_success) {
      if (window.$toast) {
        window.$toast.show(t('admin.aiJobs.jobQueuedForReprocessing'), 'success')
      }
      await loadJobs()
    }
  } catch (e) {
    console.error('Failed to reprocess job', e)
    const errorMsg = e.response?.data?.message || e.message || t('admin.aiJobs.failedToReprocessJob')
    if (window.$toast) {
      window.$toast.show(errorMsg, 'error')
    }
  } finally {
    reprocessingJobs.value = reprocessingJobs.value.filter(id => id !== jobId)
  }
}
</script>

<style scoped>
.ai-jobs-page {
  max-width: 1600px;
  margin: 0 auto;
  animation: fadeIn var(--transition-base) var(--ease-out);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-xl);
}

.page-header h1 {
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.page-header .btn-primary {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-xl);
  background: var(--gradient-primary);
  color: white;
  border: none;
  border-radius: var(--radius-lg);
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-md), var(--shadow-glow);
  position: relative;
  overflow: hidden;
}

.page-header .btn-primary::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 0.5s;
}

.page-header .btn-primary:hover::before {
  left: 100%;
}

.page-header .btn-primary:hover {
  transform: translateY(-2px) scale(1.02);
  box-shadow: var(--shadow-xl), var(--shadow-glow-ai);
}

.page-header .btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.filters-bar {
  display: flex;
  gap: var(--space-lg);
  padding: var(--space-xl);
  border-radius: var(--radius-xl);
  margin-bottom: var(--space-xl);
  flex-wrap: wrap;
  align-items: flex-end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  min-width: 150px;
}

.filter-group label {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-dark);
}

.filter-group select {
  padding: var(--space-md) var(--space-lg);
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-lg);
  background: var(--bg-white);
  font-size: 0.95rem;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  font-weight: 500;
  color: var(--text-dark);
}

.filter-group select:hover {
  border-color: var(--ai-cyan);
  box-shadow: var(--shadow-md);
}

.filter-group select:focus {
  outline: none;
  border-color: var(--ai-cyan);
  box-shadow: var(--shadow-md), 0 0 0 3px rgba(0, 217, 255, 0.1);
  background: var(--bg-white);
}

.filter-actions {
  display: flex;
  gap: var(--space-md);
  margin-left: auto;
}

.jobs-table-container {
  position: relative;
}

.loading-state,
.empty-state {
  text-align: center;
  padding: var(--space-3xl);
  color: var(--text-medium);
}

.empty-icon {
  margin: 0 auto var(--space-lg);
  width: 120px;
  height: 120px;
  border-radius: var(--radius-full);
  background: var(--gradient-ai-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
  opacity: 0.5;
}

.empty-state h3 {
  margin: 0 0 var(--space-sm) 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-dark);
}

.empty-state p {
  margin: 0;
  font-size: 1rem;
  color: var(--text-light);
}

.jobs-table {
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-2xl), var(--shadow-glow-ai);
  background: var(--bg-white);
  backdrop-filter: var(--glass-filter);
  border: var(--glass-border);
  position: relative;
}

.jobs-table::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gradient-cyan-purple);
  z-index: 1;
}

.jobs-table table {
  width: 100%;
  border-collapse: collapse;
  background: transparent;
}

.jobs-table thead {
  background: linear-gradient(135deg, rgba(0, 217, 255, 0.1) 0%, rgba(108, 92, 231, 0.1) 100%);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 10;
}

.jobs-table th {
  padding: var(--space-xl) var(--space-lg);
  text-align: left;
  font-weight: 700;
  font-size: 0.85rem;
  color: var(--text-dark);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  border-bottom: 2px solid rgba(0, 217, 255, 0.2);
  position: relative;
}

.jobs-table th::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--gradient-cyan-purple);
  transform: scaleX(0);
  transition: transform var(--transition-base);
}

.jobs-table thead:hover th::after {
  transform: scaleX(1);
}

.jobs-table td {
  padding: var(--space-xl) var(--space-lg);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  font-size: 0.9rem;
  vertical-align: middle;
}

.job-row {
  transition: all var(--transition-base);
  position: relative;
}

.job-row::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--gradient-cyan-purple);
  transform: scaleY(0);
  transition: transform var(--transition-base);
}

.job-row:hover {
  background: linear-gradient(90deg, var(--gradient-ai-soft) 0%, transparent 100%);
  transform: translateX(4px);
  box-shadow: var(--shadow-md);
}

.job-row:hover::before {
  transform: scaleY(1);
}

.job-type-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.375rem 0.875rem;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-base);
  position: relative;
  overflow: hidden;
}

.job-type-badge::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 0.5s;
}

.job-type-badge:hover::before {
  left: 100%;
}

.job-type-badge:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: var(--shadow-md);
}

.type-ocr {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.type-embed {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3);
}

.type-classify {
  background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(236, 72, 153, 0.3);
}

.type-qa {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.target-info {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  font-size: 0.85rem;
}

.target-info span {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.5rem;
  background: var(--gradient-ai-soft);
  border-radius: var(--radius-md);
  font-weight: 500;
  color: var(--text-dark);
  width: fit-content;
  box-shadow: var(--shadow-sm);
}

.output-preview {
  display: flex;
  align-items: center;
}

.output-preview .btn-link-small {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-sm);
  color: var(--ai-cyan);
  font-weight: 600;
  font-size: 0.85rem;
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
  background: transparent;
  border: none;
  cursor: pointer;
}

.output-preview .btn-link-small:hover {
  background: var(--gradient-ai-soft);
  color: var(--primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.error-message {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  color: #dc2626;
  font-size: 0.85rem;
  max-width: 200px;
  padding: var(--space-xs) var(--space-sm);
  background: linear-gradient(135deg, rgba(220, 38, 38, 0.1) 0%, rgba(239, 68, 68, 0.1) 100%);
  border-radius: var(--radius-md);
  border-left: 3px solid #dc2626;
  font-weight: 500;
}

.text-muted {
  color: var(--text-light);
  font-style: italic;
  opacity: 0.6;
}

.pagination-container {
  margin-top: var(--space-xl);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
}

.pagination-info {
  display: flex;
  align-items: center;
  justify-content: center;
}

.pagination-text {
  font-size: 0.9rem;
  color: var(--text-medium);
  font-weight: 500;
}

.job-details {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
}

.detail-section h3 {
  margin: 0 0 var(--space-md) 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--primary);
  border-bottom: 2px solid var(--gradient-ai-soft);
  padding-bottom: var(--space-sm);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-md);
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.detail-item label {
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--text-medium);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.detail-item span {
  font-size: 0.95rem;
  color: var(--text-dark);
}

.json-view {
  background: var(--bg-light);
  padding: var(--space-lg);
  border-radius: var(--radius-lg);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.error-box {
  display: flex;
  gap: var(--space-md);
  padding: var(--space-lg);
  background: #fee2e2;
  border-radius: var(--radius-lg);
  border-left: 4px solid var(--error);
  color: #991b1b;
}

.error-box pre {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.output-view {
  max-height: 500px;
  overflow: auto;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.action-buttons {
  display: flex;
  gap: var(--space-md);
  align-items: center;
  flex-wrap: wrap;
}

.btn-action {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-lg);
  border-radius: var(--radius-lg);
  font-size: 0.9rem;
  font-weight: 600;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
}

.btn-action::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 0.5s;
}

.btn-action:hover::before {
  left: 100%;
}

.btn-details {
  background: linear-gradient(135deg, var(--ai-cyan) 0%, var(--primary) 100%);
  color: white;
  border-color: var(--ai-cyan);
}

.btn-details:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: var(--shadow-lg), var(--shadow-glow-cyan);
  border-color: var(--ai-cyan);
}

.btn-cancel {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  border-color: #ef4444;
}

.btn-cancel:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.05);
  box-shadow: var(--shadow-lg), 0 0 20px rgba(239, 68, 68, 0.3);
  border-color: #ef4444;
}

.btn-reprocess {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border-color: #10b981;
}

.btn-reprocess:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.05);
  box-shadow: var(--shadow-lg), 0 0 20px rgba(16, 185, 129, 0.3);
  border-color: #10b981;
}

.btn-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-action span {
  white-space: nowrap;
}

.worker-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.85rem;
}

.worker-id {
  font-weight: 600;
  color: var(--text-dark);
  font-family: var(--font-mono);
}

.claimed-time {
  font-size: 0.75rem;
  color: var(--text-medium);
  opacity: 0.8;
}

.retry-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.5rem;
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.2) 0%, rgba(245, 158, 11, 0.2) 100%);
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 0.85rem;
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.action-buttons-horizontal {
  display: flex;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.date-time {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.date-time .time {
  font-weight: 700;
  color: var(--text-dark);
  font-size: 0.9rem;
  font-family: var(--font-mono);
  letter-spacing: 0.05em;
}

.date-time .date {
  font-size: 0.8rem;
  color: var(--text-medium);
  opacity: 0.8;
}

/* Responsive */
@media (max-width: 1024px) {
  .jobs-table {
    overflow-x: auto;
  }
  
  .jobs-table table {
    min-width: 1200px;
  }
}
</style>

