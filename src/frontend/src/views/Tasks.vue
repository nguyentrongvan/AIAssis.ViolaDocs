<template>
  <div class="tasks-page">
    <h1 class="page-header">Tasks</h1>
      <div class="task-filters">
        <button @click="filter = 'pending'" :class="['filter-btn', { active: filter === 'pending' }]">Pending</button>
        <button @click="filter = 'completed'" :class="['filter-btn', { active: filter === 'completed' }]">Completed</button>
        <button @click="filter = 'all'" :class="['filter-btn', { active: filter === 'all' }]">All</button>
      </div>
      <div v-if="tasks.length === 0" class="empty-state">
        No tasks found
      </div>
      <div v-else class="task-list">
        <div v-for="task in filteredTasks" :key="task.id" class="task-item">
          <div class="task-info">
            <h3>{{ task.document?.title || 'Untitled' }}</h3>
            <p class="meta">Workflow: {{ task.workflow?.template }} • Due: {{ formatDate(task.due_at) }}</p>
            <p class="description">{{ task.description }}</p>
          </div>
          <div class="task-actions">
            <button @click="approveTask(task)" class="btn-primary">Approve</button>
            <button @click="rejectTask(task)" class="btn-danger">Reject</button>
            <button @click="viewDocument(task.document_id)" class="btn-secondary">View Doc</button>
          </div>
        </div>
      </div>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'

const router = useRouter()
const tasks = ref([])
const filter = ref('pending')

const filteredTasks = computed(() => {
  if (filter.value === 'all') return tasks.value
  return tasks.value.filter(t => t.status === filter.value)
})

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
  } catch (e) {
    console.error('Failed to approve task', e)
  }
}

const rejectTask = async (task) => {
  try {
    await api.post(`/tasks/${task.id}/action`, { action: 'reject' })
    await loadTasks()
  } catch (e) {
    console.error('Failed to reject task', e)
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
  max-width: 1200px;
  margin: 0 auto;
}
.task-filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}
.filter-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}
.filter-btn.active {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}
.task-list {
  display: grid;
  gap: 1.5rem;
}
.task-item {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 1.5rem;
  align-items: center;
}
.task-info h3 {
  margin: 0 0 0.5rem 0;
}
.meta {
  color: #666;
  font-size: 0.9rem;
  margin: 0.25rem 0;
}
.description {
  margin-top: 0.5rem;
  color: #333;
}
.task-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.empty-state {
  text-align: center;
  padding: 3rem;
  color: #666;
}
</style>

