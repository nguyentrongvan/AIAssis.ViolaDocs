<template>
  <div class="admin-page">
    <div class="page-header">
      <h1>{{ $t('admin.groups.title') }}</h1>
      <button @click="showCreateModal = true" class="btn-primary">
        <Plus :size="20" />
        {{ $t('admin.groups.createGroup') }}
      </button>
    </div>

    <div class="groups-grid">
      <div
        v-for="group in groups"
        :key="group.id"
        class="group-card"
        @click="viewGroup(group)"
      >
        <h3>{{ group.name }}</h3>
        <p v-if="group.description" class="group-description">
          {{ group.description }}
        </p>
        <div class="group-meta">
          <span>{{ $t('nav.documents') }}: {{ group.document_count || 0 }}</span>
          <span>{{ $t('admin.groups.members') }}: {{ group.member_count || 0 }}</span>
          <span>{{ $t('admin.groups.owners') }}: {{ group.owners?.length || 0 }}</span>
        </div>
        <div class="group-actions">
          <button @click.stop="editGroup(group)" class="btn-small">
            <Edit :size="16" />
            {{ $t('common.edit') }}
          </button>
          <button @click.stop="deleteGroup(group)" class="btn-small btn-danger">
            <Trash2 :size="16" />
            {{ $t('common.delete') }}
          </button>
        </div>
      </div>
      <div v-if="groups.length === 0" class="empty-state">
        {{ $t('admin.groups.noGroups') }}
      </div>
    </div>

    <!-- Create/Edit Group Modal -->
    <Modal
      v-model:show="showCreateModal"
      :title="editingGroup ? $t('admin.groups.editGroup') : $t('admin.groups.createGroup')"
    >
      <div class="form-group">
        <label>{{ $t('admin.groups.name') }} *</label>
        <input v-model="groupForm.name" required />
      </div>
      <div class="form-group">
        <label>{{ $t('common.description') }}</label>
        <textarea v-model="groupForm.description" rows="3"></textarea>
      </div>
      <div class="form-group">
        <label>{{ $t('admin.groups.owners') }}</label>
        <div class="multi-select">
          <div class="selected-items">
            <span
              v-for="userId in groupForm.owners || []"
              :key="userId"
              class="selected-item"
            >
              {{ getUserName(userId) }}
              <button type="button" @click="removeOwner(userId)" class="item-remove">×</button>
            </span>
          </div>
          <select @change="addOwner($event.target.value)">
            <option value="">{{ $t('admin.groups.addOwner') }}</option>
            <option
              v-for="user in users"
              :key="user.id"
              :value="user.id"
              :disabled="(groupForm.owners || []).includes(user.id)"
            >
              {{ user.name }} ({{ user.email }})
            </option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label>{{ $t('admin.groups.allowedRoles') }}</label>
        <div class="multi-select">
          <div class="selected-items">
            <span
              v-for="roleName in groupForm.allowed_roles || []"
              :key="roleName"
              class="selected-item"
            >
              {{ roleName }}
              <button type="button" @click="removeAllowedRole(roleName)" class="item-remove">×</button>
            </span>
          </div>
          <select @change="addAllowedRole($event.target.value)">
            <option value="">{{ $t('admin.groups.addRole') }}</option>
            <option
              v-for="role in roles"
              :key="role.name"
              :value="role.name"
              :disabled="(groupForm.allowed_roles || []).includes(role.name)"
            >
              {{ role.name }}
            </option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label>{{ $t('admin.groups.allowedUsers') }}</label>
        <div class="multi-select">
          <div class="selected-items">
            <span
              v-for="userId in groupForm.allowed_users || []"
              :key="userId"
              class="selected-item"
            >
              {{ getUserName(userId) }}
              <button type="button" @click="removeAllowedUser(userId)" class="item-remove">×</button>
            </span>
          </div>
          <select @change="addAllowedUser($event.target.value)">
            <option value="">{{ $t('admin.groups.addUser') }}</option>
            <option
              v-for="user in users"
              :key="user.id"
              :value="user.id"
              :disabled="(groupForm.allowed_users || []).includes(user.id)"
            >
              {{ user.name }} ({{ user.email }})
            </option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label>{{ $t('admin.groups.chatbotPolicyJson') }}</label>
        <textarea
          v-model="chatbotPolicyJson"
          rows="4"
          :placeholder="$t('admin.groups.chatbotPolicyPlaceholder')"
        ></textarea>
      </div>
      <template #footer>
        <button
          type="button"
          @click="showCreateModal = false"
          class="btn-secondary"
        >
          {{ $t('common.cancel') }}
        </button>
        <button type="button" @click="saveGroup" class="btn-primary">{{ $t('common.save') }}</button>
      </template>
    </Modal>

    <!-- Group Detail Modal -->
    <Modal v-model:show="showDetailModal" :title="currentGroup?.name || $t('admin.groups.groupDetails')">
      <div v-if="currentGroup" class="group-detail">
        <div class="detail-section">
          <h4>{{ $t('common.description') }}</h4>
          <p>{{ currentGroup.description || $t('admin.groups.noDescription') }}</p>
        </div>
        <div class="detail-section">
          <h4>{{ $t('admin.groups.owners') }}</h4>
          <div class="member-list">
            <span
              v-for="ownerId in currentGroup.owners || []"
              :key="ownerId"
              class="member-badge"
            >
              {{ getUserName(ownerId) }}
            </span>
          </div>
        </div>
        <div class="detail-section">
          <h4>{{ $t('admin.groups.allowedRoles') }}</h4>
          <div class="member-list">
            <span
              v-for="roleName in currentGroup.allowed_roles || []"
              :key="roleName"
              class="member-badge"
            >
              {{ roleName }}
            </span>
          </div>
        </div>
        <div class="detail-section">
          <h4>{{ $t('admin.groups.allowedUsers') }}</h4>
          <div class="member-list">
            <span
              v-for="userId in currentGroup.allowed_users || []"
              :key="userId"
              class="member-badge"
            >
              {{ getUserName(userId) }}
            </span>
          </div>
        </div>
        <div class="detail-section">
          <h4>{{ $t('admin.groups.associatedDocuments') }}</h4>
          <div class="associations">
            <button @click="associateDocuments" class="btn-small">
              <FileText :size="16" />
              {{ $t('admin.groups.manageDocuments') }}
            </button>
            <span class="count">{{ currentGroup.document_count || 0 }} {{ $t('admin.groups.documents') }}</span>
          </div>
        </div>
        <div class="detail-section">
          <h4>{{ $t('admin.groups.associatedFolders') }}</h4>
          <div class="associations">
            <button @click="associateFolders" class="btn-small">
              <Folder :size="16" />
              {{ $t('admin.groups.manageFolders') }}
            </button>
            <span class="count">{{ currentGroup.folder_count || 0 }} {{ $t('admin.groups.folders') }}</span>
          </div>
        </div>
        <div class="detail-section">
          <h4>{{ $t('admin.groups.associatedTags') }}</h4>
          <div class="associations">
            <button @click="associateTags" class="btn-small">
              <Tag :size="16" />
              {{ $t('admin.groups.manageTags') }}
            </button>
            <span class="count">{{ currentGroup.tag_count || 0 }} {{ $t('admin.groups.tags') }}</span>
          </div>
        </div>
        <div class="detail-section">
          <h4>{{ $t('admin.groups.actions') }}</h4>
          <button @click="reindexGroup" class="btn-primary">
            <RefreshCw :size="16" />
            {{ $t('admin.groups.reindexGroup') }}
          </button>
        </div>
      </div>
      <template #footer>
        <button @click="showDetailModal = false" class="btn-secondary">{{ $t('common.close') }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGroupsStore } from '../../store/groups'
import { useRolesStore } from '../../store/roles'
import { groupsAPI, usersAPI } from '../../services/api'
import { Modal } from '../../components'
import { Plus, Edit, Trash2, FileText, Folder, Tag, RefreshCw } from 'lucide-vue-next'

const { t } = useI18n()

const groupsStore = useGroupsStore()
const rolesStore = useRolesStore()

const groups = ref([])
const users = ref([])
const roles = ref([])
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const editingGroup = ref(null)
const currentGroup = ref(null)

const groupForm = ref({
  name: '',
  description: '',
  owners: [],
  allowed_roles: [],
  allowed_users: [],
  chatbot_policy: null
})

const chatbotPolicyJson = ref('')

onMounted(async () => {
  await loadGroups()
  await loadUsers()
  await loadRoles()
})

const loadGroups = async () => {
  try {
    await groupsStore.fetchGroups()
    groups.value = groupsStore.groups
  } catch (e) {
    console.error('Failed to load groups', e)
    if (window.$toast) {
      window.$toast.show(t('admin.groups.failedToLoadGroups'), 'error')
    }
  }
}

const loadUsers = async () => {
  try {
    const res = await usersAPI.list()
    if (res.is_success) {
      users.value = res.data || []
    }
  } catch (e) {
    console.error('Failed to load users', e)
  }
}

const loadRoles = async () => {
  try {
    await rolesStore.fetchRoles()
    roles.value = rolesStore.roles
  } catch (e) {
    console.error('Failed to load roles', e)
  }
}

const viewGroup = async (group) => {
  try {
    await groupsStore.fetchGroup(group.id)
    currentGroup.value = groupsStore.currentGroup
    showDetailModal.value = true
  } catch (e) {
    console.error('Failed to load group details', e)
    if (window.$toast) {
      window.$toast.show(t('admin.groups.failedToLoadGroupDetails'), 'error')
    }
  }
}

const editGroup = (group) => {
  editingGroup.value = group
  groupForm.value = {
    name: group.name || '',
    description: group.description || '',
    owners: group.owners || [],
    allowed_roles: group.allowed_roles || [],
    allowed_users: group.allowed_users || [],
    chatbot_policy: group.chatbot_policy
  }
  chatbotPolicyJson.value = group.chatbot_policy
    ? JSON.stringify(group.chatbot_policy, null, 2)
    : ''
  showCreateModal.value = true
}

const saveGroup = async () => {
  try {
    const data = { ...groupForm.value }
    if (chatbotPolicyJson.value.trim()) {
      try {
        data.chatbot_policy = JSON.parse(chatbotPolicyJson.value)
      } catch (e) {
        if (window.$toast) {
          window.$toast.show(t('admin.groups.invalidChatbotPolicyJson'), 'error')
        }
        return
      }
    }
    const wasEditing = !!editingGroup.value
    if (editingGroup.value) {
      await groupsStore.updateGroup(editingGroup.value.id, data)
    } else {
      await groupsStore.createGroup(data)
    }
    await loadGroups()
    showCreateModal.value = false
    editingGroup.value = null
    groupForm.value = {
      name: '',
      description: '',
      owners: [],
      allowed_roles: [],
      allowed_users: [],
      chatbot_policy: null
    }
    chatbotPolicyJson.value = ''
    if (window.$toast) {
      window.$toast.show(
        wasEditing ? t('admin.groups.groupUpdated') : t('admin.groups.groupCreated'),
        'success'
      )
    }
  } catch (e) {
    console.error('Failed to save group', e)
    if (window.$toast) {
      window.$toast.show(t('admin.groups.failedToSaveGroup'), 'error')
    }
  }
}

const deleteGroup = async (group) => {
  if (confirm(t('admin.groups.deleteGroupConfirm', { name: group.name }))) {
    try {
      await groupsStore.deleteGroup(group.id)
      await loadGroups()
      if (window.$toast) {
        window.$toast.show(t('admin.groups.groupDeleted'), 'success')
      }
    } catch (e) {
      console.error('Failed to delete group', e)
      if (window.$toast) {
        window.$toast.show(t('admin.groups.failedToDeleteGroup'), 'error')
      }
    }
  }
}

const addOwner = (userId) => {
  if (!userId) return
  if (!groupForm.value.owners) {
    groupForm.value.owners = []
  }
  if (!groupForm.value.owners.includes(userId)) {
    groupForm.value.owners.push(userId)
  }
}

const removeOwner = (userId) => {
  if (groupForm.value.owners) {
    groupForm.value.owners = groupForm.value.owners.filter(id => id !== userId)
  }
}

const addAllowedRole = (roleName) => {
  if (!roleName) return
  if (!groupForm.value.allowed_roles) {
    groupForm.value.allowed_roles = []
  }
  if (!groupForm.value.allowed_roles.includes(roleName)) {
    groupForm.value.allowed_roles.push(roleName)
  }
}

const removeAllowedRole = (roleName) => {
  if (groupForm.value.allowed_roles) {
    groupForm.value.allowed_roles = groupForm.value.allowed_roles.filter(r => r !== roleName)
  }
}

const addAllowedUser = (userId) => {
  if (!userId) return
  if (!groupForm.value.allowed_users) {
    groupForm.value.allowed_users = []
  }
  if (!groupForm.value.allowed_users.includes(userId)) {
    groupForm.value.allowed_users.push(userId)
  }
}

const removeAllowedUser = (userId) => {
  if (groupForm.value.allowed_users) {
    groupForm.value.allowed_users = groupForm.value.allowed_users.filter(id => id !== userId)
  }
}

const getUserName = (userId) => {
  const user = users.value.find(u => u.id === userId)
  return user ? `${user.name} (${user.email})` : t('admin.groups.userFallback', { id: userId })
}

const associateDocuments = () => {
  if (window.$toast) {
    window.$toast.show(t('admin.groups.documentAssociationNotImplemented'), 'info')
  }
}

const associateFolders = () => {
  if (window.$toast) {
    window.$toast.show(t('admin.groups.folderAssociationNotImplemented'), 'info')
  }
}

const associateTags = () => {
  if (window.$toast) {
    window.$toast.show(t('admin.groups.tagAssociationNotImplemented'), 'info')
  }
}

const reindexGroup = async () => {
  if (!currentGroup.value) return
  if (confirm(t('admin.groups.reindexGroupConfirm'))) {
    try {
      await groupsStore.reindexGroup(currentGroup.value.id)
      if (window.$toast) {
        window.$toast.show(t('admin.groups.reindexingStarted'), 'success')
      }
    } catch (e) {
      console.error('Failed to reindex group', e)
      if (window.$toast) {
        window.$toast.show(t('admin.groups.failedToReindexGroup'), 'error')
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
  cursor: pointer;
  transition: all 0.2s;
}

.group-card:hover {
  border-color: var(--primary);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.group-card h3 {
  margin: 0 0 0.5rem 0;
  color: var(--primary);
}

.group-description {
  color: #666;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.group-meta {
  display: flex;
  gap: 1rem;
  margin: 1rem 0;
  font-size: 0.9rem;
  color: #666;
  flex-wrap: wrap;
}

.group-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.empty-state {
  grid-column: 1 / -1;
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

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-family: inherit;
}

.multi-select {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.selected-items {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
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
}

.group-detail {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.detail-section h4 {
  margin: 0 0 0.75rem 0;
  color: var(--primary);
}

.member-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.member-badge {
  background: var(--primary-light);
  color: var(--primary);
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
}

.associations {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.count {
  color: #666;
  font-size: 0.9rem;
}
</style>
