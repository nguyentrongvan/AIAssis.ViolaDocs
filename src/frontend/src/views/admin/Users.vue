<template>
  <div class="admin-page">
    <div class="page-header">
      <h1>User Management</h1>
      <button @click="showCreateModal = true" class="btn-primary">+ Add User</button>
    </div>
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
            <td>
              <div class="role-display">
                <span class="basic-role">{{ user.role }}</span>
                <span
                  v-for="role in user.roles || []"
                  :key="role.id"
                  class="role-badge"
                >
                  {{ role.name }}
                </span>
              </div>
            </td>
            <td>
              <span :class="['status-badge', user.status]">{{ user.status }}</span>
            </td>
            <td>{{ user.expires_at ? formatDate(user.expires_at) : 'Never' }}</td>
            <td>
              <div class="action-buttons">
                <button @click="editUser(user)" class="btn-action btn-edit">
                  Edit
                </button>
                <button 
                  @click="toggleUserStatus(user)" 
                  :class="['btn-action', user.status === 'active' ? 'btn-deactivate' : 'btn-activate']"
                >
                  {{ user.status === 'active' ? 'Deactivate' : 'Activate' }}
                </button>
              </div>
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
            <label>Menu Roles</label>
            <div class="acl-selector">
              <div class="selected-items">
                <span
                  v-for="roleId in newUser.role_ids || []"
                  :key="roleId"
                  class="selected-item"
                >
                  {{ getRoleName(roleId) }}
                  <button @click.stop="removeRoleFromNewUser(roleId)" class="item-remove">×</button>
                </span>
              </div>
              <button
                @click="openRolePickerForNewUser"
                class="btn-add-acl"
                type="button"
              >
                + Add Menu Roles
              </button>
            </div>
            <p class="hint-text">Select menu roles to control menu access. Editor and Manager require staff/admin role.</p>
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
    <!-- Edit User Modal -->
    <div v-if="showEditModal && editingUser" class="modal" @click.self="showEditModal = false">
      <div class="modal-content">
        <h2>Edit User</h2>
        <form @submit.prevent="updateUser">
          <div class="form-group">
            <label>Name</label>
            <input v-model="editingUser.name" required />
          </div>
          <div class="form-group">
            <label>Email</label>
            <input v-model="editingUser.email" type="email" required />
          </div>
          <div class="form-group">
            <label>Role</label>
            <select v-model="editingUser.role" required>
              <option value="user">User</option>
              <option value="staff">Staff</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div class="form-group">
            <label>Menu Roles</label>
            <div class="acl-selector">
              <div class="selected-items">
                <span
                  v-for="roleId in editingUser.role_ids || []"
                  :key="roleId"
                  class="selected-item"
                >
                  {{ getRoleName(roleId) }}
                  <button @click.stop="removeRoleFromEditingUser(roleId)" class="item-remove">×</button>
                </span>
              </div>
              <button
                @click="openRolePickerForEditingUser"
                class="btn-add-acl"
                type="button"
              >
                + Add Menu Roles
              </button>
            </div>
            <p class="hint-text">Select menu roles to control menu access. Editor and Manager require staff/admin role.</p>
          </div>
          <div class="form-group">
            <label>Status</label>
            <select v-model="editingUser.status" required>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
          <div class="form-group">
            <label>Expires At (optional)</label>
            <input v-model="editingUser.expires_at" type="date" />
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary">Update</button>
            <button type="button" @click="showEditModal = false" class="btn-secondary">Cancel</button>
          </div>
        </form>
      </div>
    </div>
    <!-- Role Picker Modal for New User -->
    <div v-if="showRolePickerForNew" class="modal" @click.self="showRolePickerForNew = false">
      <div class="modal-content role-picker-modal">
        <h3>Select Menu Roles</h3>
        <div class="picker-search">
          <input
            v-model="roleSearchQuery"
            type="text"
            placeholder="Search roles by name..."
            class="search-input"
          />
        </div>
        <div class="picker-list">
          <div
            v-for="role in filteredRoles"
            :key="role.id"
            class="picker-item"
            :class="{ disabled: isRoleDisabled(role.name, newUser.role) }"
          >
            <label class="picker-checkbox">
              <input
                type="checkbox"
                :checked="isRoleSelected(role.id, newUser)"
                :disabled="isRoleDisabled(role.name, newUser.role)"
                @change="toggleRole(role.id, newUser)"
              />
              <span class="picker-label">
                <strong>{{ role.name }}</strong>
                <span v-if="isRoleDisabled(role.name, newUser.role)" class="picker-hint">(staff/admin only)</span>
                <span class="role-description">{{ getRoleDescription(role.name) }}</span>
              </span>
            </label>
          </div>
          <div v-if="filteredRoles.length === 0" class="picker-empty">
            {{ roleSearchQuery ? 'No roles found' : 'No roles available' }}
          </div>
        </div>
        <div class="form-actions">
          <button @click="showRolePickerForNew = false" class="btn-secondary">Cancel</button>
          <button @click="confirmRolesForNewUser" class="btn-primary">Confirm ({{ tempSelectedRoles?.length || 0 }})</button>
        </div>
      </div>
    </div>
    <!-- Role Picker Modal for Editing User -->
    <div v-if="showRolePickerForEdit && editingUser" class="modal" @click.self="showRolePickerForEdit = false">
      <div class="modal-content role-picker-modal">
        <h3>Select Menu Roles</h3>
        <div class="picker-search">
          <input
            v-model="roleSearchQuery"
            type="text"
            placeholder="Search roles by name..."
            class="search-input"
          />
        </div>
        <div class="picker-list">
          <div
            v-for="role in filteredRoles"
            :key="role.id"
            class="picker-item"
            :class="{ disabled: isRoleDisabled(role.name, editingUser.role) }"
          >
            <label class="picker-checkbox">
              <input
                type="checkbox"
                :checked="isRoleSelected(role.id, editingUser)"
                :disabled="isRoleDisabled(role.name, editingUser.role)"
                @change="toggleRole(role.id, editingUser)"
              />
              <span class="picker-label">
                <strong>{{ role.name }}</strong>
                <span v-if="isRoleDisabled(role.name, editingUser.role)" class="picker-hint">(staff/admin only)</span>
                <span class="role-description">{{ getRoleDescription(role.name) }}</span>
              </span>
            </label>
          </div>
          <div v-if="filteredRoles.length === 0" class="picker-empty">
            {{ roleSearchQuery ? 'No roles found' : 'No roles available' }}
          </div>
        </div>
        <div class="form-actions">
          <button @click="showRolePickerForEdit = false" class="btn-secondary">Cancel</button>
          <button @click="confirmRolesForEditingUser" class="btn-primary">Confirm ({{ tempSelectedRoles?.length || 0 }})</button>
        </div>
      </div>
    </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../../services/api'
import { useRolesStore } from '../../store/roles'

const users = ref([])
const showCreateModal = ref(false)
const showEditModal = ref(false)
const editingUser = ref(null)
const rolesStore = useRolesStore()
const roles = computed(() => rolesStore.roles || [])
const showRolePickerForNew = ref(false)
const showRolePickerForEdit = ref(false)
const roleSearchQuery = ref('')
const tempSelectedRoles = ref([])

const newUser = ref({
  name: '',
  email: '',
  password: '',
  role: 'user',
  expires_at: '',
  role_ids: []
})

onMounted(async () => {
  await loadUsers()
  await loadRoles()
})

const loadRoles = async () => {
  try {
    await rolesStore.fetchRoles()
  } catch (e) {
    console.error('Failed to load roles', e)
  }
}

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
      newUser.value = { name: '', email: '', password: '', role: 'user', expires_at: '', role_ids: [] }
      if (window.$toast) {
        window.$toast.show('User created successfully', 'success')
      }
    }
  } catch (e) {
    console.error('Failed to create user', e)
    if (window.$toast) {
      window.$toast.show(e.response?.data?.message || 'Failed to create user', 'error')
    } else if (e.response?.data?.message) {
      alert(e.response.data.message)
    }
  }
}

const editUser = async (user) => {
  try {
    const res = await api.get(`/users/${user.id}`)
    if (res.is_success) {
      editingUser.value = {
        ...res.data,
        role_ids: res.data.roles ? res.data.roles.map(r => r.id) : [],
        expires_at: res.data.expires_at ? res.data.expires_at.split('T')[0] : ''
      }
      showEditModal.value = true
    }
  } catch (e) {
    console.error('Failed to load user', e)
  }
}

const updateUser = async () => {
  try {
    const res = await api.patch(`/users/${editingUser.value.id}`, editingUser.value)
    if (res.is_success) {
      await loadUsers()
      showEditModal.value = false
      editingUser.value = null
      if (window.$toast) {
        window.$toast.show('User updated successfully', 'success')
      }
    }
  } catch (e) {
    console.error('Failed to update user', e)
    if (window.$toast) {
      window.$toast.show(e.response?.data?.message || 'Failed to update user', 'error')
    } else if (e.response?.data?.message) {
      alert(e.response.data.message)
    }
  }
}

const filteredRoles = computed(() => {
  const rolesList = roles.value || []
  if (!Array.isArray(rolesList) || rolesList.length === 0) {
    return []
  }
  if (!roleSearchQuery.value) {
    return rolesList.filter(role => role && role.id && role.name)
  }
  const query = roleSearchQuery.value.toLowerCase()
  return rolesList.filter(role => 
    role && role.id && role.name && role.name.toLowerCase().includes(query)
  )
})

const toggleRole = (roleId, userRef) => {
  // When in picker modal, use tempSelectedRoles
  if (showRolePickerForNew.value || showRolePickerForEdit.value) {
    if (!tempSelectedRoles.value) {
      tempSelectedRoles.value = []
    }
    const index = tempSelectedRoles.value.indexOf(roleId)
    if (index > -1) {
      tempSelectedRoles.value.splice(index, 1)
    } else {
      tempSelectedRoles.value.push(roleId)
    }
  } else {
    // Direct toggle (not in modal)
    if (!userRef.role_ids) {
      userRef.role_ids = []
    }
    const index = userRef.role_ids.indexOf(roleId)
    if (index > -1) {
      userRef.role_ids.splice(index, 1)
    } else {
      userRef.role_ids.push(roleId)
    }
  }
}

const isRoleSelected = (roleId, userRef) => {
  // Use tempSelectedRoles when in picker modal, otherwise use userRef.role_ids
  if (showRolePickerForNew.value || showRolePickerForEdit.value) {
    return tempSelectedRoles.value.includes(roleId)
  }
  return userRef.role_ids && userRef.role_ids.includes(roleId)
}

const isRoleDisabled = (roleName, userRole) => {
  // editor và manager chỉ dành cho staff/admin
  if (roleName === 'editor' || roleName === 'manager') {
    return userRole !== 'staff' && userRole !== 'admin'
  }
  return false
}

const getRoleName = (roleId) => {
  const rolesList = roles.value || []
  if (!Array.isArray(rolesList)) {
    return `Role ${roleId}`
  }
  const role = rolesList.find(r => r && r.id === roleId)
  return role ? role.name : `Role ${roleId}`
}

const getRoleDescription = (roleName) => {
  const descriptions = {
    'viewer': 'No menu access. Only document-level view permission when shared.',
    'searcher': 'Access to Search menu - can search documents',
    'chatter': 'Access to Chatbot menu - can chat with AI about documents',
    'uploader': 'Access to Upload menu - can upload new documents',
    'scanner': 'Access to Scan Inbox menu - can manage scanned documents',
    'deleter': 'Access to Recycle Bin menu - can view and manage deleted documents',
    'editor': 'Access to Upload, Search, Scan Inbox, Chatbot, and Folders menus',
    'manager': 'Access to Upload, Search, Scan Inbox, Chatbot, Folders, Settings, Reports, and Users menus'
  }
  return descriptions[roleName] || ''
}

const openRolePickerForNewUser = () => {
  tempSelectedRoles.value = [...(newUser.value.role_ids || [])]
  roleSearchQuery.value = ''
  showRolePickerForNew.value = true
}

const openRolePickerForEditingUser = () => {
  tempSelectedRoles.value = [...(editingUser.value.role_ids || [])]
  roleSearchQuery.value = ''
  showRolePickerForEdit.value = true
}

const confirmRolesForNewUser = () => {
  newUser.value.role_ids = [...tempSelectedRoles.value]
  showRolePickerForNew.value = false
  tempSelectedRoles.value = []
  roleSearchQuery.value = ''
}

const confirmRolesForEditingUser = () => {
  editingUser.value.role_ids = [...tempSelectedRoles.value]
  showRolePickerForEdit.value = false
  tempSelectedRoles.value = []
  roleSearchQuery.value = ''
}

const removeRoleFromNewUser = (roleId) => {
  if (!newUser.value.role_ids) return
  const index = newUser.value.role_ids.indexOf(roleId)
  if (index > -1) {
    newUser.value.role_ids.splice(index, 1)
  }
}

const removeRoleFromEditingUser = (roleId) => {
  if (!editingUser.value || !editingUser.value.role_ids) return
  const index = editingUser.value.role_ids.indexOf(roleId)
  if (index > -1) {
    editingUser.value.role_ids.splice(index, 1)
  }
}

const toggleUserStatus = async (user) => {
  try {
    const res = await api.patch(`/users/${user.id}`, {
      status: user.status === 'active' ? 'inactive' : 'active'
    })
    if (res.is_success) {
      await loadUsers()
      if (window.$toast) {
        const newStatus = user.status === 'active' ? 'deactivated' : 'activated'
        window.$toast.show(`User ${newStatus} successfully`, 'success')
      }
    }
  } catch (e) {
    console.error('Failed to toggle status', e)
    if (window.$toast) {
      window.$toast.show('Failed to update user status', 'error')
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
  padding: var(--space-md) var(--space-lg);
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-lg);
  background: var(--bg-white);
  font-size: 0.95rem;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.form-group input[type="date"],
.form-group input[type="datetime-local"] {
  padding-right: var(--space-xl);
  cursor: pointer;
  position: relative;
}

.form-group input[type="date"]::-webkit-calendar-picker-indicator,
.form-group input[type="datetime-local"]::-webkit-calendar-picker-indicator {
  cursor: pointer;
  opacity: 0.6;
  filter: grayscale(1);
  transition: all var(--transition-base);
  padding: var(--space-xs);
  border-radius: var(--radius-sm);
}

.form-group input[type="date"]::-webkit-calendar-picker-indicator:hover,
.form-group input[type="datetime-local"]::-webkit-calendar-picker-indicator:hover {
  opacity: 1;
  filter: grayscale(0);
  background: var(--gradient-ai-soft);
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--ai-cyan);
  box-shadow: var(--shadow-md), 0 0 0 3px rgba(0, 217, 255, 0.1);
}

.form-group input[type="date"]:focus::-webkit-calendar-picker-indicator,
.form-group input[type="datetime-local"]:focus::-webkit-calendar-picker-indicator {
  opacity: 1;
  filter: grayscale(0);
}
.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.acl-selector {
  margin-top: 0.5rem;
}

.selected-items {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.selected-item {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--primary-light);
  color: var(--primary);
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
}

.item-remove {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--primary);
  font-size: 1.2rem;
  line-height: 1;
  padding: 0;
  display: flex;
  align-items: center;
}

.item-remove:hover {
  color: #ef4444;
}

.btn-add-acl {
  padding: 0.5rem 1rem;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background var(--transition-base);
}

.btn-add-acl:hover {
  background: var(--primary-dark);
}

.hint-text {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-top: 0.5rem;
  font-style: italic;
}

.role-picker-modal {
  max-width: 500px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.role-picker-modal h3 {
  margin-bottom: 1rem;
}

.picker-search {
  margin-bottom: 1rem;
}

.search-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 0.9rem;
  transition: border-color var(--transition-base);
}

.search-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}

.picker-list {
  flex: 1;
  overflow-y: auto;
  max-height: 400px;
  margin-bottom: 1rem;
}

.picker-item {
  padding: 0.75rem;
  border-bottom: 1px solid #eee;
  transition: background var(--transition-base);
}

.picker-item:hover:not(.disabled) {
  background: var(--bg-light);
}

.picker-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.picker-checkbox {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  width: 100%;
}

.picker-item.disabled .picker-checkbox {
  cursor: not-allowed;
}

.picker-checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--primary);
}

.picker-item.disabled .picker-checkbox input[type="checkbox"] {
  cursor: not-allowed;
}

.picker-label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
}

.picker-label strong {
  font-weight: 600;
  color: var(--text-primary);
}

.picker-hint {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-style: italic;
}

.role-description {
  font-size: 0.8rem;
  color: #666;
  margin-top: 0.25rem;
  line-height: 1.4;
  font-style: normal;
  display: block;
}

.picker-empty {
  padding: 2rem;
  text-align: center;
  color: var(--text-secondary);
}

.role-display {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.basic-role {
  font-weight: 600;
  color: var(--primary);
}

.role-badge {
  padding: 0.25rem 0.75rem;
  background: var(--primary-light);
  color: var(--primary);
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 500;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.btn-action {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-base);
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-edit {
  background: var(--primary);
  color: white;
  box-shadow: 0 2px 4px rgba(139, 92, 246, 0.2);
}

.btn-edit:hover {
  background: var(--primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(139, 92, 246, 0.3);
}

.btn-edit:active {
  transform: translateY(0);
}

.btn-deactivate {
  background: #fee2e2;
  color: #dc2626;
  box-shadow: 0 2px 4px rgba(220, 38, 38, 0.2);
}

.btn-deactivate:hover {
  background: #fecaca;
  color: #b91c1c;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(220, 38, 38, 0.3);
}

.btn-deactivate:active {
  transform: translateY(0);
}

.btn-activate {
  background: #dcfce7;
  color: #16a34a;
  box-shadow: 0 2px 4px rgba(22, 163, 74, 0.2);
}

.btn-activate:hover {
  background: #bbf7d0;
  color: #15803d;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(22, 163, 74, 0.3);
}

.btn-activate:active {
  transform: translateY(0);
}
</style>

