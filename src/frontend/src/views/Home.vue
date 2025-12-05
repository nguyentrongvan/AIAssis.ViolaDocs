<template>
  <Layout>
    <template #header>
      <h1>Document Library</h1>
    </template>
    <div class="home-page">
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{{ stats.totalDocuments || 0 }}</div>
          <div class="stat-label">Total Documents</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.pendingTasks || 0 }}</div>
          <div class="stat-label">Pending Tasks</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.recentUploads || 0 }}</div>
          <div class="stat-label">Recent Uploads</div>
        </div>
      </div>
      <div class="quick-actions">
        <router-link to="/upload" class="action-card">
          <div class="action-icon">📤</div>
          <div class="action-title">Upload Documents</div>
        </router-link>
        <router-link to="/search" class="action-card">
          <div class="action-icon">🔍</div>
          <div class="action-title">Search</div>
        </router-link>
        <router-link to="/chatbot" class="action-card">
          <div class="action-icon">💬</div>
          <div class="action-title">Chatbot</div>
        </router-link>
        <router-link to="/tasks" class="action-card">
          <div class="action-icon">✅</div>
          <div class="action-title">Tasks</div>
        </router-link>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Layout from '../components/Layout.vue'
import api from '../services/api'

const stats = ref({
  totalDocuments: 0,
  pendingTasks: 0,
  recentUploads: 0
})

onMounted(async () => {
  // Load stats
  try {
    const res = await api.get('/reports/usage')
    if (res.is_success && res.data) {
      stats.value = {
        totalDocuments: res.data.total_documents || 0,
        pendingTasks: res.data.pending_tasks || 0,
        recentUploads: res.data.recent_uploads || 0
      }
    }
  } catch (e) {
    console.error('Failed to load stats', e)
  }
})
</script>

<style scoped>
.home-page {
  max-width: 1200px;
  margin: 0 auto;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}
.stat-card {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  text-align: center;
}
.stat-value {
  font-size: 2.5rem;
  font-weight: bold;
  color: var(--primary);
  margin-bottom: 0.5rem;
}
.stat-label {
  color: var(--text-light);
  font-size: 0.9rem;
}
.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}
.action-card {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  text-align: center;
  text-decoration: none;
  color: inherit;
  transition: transform 0.2s, box-shadow 0.2s;
}
.action-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0,0,0,0.1);
}
.action-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}
.action-title {
  font-weight: 500;
  color: var(--primary);
}
</style>

