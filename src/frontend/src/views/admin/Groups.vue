<template>
  <div class="admin-page">
    <div class="page-header">
      <h1>Document Groups</h1>
      <button @click="showCreateModal = true" class="btn-primary">+ Create Group</button>
    </div>
      <div class="groups-grid">
        <div v-for="group in groups" :key="group.id" class="group-card">
          <h3>{{ group.name }}</h3>
          <p>{{ group.description }}</p>
          <div class="group-meta">
            <span>Documents: {{ group.document_count || 0 }}</span>
            <span>Members: {{ group.member_count || 0 }}</span>
          </div>
          <div class="group-actions">
            <button @click="editGroup(group)" class="btn-small">Edit</button>
            <button @click="deleteGroup(group)" class="btn-small btn-danger">Delete</button>
          </div>
        </div>
      </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../../services/api'

const groups = ref([])
const showCreateModal = ref(false)

onMounted(async () => {
  await loadGroups()
})

const loadGroups = async () => {
  try {
    const res = await api.get('/groups')
    if (res.is_success) {
      groups.value = res.data || []
    }
  } catch (e) {
    console.error('Failed to load groups', e)
  }
}

const editGroup = (group) => {
  console.log('Edit group', group)
}

const deleteGroup = async (group) => {
  if (confirm('Delete this group?')) {
    try {
      await api.delete(`/groups/${group.id}`)
      await loadGroups()
    } catch (e) {
      console.error('Failed to delete group', e)
    }
  }
}
</script>

<style scoped>
.admin-page {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.groups-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}
.group-card {
  background: var(--bg-light);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #eee;
}
.group-card h3 {
  margin: 0 0 0.5rem 0;
  color: var(--primary);
}
.group-meta {
  display: flex;
  gap: 1rem;
  margin: 1rem 0;
  font-size: 0.9rem;
  color: #666;
}
.group-actions {
  display: flex;
  gap: 0.5rem;
}
</style>

