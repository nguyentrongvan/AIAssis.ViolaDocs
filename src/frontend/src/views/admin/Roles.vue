<template>
  <div class="admin-page">
    <div class="page-header">
      <h1>Roles</h1>
      <button @click="showCreateModal = true" class="btn-primary">
        <Plus :size="20" />
        New Role
      </button>
    </div>

    <div class="roles-list">
      <div v-for="role in roles" :key="role.id" class="role-card">
        <div class="role-header">
          <h3>{{ role.name }}</h3>
          <div class="role-actions">
            <button @click="editRole(role)" class="btn-small">
              <Edit :size="16" />
              Edit
            </button>
            <button @click="deleteRole(role)" class="btn-small btn-danger">
              <Trash2 :size="16" />
              Delete
            </button>
          </div>
        </div>
        <div class="role-permissions">
          <div class="permissions-label">Permissions:</div>
          <div class="permissions-list">
            <span
              v-for="perm in role.permissions"
              :key="perm"
              class="permission-badge"
            >
              {{ perm }}
            </span>
            <span v-if="role.permissions.length === 0" class="no-permissions">
              No permissions
            </span>
          </div>
        </div>
      </div>
      <div v-if="roles.length === 0" class="empty-state">
        No roles found. Create your first role.
      </div>
    </div>

    <!-- Create/Edit Role Modal -->
    <Modal
      v-model:show="showCreateModal"
      :title="editingRole ? 'Edit Role' : 'Create Role'"
    >
      <div class="form-group">
        <label>Name *</label>
        <input v-model="roleForm.name" required />
      </div>
      <div class="form-group">
        <label>Permissions</label>
        <div class="permissions-editor">
          <div
            v-for="perm in availablePermissions"
            :key="perm"
            class="permission-checkbox"
          >
            <label>
              <input
                type="checkbox"
                :value="perm"
                v-model="roleForm.permissions"
              />
              {{ perm }}
            </label>
          </div>
        </div>
      </div>
      <template #footer>
        <button
          type="button"
          @click="showCreateModal = false"
          class="btn-secondary"
        >
          Cancel
        </button>
        <button type="button" @click="saveRole" class="btn-primary">Save</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRolesStore } from '../../store/roles'
import { Modal } from '../../components'
import { Plus, Edit, Trash2 } from 'lucide-vue-next'

const rolesStore = useRolesStore()

const roles = ref([])
const showCreateModal = ref(false)
const editingRole = ref(null)

const availablePermissions = [
  'read',
  'write',
  'delete',
  'share',
  'admin',
  'manage_users',
  'manage_groups',
  'manage_devices',
  'view_audit',
  'manage_settings'
]

const roleForm = ref({
  name: '',
  permissions: []
})

onMounted(async () => {
  await loadRoles()
})

const loadRoles = async () => {
  try {
    await rolesStore.fetchRoles()
    roles.value = rolesStore.roles
  } catch (e) {
    console.error('Failed to load roles', e)
    if (window.$toast) {
      window.$toast.show('Failed to load roles', 'error')
    }
  }
}

const editRole = (role) => {
  editingRole.value = role
  roleForm.value = {
    name: role.name,
    permissions: [...(role.permissions || [])]
  }
  showCreateModal.value = true
}

const saveRole = async () => {
  try {
    const isEditing = !!editingRole.value
    if (isEditing) {
      await rolesStore.updateRole(editingRole.value.id, roleForm.value)
    } else {
      await rolesStore.createRole(roleForm.value)
    }
    await loadRoles()
    showCreateModal.value = false
    editingRole.value = null
    roleForm.value = { name: '', permissions: [] }
    if (window.$toast) {
      window.$toast.show(
        isEditing ? 'Role updated' : 'Role created',
        'success'
      )
    }
  } catch (e) {
    console.error('Failed to save role', e)
    if (window.$toast) {
      window.$toast.show('Failed to save role', 'error')
    }
  }
}

const deleteRole = async (role) => {
  if (confirm(`Delete role "${role.name}"?`)) {
    try {
      await rolesStore.deleteRole(role.id)
      await loadRoles()
      if (window.$toast) {
        window.$toast.show('Role deleted', 'success')
      }
    } catch (e) {
      console.error('Failed to delete role', e)
      if (window.$toast) {
        window.$toast.show('Failed to delete role', 'error')
      }
    }
  }
}
</script>

<style scoped>
.admin-page {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.roles-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.role-card {
  background: var(--bg-light);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #eee;
}

.role-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.role-header h3 {
  margin: 0;
  color: var(--primary);
}

.role-actions {
  display: flex;
  gap: 0.5rem;
}

.role-permissions {
  margin-top: 1rem;
}

.permissions-label {
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: #666;
}

.permissions-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.permission-badge {
  background: white;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  border: 1px solid #ddd;
}

.no-permissions {
  color: #999;
  font-style: italic;
}

.permissions-editor {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 1rem;
}

.permission-checkbox {
  margin-bottom: 0.75rem;
}

.permission-checkbox label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.permission-checkbox input[type="checkbox"] {
  width: auto;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #666;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}
</style>

