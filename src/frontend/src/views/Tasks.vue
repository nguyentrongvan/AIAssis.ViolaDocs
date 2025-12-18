<template>
  <div class="tasks-page">
    <h1 class="page-header">{{ $t('tasks.title') }}</h1>
      <div class="task-filters">
        <button 
          v-for="filterOption in filterOptions" 
          :key="filterOption.value"
          @click="filter = filterOption.value" 
          :class="['filter-btn', { active: filter === filterOption.value }]"
        >
          {{ filterOption.label }}
        </button>
      </div>
      <div v-if="tasks.length === 0" class="empty-state">
        <div class="empty-icon">
          <CheckSquare :size="64" />
        </div>
        <h3>{{ $t('tasks.noTasks') }}</h3>
        <p>{{ $t('tasks.noTasksMatching') }}</p>
      </div>
      <div v-else class="task-list">
        <div v-for="task in filteredTasks" :key="task.id" class="task-item">
          <div class="task-info">
            <div class="task-header">
              <h3>{{ task.document?.title || $t('common.unknown') }}</h3>
              <StatusBadge :status="task.state || 'pending'" :label="getStatusLabel(task.state)" />
            </div>
            <p class="meta">
              <span>{{ $t('tasks.workflow') }}: {{ task.workflow?.template || $t('common.na') }}</span>
              <span v-if="task.due_at">• {{ $t('tasks.due') }}: {{ formatDate(task.due_at) }}</span>
              <span v-if="task.assignee">• {{ $t('tasks.assignee') }}: {{ task.assignee.name }}</span>
            </p>
            <p v-if="task.description" class="description">{{ task.description }}</p>
            <div v-if="task.comment" class="task-comment">
              <strong>{{ $t('tasks.comment') }}:</strong> {{ task.comment }}
            </div>
          </div>
          <div class="task-actions">
            <button 
              v-if="task.state === 'pending' || task.state === 'changes_requested'"
              @click="approveTask(task)" 
              class="btn-primary"
            >
              <Check :size="16" />
              {{ $t('tasks.approve') }}
            </button>
            <button 
              v-if="task.state === 'pending' || task.state === 'changes_requested'"
              @click="rejectTask(task)" 
              class="btn-danger"
            >
              <X :size="16" />
              {{ $t('tasks.reject') }}
            </button>
            <button 
              v-if="task.state === 'pending'"
              @click="requestChanges(task)" 
              class="btn-secondary"
            >
              <Edit :size="16" />
              {{ $t('tasks.requestChanges') }}
            </button>
            <button @click="viewDocument(task.document_id)" class="btn-secondary">
              <FileText :size="16" />
              {{ $t('tasks.viewDoc') }}
            </button>
          </div>
        </div>
      </div>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../services/api'
import { StatusBadge } from '../components'
import { CheckSquare, Check, X, Edit, FileText } from 'lucide-vue-next'

const { t } = useI18n()

const router = useRouter()
const tasks = ref([])
const filter = ref('all')

const filterOptions = computed(() => {
  const { t } = useI18n()
  return [
    { value: 'all', label: t('tasks.all') },
    { value: 'pending', label: t('tasks.pending') },
    { value: 'approved', label: t('tasks.approved') },
    { value: 'rejected', label: t('tasks.rejected') },
    { value: 'changes_requested', label: t('tasks.changesRequested') },
    { value: 'in_progress', label: t('tasks.inProgress') },
    { value: 'completed', label: t('tasks.completed') }
  ]
})

const filteredTasks = computed(() => {
  if (filter.value === 'all') return tasks.value
  return tasks.value.filter(t => (t.state || 'pending') === filter.value)
})

const getStatusLabel = (state) => {
  const { t } = useI18n()
  const labels = {
    'pending': t('tasks.pending'),
    'approved': t('tasks.approved'),
    'rejected': t('tasks.rejected'),
    'changes_requested': t('tasks.changesRequested'),
    'in_progress': t('tasks.inProgress'),
    'completed': t('tasks.completed')
  }
  return labels[state] || state
}

onMounted(async () => {
  await loadTasks()
})

const loadTasks = async () => {
  try {
    const res = await api.get('/tasks')
    if (res.is_success) {
      tasks.value = res.data || []
    }
  } catch (e) {
    console.error('Failed to load tasks', e)
  }
}

const approveTask = async (task) => {
  try {
    await api.post(`/tasks/${task.id}/action`, { action: 'approve' })
    await loadTasks()
    if (window.$toast) {
      window.$toast.show(t('tasks.taskApproved'), 'success')
    }
  } catch (e) {
    console.error('Failed to approve task', e)
    if (window.$toast) {
      window.$toast.show(t('tasks.failedToApprove'), 'error')
    }
  }
}

const rejectTask = async (task) => {
  try {
    const comment = prompt(t('tasks.rejectReason'))
    if (comment !== null) {
      await api.post(`/tasks/${task.id}/action`, { action: 'reject', comment })
      await loadTasks()
      if (window.$toast) {
        window.$toast.show(t('tasks.taskRejected'), 'success')
      }
    }
  } catch (e) {
    console.error('Failed to reject task', e)
    if (window.$toast) {
      window.$toast.show(t('tasks.failedToReject'), 'error')
    }
  }
}

const requestChanges = async (task) => {
  try {
    const comment = prompt(t('tasks.changesNeeded'))
    if (comment !== null) {
      await api.post(`/tasks/${task.id}/action`, { action: 'request_changes', comment })
      await loadTasks()
      if (window.$toast) {
        window.$toast.show(t('tasks.changesRequestedSuccess'), 'success')
      }
    }
  } catch (e) {
    console.error('Failed to request changes', e)
    if (window.$toast) {
      window.$toast.show(t('tasks.failedToRequestChanges'), 'error')
    }
  }
}

const viewDocument = (docId) => {
  router.push(`/documents/${docId}`)
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleDateString()
}
</script>

<style scoped>
.tasks-page {
  max-width: 1400px;
  margin: 0 auto;
  animation: fadeIn var(--transition-base) var(--ease-out);
}

.task-filters {
  display: flex;
  gap: var(--space-sm);
  margin-bottom: var(--space-xl);
  flex-wrap: wrap;
}

.filter-btn {
  padding: var(--space-md) var(--space-lg);
  border: 2px solid rgba(0, 0, 0, 0.1);
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-base);
  font-weight: 500;
  font-size: 0.95rem;
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
}

.filter-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: var(--gradient-ai-soft);
  transition: left var(--transition-base);
  z-index: 0;
}

.filter-btn:hover::before {
  left: 0;
}

.filter-btn:hover {
  border-color: var(--ai-cyan);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.filter-btn.active {
  background: var(--gradient-primary);
  color: white;
  border-color: var(--primary);
  box-shadow: var(--shadow-lg), var(--shadow-glow);
  position: relative;
  z-index: 1;
}

.filter-btn.active::before {
  display: none;
}

.task-list {
  display: grid;
  gap: var(--space-xl);
}

.task-item {
  background: var(--bg-white);
  padding: var(--space-xl);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--space-xl);
  align-items: flex-start;
  border: 2px solid transparent;
  transition: all var(--transition-base);
  position: relative;
  overflow: hidden;
  animation: fadeInUp var(--transition-base) var(--ease-out) both;
}

.task-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gradient-cyan-purple);
  transform: scaleX(0);
  transition: transform var(--transition-base);
}

.task-item:hover::before {
  transform: scaleX(1);
}

.task-item:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-2xl), var(--shadow-glow);
  border-color: var(--ai-cyan);
}

.task-info {
  flex: 1;
}

.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
  flex-wrap: wrap;
}

.task-info h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-dark);
  flex: 1;
  min-width: 0;
}

.meta {
  color: var(--text-medium);
  font-size: 0.9rem;
  margin: var(--space-sm) 0;
  display: flex;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.meta span {
  white-space: nowrap;
}

.description {
  margin-top: var(--space-md);
  color: var(--text-dark);
  line-height: 1.6;
}

.task-comment {
  margin-top: var(--space-md);
  padding: var(--space-md);
  background: var(--gradient-ai-soft);
  border-radius: var(--radius-lg);
  border-left: 3px solid var(--ai-cyan);
  font-size: 0.9rem;
  line-height: 1.6;
}

.task-comment strong {
  color: var(--primary);
}

.task-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  min-width: 150px;
}

.task-actions button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  white-space: nowrap;
}

.empty-state {
  text-align: center;
  padding: var(--space-3xl);
  color: var(--text-medium);
  animation: fadeInUp var(--transition-base) var(--ease-out);
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

/* Responsive */
@media (max-width: 768px) {
  .task-item {
    grid-template-columns: 1fr;
    gap: var(--space-lg);
  }
  
  .task-actions {
    flex-direction: row;
    flex-wrap: wrap;
    min-width: auto;
  }
  
  .task-actions button {
    flex: 1;
    min-width: 120px;
  }
}
</style>

