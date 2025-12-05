<template>
  <Layout>
    <template #header>
      <h1>Device Management</h1>
      <button @click="showCreateModal = true" class="btn-primary">+ Add Device</button>
    </template>
    <div class="admin-page">
      <table class="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Location</th>
            <th>Status</th>
            <th>Last Seen</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="device in devices" :key="device.id">
            <td>{{ device.name }}</td>
            <td>{{ device.location }}</td>
            <td>
              <span :class="['status-badge', device.status]">{{ device.status }}</span>
            </td>
            <td>{{ device.last_seen ? formatDate(device.last_seen) : 'Never' }}</td>
            <td>
              <button @click="editDevice(device)" class="btn-small">Edit</button>
              <button @click="issueKey(device)" class="btn-small">Issue Key</button>
              <button @click="deleteDevice(device)" class="btn-small btn-danger">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </Layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Layout from '../../components/Layout.vue'
import api from '../../services/api'

const devices = ref([])
const showCreateModal = ref(false)

onMounted(async () => {
  await loadDevices()
})

const loadDevices = async () => {
  try {
    const res = await api.get('/devices')
    if (res.is_success) {
      devices.value = res.data || []
    }
  } catch (e) {
    console.error('Failed to load devices', e)
  }
}

const editDevice = (device) => {
  console.log('Edit device', device)
}

const issueKey = async (device) => {
  try {
    const res = await api.post(`/devices/${device.id}/issue-key`)
    if (res.is_success) {
      alert('Device key issued: ' + res.data.key)
    }
  } catch (e) {
    console.error('Failed to issue key', e)
  }
}

const deleteDevice = async (device) => {
  if (confirm('Delete this device?')) {
    try {
      await api.delete(`/devices/${device.id}`)
      await loadDevices()
    } catch (e) {
      console.error('Failed to delete device', e)
    }
  }
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleDateString()
}
</script>

<style scoped>
.admin-page {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.data-table {
  width: 100%;
  border-collapse: collapse;
}
.data-table th,
.data-table td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}
.data-table th {
  font-weight: 600;
  color: var(--primary);
}
.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
}
.status-badge.online {
  background: var(--success-light);
  color: var(--success);
}
.status-badge.offline {
  background: #f0f0f0;
  color: #666;
}
.btn-small {
  padding: 0.25rem 0.75rem;
  font-size: 0.85rem;
  margin-right: 0.5rem;
}
</style>

