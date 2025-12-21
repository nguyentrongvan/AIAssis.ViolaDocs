<template>
  <div class="admin-page">
    <div class="page-header">
      <h1>{{ $t('admin.roles.title') }}</h1>
      <button @click="showCreateModal = true" class="btn-primary">
        <Plus :size="20" />
        {{ $t('admin.roles.createRole') }}
      </button>
    </div>

    <div class="roles-list">
      <div v-for="role in roles" :key="role.id" class="role-card">
        <div class="role-header">
          <h3>{{ role.name }}</h3>
          <div class="role-actions">
            <button @click="editRole(role)" class="btn-small">
              <Edit :size="16" />
              {{ $t('common.edit') }}
            </button>
            <button @click="deleteRole(role)" class="btn-small btn-danger">
              <Trash2 :size="16" />
              {{ $t('common.delete') }}
            </button>
          </div>
        </div>
        <div class="role-permissions">
          <div class="permissions-label">{{ $t('admin.roles.permissions') }}:</div>
          <div class="permissions-list">
            <span
              v-for="perm in role.permissions"
              :key="perm"
              class="permission-badge"
            >
              {{ getPermissionName(perm) }}
            </span>
            <span v-if="role.permissions.length === 0" class="no-permissions">
              {{ $t('admin.roles.noPermissions') }}
            </span>
          </div>
        </div>
      </div>
      <div v-if="roles.length === 0" class="empty-state">
        {{ $t('admin.roles.noRoles') }}
      </div>
    </div>

    <!-- Create/Edit Role Modal -->
    <Modal
      v-model:show="showCreateModal"
      :title="editingRole ? $t('admin.roles.editRole') : $t('admin.roles.createRole')"
    >
      <div class="form-group">
        <label>{{ $t('admin.roles.name') }} *</label>
        <input v-model="roleForm.name" required />
      </div>
      <div class="form-group">
        <label>{{ $t('admin.roles.permissions') }}</label>
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
              {{ getPermissionName(perm) }}
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
          {{ $t('common.cancel') }}
        </button>
        <button type="button" @click="saveRole" class="btn-primary">{{ $t('common.save') }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRolesStore } from '../../store/roles'
import { Modal } from '../../components'
import { Plus, Edit, Trash2 } from 'lucide-vue-next'

const { t } = useI18n()

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
      window.$toast.show(t('admin.roles.failedToLoadRoles'), 'error')
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
        isEditing ? t('admin.roles.roleUpdated') : t('admin.roles.roleCreated'),
        'success'
      )
    }
  } catch (e) {
    console.error('Failed to save role', e)
    if (window.$toast) {
      window.$toast.show(t('admin.roles.failedToSaveRole'), 'error')
    }
  }
}

const getPermissionName = (perm) => {
  const key = `admin.roles.permissionNames.${perm}`
  const translated = t(key)
  // If translation key doesn't exist, return the original permission name
  return translated !== key ? translated : perm
}

const deleteRole = async (role) => {
  if (confirm(t('admin.roles.deleteRoleConfirm', { name: role.name }))) {
    try {
      await rolesStore.deleteRole(role.id)
      await loadRoles()
      if (window.$toast) {
        window.$toast.show(t('admin.roles.roleDeleted'), 'success')
      }
    } catch (e) {
      console.error('Failed to delete role', e)
      if (window.$toast) {
        window.$toast.show(t('admin.roles.failedToDeleteRole'), 'error')
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

.page-header h1 {
  font-size: 2rem;
  font-weight: 700;
  margin: 0;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.02em;
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
  align-items: center;
}

.btn-small {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--bg-white);
  border: 2px solid rgba(0, 0, 0, 0.08);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-dark);
  cursor: pointer;
  transition: all var(--transition-base);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.btn-small:hover {
  background: var(--gradient-ai-soft);
  border-color: var(--ai-cyan);
  color: var(--primary);
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0, 217, 255, 0.15);
}

.btn-small:active {
  transform: translateY(0);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.btn-small.btn-danger {
  background: var(--bg-white);
  border-color: rgba(231, 76, 60, 0.3);
  color: var(--error);
}

.btn-small.btn-danger:hover {
  background: var(--error-light);
  border-color: var(--error);
  color: var(--error);
  box-shadow: 0 2px 6px rgba(231, 76, 60, 0.2);
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

