<template>
  <div class="upload-page">
    <h1 class="page-header">Upload Documents</h1>
    
    <!-- Upload Zone -->
    <div class="upload-zone" @drop.prevent="handleDrop" @dragover.prevent @click="openFileDialog">
      <input ref="fileInput" type="file" multiple @change="handleFileSelect" style="display: none" />
      <input ref="folderInput" type="file" webkitdirectory directory multiple @change="handleFileSelect" style="display: none" />
      <div class="upload-content">
        <Upload class="upload-icon" />
        <p>Drag & drop files here or 
          <button @click.stop="openFileDialog" class="btn-link">browse files</button>
          <span class="separator">|</span>
          <button @click.stop="openFolderDialog" class="btn-link">browse folder</button>
        </p>
        <p class="hint">Supports: PDF, DOCX, XLSX, CSV, TXT, Images</p>
      </div>
    </div>

    <!-- File List -->
    <div v-if="files.length > 0" class="file-list">
      <div v-for="(file, idx) in files" :key="idx" class="file-item">
        <div class="file-header">
          <div class="file-info">
            <span class="file-type-badge" :class="getFileTypeClass(file.file.type)">
              {{ getFileTypeLabel(file.file.type) }}
            </span>
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatSize(file.size) }}</span>
          </div>
          <button v-if="file.status === 'pending'" @click="removeFile(idx)" class="btn-remove">×</button>
        </div>
        
        <div v-if="file.status === 'pending'" class="file-metadata">
          <div class="form-group">
            <label>Title</label>
            <input v-model="file.metadata.title" type="text" :placeholder="file.name" />
          </div>
          <div class="form-group">
            <label>Tags (comma-separated)</label>
            <input v-model="file.metadata.tags" type="text" placeholder="e.g., invoice, 2024, important" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Folder</label>
              <div class="picker-input">
                <input
                  :value="getFolderName(file.metadata.folder_id)"
                  readonly
                  placeholder="Select folder"
                  @click="openFolderPicker(idx)"
                />
                <button
                  type="button"
                  @click="openFolderPicker(idx)"
                  class="picker-btn"
                >
                  <Folder :size="16" />
                </button>
                <button
                  v-if="file.metadata.folder_id"
                  type="button"
                  @click.stop="file.metadata.folder_id = null"
                  class="picker-clear"
                >
                  ×
                </button>
              </div>
            </div>
            <div class="form-group">
              <label>Retention Policy</label>
              <select v-model.number="file.metadata.retention_policy_id">
                <option :value="null">Default</option>
                <option
                  v-for="p in retentionPolicies"
                  :key="p.id"
                  :value="p.id"
                >
                  {{ p.name }} ({{ p.duration_days }} days)
                </option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>Share Permissions</label>
            <div class="permissions-checkbox-group">
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  v-model="file.metadata.share_permissions"
                  :value="'view'"
                  checked
                />
                <span>View</span>
              </label>
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  v-model="file.metadata.share_permissions"
                  value="search"
                />
                <span>Search</span>
              </label>
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  v-model="file.metadata.share_permissions"
                  value="chat"
                />
                <span>Chat</span>
              </label>
            </div>
            <p class="hint-text">Select permissions for shared users/roles. View is required.</p>
          </div>
          <div class="form-group">
            <label>ACL - Allowed Users</label>
            <div class="acl-selector">
              <div class="selected-items">
                <span
                  v-for="userId in file.metadata.allowed_users || []"
                  :key="userId"
                  class="selected-item"
                >
                  {{ getUserName(userId) }}
                  <button @click="removeUser(idx, userId)" class="item-remove">×</button>
                </span>
              </div>
              <button
                @click="openUserPicker(idx)"
                class="btn-add-acl"
                type="button"
              >
                + Add Users
              </button>
            </div>
          </div>
          <div class="form-group">
            <label>ACL - Allowed Roles</label>
            <div class="acl-selector">
              <div class="selected-items">
                <span
                  v-for="roleId in file.metadata.allowed_roles || []"
                  :key="roleId"
                  class="selected-item"
                >
                  {{ getRoleName(roleId) }}
                  <button @click="removeRole(idx, roleId)" class="item-remove">×</button>
                </span>
              </div>
              <button
                @click="openRolePicker(idx)"
                class="btn-add-acl"
                type="button"
              >
                + Add Roles
              </button>
            </div>
          </div>
          <div class="form-group">
            <label>Sensitivity</label>
            <select v-model="file.metadata.sensitivity">
              <option value="">None</option>
              <option value="public">Public</option>
              <option value="internal">Internal</option>
              <option value="confidential">Confidential</option>
              <option value="restricted">Restricted</option>
            </select>
          </div>
          <div class="form-group">
            <label>Workflow Template</label>
            <input v-model="file.metadata.workflow_template" type="text" placeholder="Optional workflow template name" />
          </div>
        </div>

        <div v-if="file.status === 'uploading' || file.status === 'processing'" class="file-progress">
          <div class="progress-bar" :style="{ width: file.progress + '%' }"></div>
          <span>{{ file.progress }}%</span>
        </div>
        
        <div class="file-status">
          <div v-if="file.status === 'calculating'" class="status-item">
            <Loader2 class="status-icon" /> Calculating checksum...
          </div>
          <div v-else-if="file.status === 'uploading'" class="status-item">
            <Loader2 class="status-icon" /> Uploading...
          </div>
          <div v-else-if="file.status === 'processing'" class="status-item">
            <Loader2 class="status-icon" /> Processing...
          </div>
          <div v-else-if="file.status === 'done'" class="status-item success">
            <CheckCircle class="status-icon" /> Done
            <a v-if="file.document_id" :href="`/documents/${file.document_id}`" class="doc-link">
              View Document
            </a>
          </div>
          <div v-else-if="file.status === 'error'" class="status-item error">
            <XCircle class="status-icon" /> {{ file.error || 'Error' }}
          </div>
        </div>
      </div>
    </div>

    <!-- Upload Actions -->
    <div v-if="files.length > 0" class="upload-actions">
      <button @click="startUpload" :disabled="uploading || files.every(f => f.status === 'done')" class="btn-primary">
        {{ uploading ? 'Uploading...' : 'Upload All' }}
      </button>
      <button @click="clearFiles" class="btn-secondary">Clear All</button>
    </div>

    <!-- Folder Picker Modal -->
    <Modal v-model:show="showFolderPicker" title="Select Folder">
      <FolderTree
        :folders="foldersStore.folderTree"
        @select="selectFolder"
      />
      <template #footer>
        <button @click="showFolderPicker = false" class="btn-secondary">Cancel</button>
      </template>
    </Modal>

    <!-- User Picker Modal -->
    <Modal v-model:show="showUserPicker" title="Select Users" size="medium">
      <div class="picker-search">
        <input
          v-model="userSearchQuery"
          type="text"
          placeholder="Search users by name or email..."
          class="search-input"
        />
      </div>
      <div class="picker-list">
        <div
          v-for="user in filteredUsers"
          :key="user.id"
          class="picker-item"
        >
          <label class="picker-checkbox">
            <input
              type="checkbox"
              :checked="isUserSelected(user.id)"
              @change="toggleUser(user.id)"
            />
            <span class="picker-label">
              <strong>{{ user.name }}</strong>
              <span class="picker-email">{{ user.email }}</span>
            </span>
          </label>
        </div>
        <div v-if="filteredUsers.length === 0" class="picker-empty">
          {{ userSearchQuery ? 'No users found' : 'No users available' }}
        </div>
      </div>
      <template #footer>
        <button @click="showUserPicker = false" class="btn-secondary">Cancel</button>
        <button @click="confirmUsers" class="btn-primary">Confirm ({{ tempSelectedUsers.length }})</button>
      </template>
    </Modal>

    <!-- Role Picker Modal -->
    <Modal v-model:show="showRolePicker" title="Select Roles" size="medium">
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
        >
          <label class="picker-checkbox">
            <input
              type="checkbox"
              :checked="isRoleSelected(role.id)"
              @change="toggleRole(role.id)"
            />
            <span class="picker-label">
              <strong>{{ role.name }}</strong>
            </span>
          </label>
        </div>
        <div v-if="filteredRoles.length === 0" class="picker-empty">
          {{ roleSearchQuery ? 'No roles found' : 'No roles available' }}
        </div>
      </div>
      <template #footer>
        <button @click="showRolePicker = false" class="btn-secondary">Cancel</button>
        <button @click="confirmRoles" class="btn-primary">Confirm ({{ tempSelectedRoles.length }})</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useFoldersStore } from '../store/folders'
import { useSettingsStore } from '../store/settings'
import { useRolesStore } from '../store/roles'
import { usersAPI, uploadsAPI } from '../services/api'
import { FolderTree, Modal } from '../components'
import { Upload, Loader2, CheckCircle, XCircle, Folder, Shield } from 'lucide-vue-next'

const fileInput = ref(null)
const folderInput = ref(null)
const files = ref([])
const uploading = ref(false)
const foldersStore = useFoldersStore()
const settingsStore = useSettingsStore()
const rolesStore = useRolesStore()

const folders = ref([])
const retentionPolicies = ref([])
const roles = computed(() => rolesStore.roles || [])
const users = ref([])
const showFolderPicker = ref(false)
const showUserPicker = ref(false)
const showRolePicker = ref(false)
const currentFileIndex = ref(null)
const tempSelectedUsers = ref([])
const tempSelectedRoles = ref([])
const userSearchQuery = ref('')
const roleSearchQuery = ref('')

const handleDrop = (e) => {
  const droppedFiles = Array.from(e.dataTransfer.files)
  addFiles(droppedFiles)
}

const openFileDialog = () => {
  if (fileInput.value) {
    fileInput.value.click()
  }
}

const openFolderDialog = () => {
  if (folderInput.value) {
    folderInput.value.click()
  }
}

const handleFileSelect = (e) => {
  const selectedFiles = Array.from(e.target.files)
  addFiles(selectedFiles)
  // Reset input to allow selecting same file again
  e.target.value = ''
}

const addFiles = (fileList) => {
  fileList.forEach(file => {
    files.value.push({
      name: file.name,
      size: file.size,
      file,
      progress: 0,
      status: 'pending',
      checksum: null,
      document_id: null,
      error: null,
      metadata: {
        share_permissions: ['view'], // Default: view permission
        title: '',
        tags: '',
        folder_id: null,
        retention_policy_id: null,
        sensitivity: '',
        workflow_template: '',
        allowed_users: [],
        allowed_roles: []
      }
    })
  })
}

const removeFile = (index) => {
  files.value.splice(index, 1)
}

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

const getFileTypeLabel = (mimeType) => {
  if (mimeType === 'application/pdf') return 'PDF'
  if (mimeType.includes('wordprocessingml')) return 'DOCX'
  if (mimeType.includes('spreadsheetml')) return 'XLSX'
  if (mimeType === 'text/csv' || mimeType === 'application/csv') return 'CSV'
  if (mimeType === 'text/plain') return 'TXT'
  if (mimeType.startsWith('image/')) return 'IMAGE'
  return 'FILE'
}

const getFileTypeClass = (mimeType) => {
  if (mimeType === 'application/pdf') return 'type-pdf'
  if (mimeType.includes('wordprocessingml')) return 'type-docx'
  if (mimeType.includes('spreadsheetml')) return 'type-xlsx'
  if (mimeType === 'text/csv' || mimeType === 'application/csv') return 'type-csv'
  if (mimeType === 'text/plain') return 'type-txt'
  if (mimeType.startsWith('image/')) return 'type-image'
  return 'type-other'
}

// Calculate SHA-256 checksum
const calculateChecksum = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        const arrayBuffer = e.target.result
        const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer)
        const hashArray = Array.from(new Uint8Array(hashBuffer))
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
        resolve(hashHex)
      } catch (err) {
        reject(err)
      }
    }
    reader.onerror = reject
    reader.readAsArrayBuffer(file)
  })
}

const parseTags = (tagsString) => {
  if (!tagsString || !tagsString.trim()) return []
  return tagsString.split(',').map(t => t.trim()).filter(t => t.length > 0)
}

const startUpload = async () => {
  uploading.value = true
  
  for (const fileItem of files.value) {
    if (fileItem.status === 'done' || fileItem.status === 'uploading' || fileItem.status === 'processing') {
      continue
    }
    
    try {
      // Calculate checksum
      fileItem.status = 'calculating'
      fileItem.checksum = await calculateChecksum(fileItem.file)
      
      // Init upload
      fileItem.status = 'uploading'
      const initRes = await uploadsAPI.init({
        filename: fileItem.name,
        size: fileItem.size,
        mime: fileItem.file.type || 'application/octet-stream',
        checksum: fileItem.checksum
      })
      
      if (!initRes.is_success) {
        throw new Error(initRes.message || 'Failed to initialize upload')
      }
      
      const { upload_id, upload_url } = initRes.data
      
      // Upload file to MinIO
      await uploadFile(fileItem.file, upload_url, (progress) => {
        fileItem.progress = progress
      })
      
      // Prepare metadata for finalize
      const tags = parseTags(fileItem.metadata.tags)
      const finalizeData = {
        title: fileItem.metadata.title || fileItem.name,
        tags: tags,
        folder_id: fileItem.metadata.folder_id || null,
        retention_policy_id: fileItem.metadata.retention_policy_id || null,
        sensitivity: fileItem.metadata.sensitivity || null,
        workflow_template: fileItem.metadata.workflow_template || null,
        allowed_users: fileItem.metadata.allowed_users || [],
        allowed_roles: fileItem.metadata.allowed_roles || [],
        share_permissions: fileItem.metadata.share_permissions || ['view']
      }
      
      // Finalize upload
      fileItem.status = 'processing'
      const finalizeRes = await uploadsAPI.finalize(upload_id, finalizeData)
      
      if (!finalizeRes.is_success) {
        throw new Error(finalizeRes.message || 'Failed to finalize upload')
      }
      
      fileItem.document_id = finalizeRes.data.document_id
      fileItem.status = 'done'
      fileItem.progress = 100
      
    } catch (e) {
      fileItem.status = 'error'
      fileItem.error = e.response?.data?.message || e.message || 'Upload failed'
      console.error('Upload failed', e)
    }
  }
  
  uploading.value = false
}

const uploadFile = (file, url, onProgress) => {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    })
    
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve()
      } else {
        reject(new Error(`Upload failed with status ${xhr.status}`))
      }
    })
    
    xhr.addEventListener('error', () => {
      reject(new Error('Network error during upload'))
    })
    
    xhr.addEventListener('abort', () => {
      reject(new Error('Upload aborted'))
    })
    
    xhr.open('PUT', url)
    xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream')
    xhr.send(file)
  })
}

const clearFiles = () => {
  files.value = []
}

onMounted(async () => {
  await loadFolders()
  await loadRetentionPolicies()
  await loadRoles()
  await loadUsers()
})

const loadFolders = async () => {
  try {
    await foldersStore.fetchFolders()
    folders.value = foldersStore.folders
  } catch (e) {
    console.error('Failed to load folders', e)
  }
}

const loadRetentionPolicies = async () => {
  try {
    await settingsStore.fetchRetentionPolicies()
    retentionPolicies.value = settingsStore.retentionPolicies
  } catch (e) {
    console.error('Failed to load retention policies', e)
  }
}

const loadRoles = async () => {
  try {
    await rolesStore.fetchRoles()
    if (rolesStore.roles.length === 0) {
      console.warn('No roles found in system')
    }
  } catch (e) {
    console.error('Failed to load roles', e)
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

const openFolderPicker = (index) => {
  currentFileIndex.value = index
  showFolderPicker.value = true
}

const selectFolder = (folder) => {
  if (currentFileIndex.value !== null) {
    files.value[currentFileIndex.value].metadata.folder_id = folder.id
  }
  showFolderPicker.value = false
  currentFileIndex.value = null
}

const openUserPicker = (index) => {
  currentFileIndex.value = index
  // Initialize temp selection with currently selected users
  tempSelectedUsers.value = [...(files.value[index].metadata.allowed_users || [])]
  userSearchQuery.value = ''
  showUserPicker.value = true
}

const openRolePicker = (index) => {
  currentFileIndex.value = index
  // Initialize temp selection with currently selected roles
  tempSelectedRoles.value = [...(files.value[index].metadata.allowed_roles || [])]
  roleSearchQuery.value = ''
  showRolePicker.value = true
}

const filteredUsers = computed(() => {
  if (!users.value || !Array.isArray(users.value)) {
    return []
  }
  if (!userSearchQuery.value) {
    return users.value.filter(user => user && user.id && user.name)
  }
  const query = userSearchQuery.value.toLowerCase()
  return users.value.filter(user => 
    user && user.id && user.name && (
      user.name.toLowerCase().includes(query) ||
      (user.email && user.email.toLowerCase().includes(query))
    )
  )
})

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

const isUserSelected = (userId) => {
  return tempSelectedUsers.value.includes(userId)
}

const isRoleSelected = (roleId) => {
  return tempSelectedRoles.value.includes(roleId)
}

const toggleUser = (userId) => {
  const index = tempSelectedUsers.value.indexOf(userId)
  if (index > -1) {
    tempSelectedUsers.value.splice(index, 1)
  } else {
    tempSelectedUsers.value.push(userId)
  }
}

const toggleRole = (roleId) => {
  const index = tempSelectedRoles.value.indexOf(roleId)
  if (index > -1) {
    tempSelectedRoles.value.splice(index, 1)
  } else {
    tempSelectedRoles.value.push(roleId)
  }
}

const confirmUsers = () => {
  if (currentFileIndex.value !== null) {
    files.value[currentFileIndex.value].metadata.allowed_users = [...tempSelectedUsers.value]
  }
  showUserPicker.value = false
  currentFileIndex.value = null
  tempSelectedUsers.value = []
  userSearchQuery.value = ''
}

const confirmRoles = () => {
  if (currentFileIndex.value !== null) {
    files.value[currentFileIndex.value].metadata.allowed_roles = [...tempSelectedRoles.value]
  }
  showRolePicker.value = false
  currentFileIndex.value = null
  tempSelectedRoles.value = []
  roleSearchQuery.value = ''
}

const getFolderName = (folderId) => {
  if (!folderId) return 'None'
  const folder = folders.value.find(f => f.id === folderId)
  return folder ? folder.name : 'Unknown'
}

const addUser = (fileIndex, userId) => {
  if (!userId) return
  const userIdNum = parseInt(userId)
  if (!files.value[fileIndex].metadata.allowed_users) {
    files.value[fileIndex].metadata.allowed_users = []
  }
  if (!files.value[fileIndex].metadata.allowed_users.includes(userIdNum)) {
    files.value[fileIndex].metadata.allowed_users.push(userIdNum)
  }
}

const removeUser = (fileIndex, userId) => {
  if (!files.value[fileIndex].metadata.allowed_users) return
  const index = files.value[fileIndex].metadata.allowed_users.indexOf(userId)
  if (index > -1) {
    files.value[fileIndex].metadata.allowed_users.splice(index, 1)
  }
}

const getUserName = (userId) => {
  const user = users.value.find(u => u.id === userId)
  return user ? `${user.name} (${user.email})` : `User ${userId}`
}

const addRole = (fileIndex, roleId) => {
  if (!roleId) return
  const roleIdNum = parseInt(roleId)
  if (!files.value[fileIndex].metadata.allowed_roles) {
    files.value[fileIndex].metadata.allowed_roles = []
  }
  if (!files.value[fileIndex].metadata.allowed_roles.includes(roleIdNum)) {
    files.value[fileIndex].metadata.allowed_roles.push(roleIdNum)
  }
}

const removeRole = (fileIndex, roleId) => {
  if (!files.value[fileIndex].metadata.allowed_roles) return
  const index = files.value[fileIndex].metadata.allowed_roles.indexOf(roleId)
  if (index > -1) {
    files.value[fileIndex].metadata.allowed_roles.splice(index, 1)
  }
}

const getRoleName = (roleId) => {
  const rolesList = roles.value || []
  if (!Array.isArray(rolesList)) {
    return `Role ${roleId}`
  }
  const role = rolesList.find(r => r && r.id === roleId)
  return role ? role.name : `Role ${roleId}`
}
</script>

<style scoped>
.upload-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
}

.upload-zone {
  border: 3px dashed transparent;
  border-radius: var(--radius-xl);
  padding: var(--space-3xl);
  text-align: center;
  background: var(--bg-white);
  margin-bottom: var(--space-xl);
  cursor: pointer;
  transition: all var(--transition-base);
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-lg);
  background-clip: padding-box;
}

.upload-zone::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: var(--radius-xl);
  padding: 3px;
  background: var(--gradient-cyan-purple);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  animation: shimmer 3s ease-in-out infinite;
  z-index: -1;
}

.upload-zone:hover::before {
  animation: shimmer 1s ease-in-out infinite;
}

.upload-zone:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-2xl), var(--shadow-glow-cyan);
}

.upload-zone.dragover {
  border-color: var(--ai-cyan);
  background: var(--gradient-ai-soft);
  animation: pulse 1s ease-in-out infinite;
}

.upload-content {
  pointer-events: none;
  position: relative;
  z-index: 1;
}

.upload-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto var(--space-lg);
  color: var(--primary);
  stroke-width: 1.5;
  animation: float 3s var(--ease-in-out) infinite;
  filter: drop-shadow(0 0 20px rgba(0, 217, 255, 0.3));
}

.hint {
  color: #666;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}

.file-list {
  margin-bottom: 2rem;
}

.file-item {
  background: var(--bg-white);
  padding: var(--space-xl);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  position: relative;
  overflow: hidden;
  animation: fadeInUp var(--transition-base) var(--ease-out) both;
  border: 2px solid transparent;
  transition: all var(--transition-base);
  margin-bottom: var(--space-lg);
}

.file-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gradient-cyan-purple);
  transform: scaleX(0);
  transition: transform var(--transition-base);
}

.file-item:hover::before {
  transform: scaleX(1);
}

.file-item:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-2xl), var(--shadow-glow);
  border-color: var(--ai-cyan);
}

.file-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.file-type-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.type-pdf { background: #ff4444; color: white; }
.type-docx { background: #2b579a; color: white; }
.type-xlsx { background: #217346; color: white; }
.type-image { background: #4caf50; color: white; }
.type-other { background: #666; color: white; }

.file-name {
  font-weight: 500;
  flex: 1;
}

.file-size {
  color: #666;
  font-size: 0.9rem;
}

.btn-remove {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #999;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  line-height: 1;
}

.btn-remove:hover {
  color: var(--error);
}

.file-metadata {
  background: var(--bg-light);
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  font-size: 0.9rem;
  color: #333;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.file-progress {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.progress-bar {
  flex: 1;
  height: 10px;
  background: var(--gradient-cyan-purple);
  border-radius: var(--radius-full);
  transition: width var(--transition-base);
  box-shadow: 0 0 10px rgba(0, 217, 255, 0.4);
  position: relative;
  overflow: hidden;
}

.progress-bar::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: shimmer 2s ease-in-out infinite;
}

.file-status {
  margin-top: 0.5rem;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.status-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  stroke-width: 2;
}

.status-item.success {
  color: var(--success);
}

.status-item.error {
  color: var(--error);
}

.status-item .status-icon {
  animation: spin 1s linear infinite;
}

.status-item.success .status-icon,
.status-item.error .status-icon {
  animation: none;
}

.btn-link {
  background: none;
  border: none;
  color: var(--primary);
  cursor: pointer;
  text-decoration: underline;
  font-size: inherit;
  padding: 0;
  margin: 0;
}

.btn-link:hover {
  color: var(--primary-dark);
}

.separator {
  margin: 0 0.5rem;
  color: #999;
}

.doc-link {
  margin-left: 0.5rem;
  color: var(--primary);
  text-decoration: none;
}

.doc-link:hover {
  text-decoration: underline;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.upload-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.picker-input {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.picker-input input {
  flex: 1;
  cursor: pointer;
}

.picker-btn {
  padding: 0.5rem;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.picker-btn:hover {
  background: var(--primary-dark);
}

.picker-clear {
  padding: 0.5rem;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1.2rem;
  line-height: 1;
}

.picker-clear:hover {
  background: #dc2626;
}

.acl-selector {
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
  display: flex;
  align-items: center;
}

.item-remove:hover {
  color: #ef4444;
}

.acl-select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
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

.picker-list {
  max-height: 400px;
  overflow-y: auto;
  margin: 1rem 0;
}

.picker-item {
  padding: 0.75rem;
  border-bottom: 1px solid var(--border-color);
  transition: background var(--transition-base);
}

.picker-item:hover {
  background: var(--bg-light);
}

.picker-item:last-child {
  border-bottom: none;
}

.picker-checkbox {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  width: 100%;
}

.picker-checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--primary);
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

.picker-email {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.picker-empty {
  padding: 2rem;
  text-align: center;
  color: var(--text-secondary);
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

.permissions-checkbox-group {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.9rem;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--primary);
}

.hint-text {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-top: 0.5rem;
  font-style: italic;
}
</style>
