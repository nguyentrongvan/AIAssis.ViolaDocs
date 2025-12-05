<template>
  <Layout>
    <template #header>
      <h1>Scan Inbox</h1>
    </template>
    <div class="scan-page">
      <div v-if="scans.length === 0" class="empty-state">
        <p>No pending scans</p>
      </div>
      <div v-else class="scan-list">
        <div v-for="scan in scans" :key="scan.id" class="scan-item">
          <div class="scan-preview">
            <img v-if="scan.thumbnail" :src="scan.thumbnail" alt="Scan preview" />
          </div>
          <div class="scan-info">
            <h3>{{ scan.filename }}</h3>
            <p class="meta">From {{ scan.device?.name }} • {{ formatDate(scan.created_at) }}</p>
            <p v-if="scan.user" class="meta">User: {{ scan.user.name }}</p>
          </div>
          <div class="scan-actions">
            <button @click="claimScan(scan)" class="btn-primary">Claim</button>
            <button @click="assignScan(scan)" class="btn-secondary">Assign</button>
            <button @click="deleteScan(scan)" class="btn-danger">Delete</button>
          </div>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Layout from '../components/Layout.vue'
import api from '../services/api'

const scans = ref([])

onMounted(async () => {
  await loadScans()
})

const loadScans = async () => {
  try {
    const res = await api.get('/scan-jobs/pending')
    if (res.is_success) {
      scans.value = res.data || []
    }
  } catch (e) {
    console.error('Failed to load scans', e)
  }
}

const claimScan = async (scan) => {
  try {
    await api.post(`/scan-jobs/${scan.id}/claim`)
    await loadScans()
  } catch (e) {
    console.error('Failed to claim scan', e)
  }
}

const assignScan = (scan) => {
  // Open assign modal
  console.log('Assign scan', scan)
}

const deleteScan = async (scan) => {
  if (confirm('Delete this scan?')) {
    try {
      await api.delete(`/scan-jobs/${scan.id}`)
      await loadScans()
    } catch (e) {
      console.error('Failed to delete scan', e)
    }
  }
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleDateString()
}
</script>

<style scoped>
.scan-page {
  max-width: 1200px;
  margin: 0 auto;
}
.empty-state {
  text-align: center;
  padding: 3rem;
  color: #666;
}
.scan-list {
  display: grid;
  gap: 1.5rem;
}
.scan-item {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  display: grid;
  grid-template-columns: 150px 1fr auto;
  gap: 1.5rem;
  align-items: center;
}
.scan-preview img {
  width: 100%;
  height: 150px;
  object-fit: cover;
  border-radius: 6px;
}
.scan-info h3 {
  margin: 0 0 0.5rem 0;
}
.meta {
  color: #666;
  font-size: 0.9rem;
  margin: 0.25rem 0;
}
.scan-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
</style>

