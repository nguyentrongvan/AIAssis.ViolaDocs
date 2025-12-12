<template>
  <div class="admin-page">
    <div class="page-header">
      <h1>Document Groups</h1>
      <button @click="showCreateModal = true" class="btn-primary">
        <Plus :size="20" />
        Create Group
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
          <span>Documents: {{ group.document_count || 0 }}</span>
          <span>Members: {{ group.member_count || 0 }}</span>
          <span>Owners: {{ group.owners?.length || 0 }}</span>
        </div>
        <div class="group-actions">
          <button @click.stop="editGroup(group)" class="btn-small">
            <Edit :size="16" />
            Edit
          </button>
          <button @click.stop="deleteGroup(group)" class="btn-small btn-danger">
            <Trash2 :size="16" />
            Delete
          </button>
        </div>
      </div>
      <div v-if="groups.length === 0" class="empty-state">
        No groups found. Create your first group.
      </div>
    </div>

    <!-- Create/Edit Group Modal -->
    <Modal
      v-model:show="showCreateModal"
      :title="editingGroup ? 'Edit Group' : 'Create Group'"
    >
      <div class="form-group">
        <label>Name *</label>
        <input v-model="groupForm.name" required />
      </div>
      <div class="form-group">
        <label>Description</label>
        <textarea v-model="groupForm.description" rows="3"></textarea>
      </div>
      <div class="form-group">
        <label>Owners</label>
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
            <option value="">Add owner...</option>
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
        <label>Allowed Roles</label>
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
            <option value="">Add role...</option>
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
        <label>Allowed Users</label>
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
            <option value="">Add user...</option>
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
        <label>Chatbot Policy (JSON)</label>
        <textarea
          v-model="chatbotPolicyJson"
          rows="4"
          placeholder='{"allowed_sources": ["docs"], "allow_preview": true}'
        ></textarea>
      </div>
      <template #footer>
        <button
          type="button"
          @click="showCreateModal = false"
          class="btn-secondary"
        >
          Cancel
        </button>
        <button type="button" @click="saveGroup" class="btn-primary">Save</button>
      </template>
    </Modal>

    <!-- Group Detail Modal -->
    <Modal v-model:show="showDetailModal" :title="currentGroup?.name || 'Group Details'">
      <div v-if="currentGroup" class="group-detail">
        <div class="detail-section">
          <h4>Description</h4>
          <p>{{ currentGroup.description || 'No description' }}</p>
        </div>
        <div class="detail-section">
          <h4>Owners</h4>
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
          <h4>Allowed Roles</h4>
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
          <h4>Allowed Users</h4>
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
          <h4>Associated Documents</h4>
          <div class="associations">
            <button @click="associateDocuments" class="btn-small">
              <FileText :size="16" />
              Manage Documents
            </button>
            <span class="count">{{ currentGroup.document_count || 0 }} documents</span>
          </div>
        </div>
        <div class="detail-section">
          <h4>Associated Folders</h4>
          <div class="associations">
            <button @click="associateFolders" class="btn-small">
              <Folder :size="16" />
              Manage Folders
            </button>
            <span class="count">{{ currentGroup.folder_count || 0 }} folders</span>
          </div>
        </div>
        <div class="detail-section">
          <h4>Associated Tags</h4>
          <div class="associations">
            <button @click="associateTags" class="btn-small">
              <Tag :size="16" />
              Manage Tags
            </button>
            <span class="count">{{ currentGroup.tag_count || 0 }} tags</span>
          </div>
        </div>
        <div class="detail-section">
          <h4>Actions</h4>
          <button @click="reindexGroup" class="btn-primary">
            <RefreshCw :size="16" />
            Reindex Group
          </button>
        </div>
      </div>
      <template #footer>
        <button @click="showDetailModal = false" class="btn-secondary">Close</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useGroupsStore } from '../../store/groups'
import { useRolesStore } from '../../store/roles'
import { groupsAPI, usersAPI } from '../../services/api'
import { Modal } from '../../components'
import { Plus, Edit, Trash2, FileText, Folder, Tag, RefreshCw } from 'lucide-vue-next'

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
      window.$toast.show('Failed to load groups', 'error')
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
      window.$toast.show('Failed to load group details', 'error')
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
          window.$toast.show('Invalid chatbot policy JSON', 'error')
        }
        return
      }
    }
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
        editingGroup.value ? 'Group updated' : 'Group created',
        'success'
      )
    }
  } catch (e) {
    console.error('Failed to save group', e)
    if (window.$toast) {
      window.$toast.show('Failed to save group', 'error')
    }
  }
}

const deleteGroup = async (group) => {
  if (confirm(`Delete group "${group.name}"?`)) {
    try {
      await groupsStore.deleteGroup(group.id)
      await loadGroups()
      if (window.$toast) {
        window.$toast.show('Group deleted', 'success')
      }
    } catch (e) {
      console.error('Failed to delete group', e)
      if (window.$toast) {
        window.$toast.show('Failed to delete group', 'error')
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
  return user ? `${user.name} (${user.email})` : `User ${userId}`
}

const associateDocuments = () => {
  if (window.$toast) {
    window.$toast.show('Document association not yet implemented', 'info')
  }
}

const associateFolders = () => {
  if (window.$toast) {
    window.$toast.show('Folder association not yet implemented', 'info')
  }
}

const associateTags = () => {
  if (window.$toast) {
    window.$toast.show('Tag association not yet implemented', 'info')
  }
}

const reindexGroup = async () => {
  if (!currentGroup.value) return
  if (confirm('Reindex this group? This may take a while.')) {
    try {
      await groupsStore.reindexGroup(currentGroup.value.id)
      if (window.$toast) {
        window.$toast.show('Reindexing started', 'success')
      }
    } catch (e) {
      console.error('Failed to reindex group', e)
      if (window.$toast) {
        window.$toast.show('Failed to reindex group', 'error')
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
