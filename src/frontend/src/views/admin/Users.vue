<template>
  <Layout>
    <template #header>
      <h1>User Management</h1>
      <button @click="showCreateModal = true" class="btn-primary">+ Add User</button>
    </template>
    <div class="admin-page">
      <table class="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Expires</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>{{ user.name }}</td>
            <td>{{ user.email }}</td>
            <td>{{ user.role }}</td>
            <td>
              <span :class="['status-badge', user.status]">{{ user.status }}</span>
            </td>
            <td>{{ user.expires_at ? formatDate(user.expires_at) : 'Never' }}</td>
            <td>
              <button @click="editUser(user)" class="btn-small">Edit</button>
              <button @click="toggleUserStatus(user)" class="btn-small">
                {{ user.status === 'active' ? 'Deactivate' : 'Activate' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="showCreateModal" class="modal" @click.self="showCreateModal = false">
      <div class="modal-content">
        <h2>Create User</h2>
        <form @submit.prevent="createUser">
          <div class="form-group">
            <label>Name</label>
            <input v-model="newUser.name" required />
          </div>
          <div class="form-group">
            <label>Email</label>
            <input v-model="newUser.email" type="email" required />
          </div>
          <div class="form-group">
            <label>Password</label>
            <input v-model="newUser.password" type="password" required />
          </div>
          <div class="form-group">
            <label>Role</label>
            <select v-model="newUser.role" required>
              <option value="user">User</option>
              <option value="staff">Staff</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div class="form-group">
            <label>Expires At (optional)</label>
            <input v-model="newUser.expires_at" type="date" />
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary">Create</button>
            <button type="button" @click="showCreateModal = false" class="btn-secondary">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Layout from '../../components/Layout.vue'
import api from '../../services/api'

const users = ref([])
const showCreateModal = ref(false)
const newUser = ref({
  name: '',
  email: '',
  password: '',
  role: 'user',
  expires_at: ''
})

onMounted(async () => {
  await loadUsers()
})

const loadUsers = async () => {
  try {
    const res = await api.get('/users')
    if (res.is_success) {
      users.value = res.data || []
    }
  } catch (e) {
    console.error('Failed to load users', e)
  }
}

const createUser = async () => {
  try {
    const res = await api.post('/users', newUser.value)
    if (res.is_success) {
      await loadUsers()
      showCreateModal.value = false
      newUser.value = { name: '', email: '', password: '', role: 'user', expires_at: '' }
    }
  } catch (e) {
    console.error('Failed to create user', e)
  }
}

const editUser = (user) => {
  // Open edit modal
  console.log('Edit user', user)
}

const toggleUserStatus = async (user) => {
  try {
    const res = await api.patch(`/users/${user.id}`, {
      status: user.status === 'active' ? 'inactive' : 'active'
    })
    if (res.is_success) {
      await loadUsers()
    }
  } catch (e) {
    console.error('Failed to toggle status', e)
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
.status-badge.active {
  background: var(--success-light);
  color: var(--success);
}
.status-badge.inactive {
  background: #f0f0f0;
  color: #666;
}
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
}
.form-group {
  margin-bottom: 1rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}
.form-group input,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}
.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}
</style>

