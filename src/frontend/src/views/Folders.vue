<template>
  <div class="folders-page">
    <div class="page-header">
      <h1>Folders</h1>
      <button @click="showCreateModal = true" class="btn-primary">
        <FolderPlus :size="20" />
        New Folder
      </button>
    </div>

    <div class="folders-content">
      <div class="folders-sidebar">
        <div class="sidebar-section">
          <h3>All Folders</h3>
          <FolderTree
            v-if="hasFolders"
            :folders="folderTree"
            :selected-id="selectedFolderId"
            @select="selectFolder"
          />
          <div v-else-if="!isLoading" class="empty-folders">
            <Folder :size="32" />
            <p>No folders yet. Create your first folder.</p>
          </div>
          <div v-else class="loading-state">Loading folders...</div>
        </div>
      </div>

      <div class="folders-main">
        <div v-if="selectedFolder" class="folder-detail">
          <div class="folder-header">
            <h2>{{ selectedFolder.name || 'Unnamed Folder' }}</h2>
            <div class="folder-actions">
              <button @click="openShareModal(selectedFolder)" class="btn-secondary">
                <Share2 :size="16" />
                Share
              </button>
              <button @click="openAddDocumentsModal" class="btn-secondary">
                <FilePlus :size="16" />
                Add Documents
              </button>
              <button @click="editFolder(selectedFolder)" class="btn-secondary">
                <Edit :size="16" />
                Edit
              </button>
              <button @click="deleteFolder(selectedFolder)" class="btn-danger">
                <Trash2 :size="16" />
                Delete
              </button>
            </div>
          </div>
          <div v-if="selectedFolder.description" class="folder-description">
            {{ selectedFolder.description }}
          </div>
          <div class="folder-meta">
            <span>Documents: {{ documentsList.length }}</span>
            <span>Created: {{ formatDate(selectedFolder.created_at) }}</span>
          </div>
          <div class="documents-list">
            <h3>Documents in this folder</h3>
            <div v-if="documentsList.length === 0" class="empty-state">
              No documents in this folder
            </div>
            <div v-else class="documents-grid">
              <div
                v-for="doc in documentsList"
                :key="doc.id"
                class="document-card"
                @click="viewDocument(doc.id)"
              >
                <h4>{{ doc.title || 'Untitled Document' }}</h4>
                <div class="document-meta">
                  <StatusBadge :status="doc.status || 'unknown'" />
                  <span>{{ formatSize(doc.size) }}</span>
                  <span>{{ formatDate(doc.created_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <Folder :size="48" />
          <p>Select a folder to view its contents</p>
        </div>
      </div>
    </div>

    <!-- Create/Edit Folder Modal -->
    <Modal v-model:show="showCreateModal" :title="modalTitle">
      <div class="form-group">
        <label>Name *</label>
        <input v-model="folderForm.name" required />
      </div>
      <div class="form-group">
        <label>Parent Folder</label>
        <select v-model="folderForm.parent_id">
          <option :value="null">None (Root)</option>
          <option v-for="f in allFolders" :key="f.id" :value="f.id">
            {{ f.name || 'Unnamed Folder' }}
          </option>
        </select>
      </div>
      <div class="form-group">
        <label>Description</label>
        <textarea v-model="folderForm.description" rows="3"></textarea>
      </div>
      <template #footer>
        <button type="button" @click="showCreateModal = false" class="btn-secondary">
          Cancel
        </button>
        <button type="button" @click="saveFolder" class="btn-primary">Save</button>
      </template>
    </Modal>

    <!-- Share Folder Modal -->
    <Modal v-model:show="showShareModal" title="Share Folder" size="large">
      <div v-if="selectedFolder">
        <div class="share-section">
          <h4>Share with Users</h4>
          <div class="share-input-group">
            <input
              v-model="shareUserEmail"
              type="email"
              placeholder="Enter user email"
              @keyup.enter="addShareUser"
              class="share-input"
            />
            <button @click="addShareUser" class="btn-primary">Add</button>
          </div>
          <div v-if="shareForm.user_emails.length > 0" class="share-list">
            <div v-for="(email, idx) in shareForm.user_emails" :key="idx" class="share-item">
              <span>{{ email }}</span>
              <button @click="removeShareUser(idx)" class="btn-remove-small">×</button>
            </div>
          </div>
        </div>

        <div class="share-section">
          <h4>Share with Roles</h4>
          <div class="share-input-group">
            <select v-model="shareRoleId" class="share-select">
              <option :value="null">Select a role</option>
              <option v-for="role in roles" :key="role.id" :value="role.id">
                {{ role.name }}
              </option>
            </select>
            <button @click="addShareRole" class="btn-primary">Add</button>
          </div>
          <div v-if="shareForm.role_ids.length > 0" class="share-list">
            <div v-for="(roleId, idx) in shareForm.role_ids" :key="idx" class="share-item">
              <span>{{ getRoleName(roleId) }}</span>
              <button @click="removeShareRole(idx)" class="btn-remove-small">×</button>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>Expiration Date (Optional)</label>
          <input v-model="shareForm.expires_at" type="datetime-local" />
        </div>

        <div v-if="folderShares.length > 0" class="share-section">
          <h4>Current Shares</h4>
          <div class="shares-list">
            <div v-for="share in folderShares" :key="share.id" class="share-item">
              <div class="share-info">
                <span class="share-type">{{ share.target_type }}</span>
                <span v-if="share.target_email">{{ share.target_email }}</span>
                <span v-else-if="share.target_role_name">{{ share.target_role_name }}</span>
                <span v-if="share.expires_at" class="share-expires">
                  Expires: {{ formatDate(share.expires_at) }}
                </span>
                <span v-else class="share-expires">No expiration</span>
              </div>
              <button @click="removeShare(share.id)" class="btn-danger-small">Remove</button>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <button type="button" @click="showShareModal = false" class="btn-secondary">
          Close
        </button>
        <button type="button" @click="saveShares" class="btn-primary">Save Shares</button>
      </template>
    </Modal>

    <!-- Add Documents Modal -->
    <Modal v-model:show="showAddDocumentsModal" title="Add Documents to Folder">
      <div v-if="selectedFolder">
        <div class="form-group">
          <label class="form-label-large">Select Documents</label>
          <p class="form-hint">Choose documents to add to folder "{{ selectedFolder.name }}"</p>
          <div class="documents-selector">
            <div v-if="availableDocuments.length === 0" class="empty-documents-state">
              <FileText :size="48" class="empty-icon" />
              <p class="empty-title">No documents available</p>
              <p class="empty-description">All documents are already in this folder or you don't have access to any documents.</p>
            </div>
            <div v-else class="documents-checkbox-list">
              <label
                v-for="doc in availableDocuments"
                :key="doc.id"
                class="document-checkbox-item"
                :class="{ 'selected': selectedDocumentIds.includes(doc.id) }"
              >
                <div class="checkbox-wrapper">
                  <input
                    type="checkbox"
                    :value="doc.id"
                    v-model="selectedDocumentIds"
                    class="document-checkbox"
                  />
                  <div class="checkbox-custom"></div>
                </div>
                <div class="document-info">
                  <div class="document-title-row">
                    <FileText :size="18" class="doc-icon" />
                    <span class="document-title">{{ doc.title || 'Untitled Document' }}</span>
                  </div>
                  <div class="document-meta-row">
                    <span class="doc-size">{{ formatSize(doc.size) }}</span>
                    <span class="doc-separator">•</span>
                    <span class="doc-date">{{ formatDate(doc.created_at) }}</span>
                    <span v-if="doc.file_extension" class="doc-extension">{{ doc.file_extension.toUpperCase() }}</span>
                  </div>
                </div>
              </label>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <button type="button" @click="showAddDocumentsModal = false" class="btn-secondary">
          Cancel
        </button>
        <button 
          type="button" 
          @click="moveDocumentsToFolder" 
          class="btn-primary"
          :disabled="selectedDocumentIds.length === 0"
        >
          <FilePlus :size="16" />
          Add {{ selectedDocumentIds.length }} Document{{ selectedDocumentIds.length !== 1 ? 's' : '' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useFoldersStore } from '../store/folders'
import { useRolesStore } from '../store/roles'
import { foldersAPI, documentsAPI } from '../services/api'
import { FolderTree, Modal, StatusBadge } from '../components'
import { Folder, FolderPlus, Edit, Trash2, Share2, FilePlus, FileText } from 'lucide-vue-next'

const router = useRouter()
const foldersStore = useFoldersStore()
const rolesStore = useRolesStore()

const selectedFolder = ref(null)
const folderDocuments = ref([])
const showCreateModal = ref(false)
const editingFolder = ref(null)
const showShareModal = ref(false)
const showAddDocumentsModal = ref(false)
const folderShares = ref([])
const availableDocuments = ref([])
const selectedDocumentIds = ref([])

const shareForm = ref({
  user_emails: [],
  role_ids: [],
  expires_at: null
})
const shareUserEmail = ref('')
const shareRoleId = ref(null)

const roles = computed(() => rolesStore.roles || [])

const folderForm = ref({
  name: '',
  parent_id: null,
  description: ''
})

const folderTree = computed(() => {
  const tree = foldersStore.folderTree
  return Array.isArray(tree) ? tree : []
})
const allFolders = computed(() => {
  const folders = foldersStore.folders
  return Array.isArray(folders) ? folders : []
})
const isLoading = computed(() => foldersStore.loading)
const hasFolders = computed(() => {
  return folderTree.value && folderTree.value.length > 0
})
const selectedFolderId = computed(() => {
  return selectedFolder.value ? selectedFolder.value.id : null
})
const modalTitle = computed(() => {
  return editingFolder.value ? 'Edit Folder' : 'Create Folder'
})
const documentsList = computed(() => {
  return Array.isArray(folderDocuments.value) ? folderDocuments.value : []
})

onMounted(async () => {
  await foldersStore.fetchFolders()
})

const selectFolder = async (folder) => {
  selectedFolder.value = folder
  await foldersStore.fetchFolder(folder.id)
  await loadFolderDocuments(folder.id)
  await loadFolderShares(folder.id)
}

const loadFolderDocuments = async (folderId) => {
  try {
    const res = await documentsAPI.list({ folder_id: folderId })
    if (res.is_success) {
      folderDocuments.value = res.data?.items || res.data || []
    }
  } catch (e) {
    console.error('Failed to load folder documents', e)
  }
}

const editFolder = (folder) => {
  editingFolder.value = folder
  folderForm.value = {
    name: folder.name,
    parent_id: folder.parent_id,
    description: folder.description || ''
  }
  showCreateModal.value = true
}

const saveFolder = async () => {
  try {
    if (editingFolder.value) {
      await foldersStore.updateFolder(editingFolder.value.id, folderForm.value)
    } else {
      await foldersStore.createFolder(folderForm.value)
    }
    showCreateModal.value = false
    editingFolder.value = null
    folderForm.value = { name: '', parent_id: null, description: '' }
    if (window.$toast) {
      window.$toast.show(
        editingFolder.value ? 'Folder updated' : 'Folder created',
        'success'
      )
    }
  } catch (e) {
    console.error('Failed to save folder', e)
    if (window.$toast) {
      window.$toast.show('Failed to save folder', 'error')
    }
  }
}

const deleteFolder = async (folder) => {
  if (confirm(`Delete folder "${folder.name}"?`)) {
    try {
      await foldersStore.deleteFolder(folder.id)
      if (selectedFolder.value?.id === folder.id) {
        selectedFolder.value = null
        folderDocuments.value = []
      }
      if (window.$toast) {
        window.$toast.show('Folder deleted', 'success')
      }
    } catch (e) {
      console.error('Failed to delete folder', e)
      if (window.$toast) {
        window.$toast.show('Failed to delete folder', 'error')
      }
    }
  }
}

const viewDocument = (id) => {
  router.push(`/documents/${id}`)
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'N/A'
  try {
    return new Date(dateStr).toLocaleDateString()
  } catch (e) {
    return 'N/A'
  }
}

const formatSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

const loadFolderShares = async (folderId) => {
  try {
    const res = await foldersAPI.getShares(folderId)
    if (res.is_success) {
      folderShares.value = res.data || []
    }
  } catch (e) {
    console.error('Failed to load folder shares', e)
  }
}

const openShareModal = async (folder) => {
  selectedFolder.value = folder
  shareForm.value = {
    user_emails: [],
    role_ids: [],
    expires_at: null
  }
  shareUserEmail.value = ''
  shareRoleId.value = null
  await loadFolderShares(folder.id)
  showShareModal.value = true
}

const addShareUser = () => {
  if (shareUserEmail.value && shareUserEmail.value.trim()) {
    const email = shareUserEmail.value.trim()
    if (!shareForm.value.user_emails.includes(email)) {
      shareForm.value.user_emails.push(email)
      shareUserEmail.value = ''
    }
  }
}

const removeShareUser = (index) => {
  shareForm.value.user_emails.splice(index, 1)
}

const addShareRole = () => {
  if (shareRoleId.value && !shareForm.value.role_ids.includes(shareRoleId.value)) {
    shareForm.value.role_ids.push(shareRoleId.value)
    shareRoleId.value = null
  }
}

const removeShareRole = (index) => {
  shareForm.value.role_ids.splice(index, 1)
}

const getRoleName = (roleId) => {
  const role = roles.value.find(r => r.id === roleId)
  return role ? role.name : `Role ${roleId}`
}

const saveShares = async () => {
  if (!selectedFolder.value) return
  
  try {
    const data = {
      user_emails: shareForm.value.user_emails,
      role_ids: shareForm.value.role_ids
    }
    
    if (shareForm.value.expires_at) {
      // Convert local datetime to ISO string
      const date = new Date(shareForm.value.expires_at)
      data.expires_at = date.toISOString()
    }
    
    const res = await foldersAPI.share(selectedFolder.value.id, data)
    if (res.is_success) {
      await loadFolderShares(selectedFolder.value.id)
      if (window.$toast) {
        window.$toast.show('Folder shared successfully', 'success')
      }
      shareForm.value = {
        user_emails: [],
        role_ids: [],
        expires_at: null
      }
      shareUserEmail.value = ''
      shareRoleId.value = null
    }
  } catch (e) {
    console.error('Failed to share folder', e)
    if (window.$toast) {
      window.$toast.show('Failed to share folder', 'error')
    }
  }
}

const removeShare = async (shareId) => {
  if (!selectedFolder.value) return
  
  if (confirm('Remove this share?')) {
    try {
      await foldersAPI.deleteShare(selectedFolder.value.id, shareId)
      await loadFolderShares(selectedFolder.value.id)
      if (window.$toast) {
        window.$toast.show('Share removed', 'success')
      }
    } catch (e) {
      console.error('Failed to remove share', e)
      if (window.$toast) {
        window.$toast.show('Failed to remove share', 'error')
      }
    }
  }
}

const openAddDocumentsModal = async () => {
  if (!selectedFolder.value) return
  
  selectedDocumentIds.value = []
  availableDocuments.value = []
  
  try {
    // Load all accessible documents (excluding those already in this folder)
    // API has max limit of 100, so we'll load in batches if needed
    const res = await documentsAPI.list({ limit: 100, skip: 0 })
    if (res.is_success) {
      const allDocs = res.data?.items || res.data || []
      console.log('Loaded documents:', allDocs.length, 'Current folder ID:', selectedFolder.value.id)
      
      // Filter out documents already in this folder
      // Include documents with folder_id = null/undefined or folder_id != selectedFolder.id
      availableDocuments.value = allDocs.filter(doc => {
        // Include if no folder_id (null/undefined) or different folder_id
        return !doc.folder_id || doc.folder_id !== selectedFolder.value.id
      })
      
      console.log('Available documents after filter:', availableDocuments.value.length)
      
      // If we got 100 documents, there might be more - load additional pages
      if (allDocs.length === 100 && res.data?.total > 100) {
        const totalPages = Math.ceil(res.data.total / 100)
        for (let page = 1; page < totalPages; page++) {
          try {
            const nextRes = await documentsAPI.list({ limit: 100, skip: page * 100 })
            if (nextRes.is_success) {
              const nextDocs = nextRes.data?.items || nextRes.data || []
              const filteredNextDocs = nextDocs.filter(doc => {
                return !doc.folder_id || doc.folder_id !== selectedFolder.value.id
              })
              availableDocuments.value.push(...filteredNextDocs)
            }
          } catch (e) {
            console.error(`Failed to load page ${page + 1}`, e)
          }
        }
      }
    } else {
      console.error('API response not successful:', res)
    }
  } catch (e) {
    console.error('Failed to load documents', e)
    if (window.$toast) {
      window.$toast.show('Failed to load documents', 'error')
    }
    availableDocuments.value = []
  }
  showAddDocumentsModal.value = true
}

const moveDocumentsToFolder = async () => {
  if (!selectedFolder.value || selectedDocumentIds.value.length === 0) return
  
  try {
    let successCount = 0
    let failCount = 0
    
    for (const docId of selectedDocumentIds.value) {
      try {
        await documentsAPI.update(docId, { folder_id: selectedFolder.value.id })
        successCount++
      } catch (e) {
        console.error(`Failed to move document ${docId}`, e)
        failCount++
      }
    }
    
    await loadFolderDocuments(selectedFolder.value.id)
    showAddDocumentsModal.value = false
    selectedDocumentIds.value = []
    
    if (window.$toast) {
      if (failCount === 0) {
        window.$toast.show(`${successCount} document(s) added to folder`, 'success')
      } else {
        window.$toast.show(`${successCount} added, ${failCount} failed`, 'warning')
      }
    }
  } catch (e) {
    console.error('Failed to move documents', e)
    if (window.$toast) {
      window.$toast.show('Failed to add documents', 'error')
    }
  }
}

onMounted(async () => {
  await foldersStore.fetchFolders()
  await rolesStore.fetchRoles()
})
</script>

<style scoped>
.folders-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.folders-content {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 2rem;
}

.folders-sidebar {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  height: fit-content;
}

.sidebar-section h3 {
  margin: 0 0 1rem 0;
  color: var(--primary);
}

.folders-main {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.folder-detail {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.folder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.folder-actions {
  display: flex;
  gap: 0.75rem;
}

.folder-description {
  color: #666;
  padding: 1rem;
  background: var(--bg-light);
  border-radius: 6px;
}

.folder-meta {
  display: flex;
  gap: 2rem;
  color: #666;
  font-size: 0.9rem;
}

.documents-list h3 {
  margin: 0 0 1rem 0;
  color: var(--primary);
}

.documents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}

.document-card {
  padding: 1rem;
  border: 1px solid #eee;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.document-card:hover {
  border-color: var(--primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.document-card h4 {
  margin: 0 0 0.5rem 0;
  color: var(--primary);
}

.document-meta {
  display: flex;
  gap: 0.75rem;
  font-size: 0.85rem;
  color: #666;
  flex-wrap: wrap;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #666;
}

.empty-state svg {
  margin-bottom: 1rem;
  color: #ccc;
}

.empty-folders {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.empty-folders svg {
  margin-bottom: 0.5rem;
  color: #ccc;
}

.loading-state {
  text-align: center;
  padding: 2rem;
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
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-family: inherit;
}

.form-group textarea {
  resize: vertical;
}

.documents-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.btn-small {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.share-section {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #eee;
}

.share-section:last-child {
  border-bottom: none;
}

.share-section h4 {
  margin: 0 0 1rem 0;
  color: var(--primary);
}

.share-input-group {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.share-input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.share-select {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.share-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.share-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: var(--bg-light);
  border-radius: 6px;
}

.share-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
}

.share-type {
  padding: 0.25rem 0.5rem;
  background: var(--primary-light);
  color: var(--primary);
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.share-expires {
  color: #666;
  font-size: 0.85rem;
}

.btn-remove-small {
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
}

.btn-remove-small:hover {
  background: #dc2626;
}

.btn-danger-small {
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-danger-small:hover {
  background: #dc2626;
}

.shares-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.documents-selector {
  max-height: 500px;
  min-height: 200px;
  overflow-y: auto;
  border: 2px solid var(--bg-light);
  border-radius: 12px;
  padding: 0.75rem;
  background: var(--bg-white);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.02);
  transition: border-color 0.2s ease;
}

.documents-selector:focus-within {
  border-color: var(--primary-light);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.02), 0 0 0 3px rgba(108, 92, 231, 0.1);
}

.empty-documents-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  text-align: center;
  min-height: 200px;
}

.empty-icon {
  color: var(--text-lighter);
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-medium);
  margin: 0 0 0.5rem 0;
}

.empty-description {
  font-size: 0.9rem;
  color: var(--text-light);
  margin: 0;
  max-width: 400px;
  line-height: 1.5;
}

.documents-selector::-webkit-scrollbar {
  width: 8px;
}

.documents-selector::-webkit-scrollbar-track {
  background: var(--bg-light);
  border-radius: 4px;
}

.documents-selector::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 4px;
}

.documents-selector::-webkit-scrollbar-thumb:hover {
  background: #999;
}

.documents-checkbox-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.document-checkbox-item {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
  border: 2px solid transparent;
  border-radius: 10px;
  background: var(--bg-white);
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.document-checkbox-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: var(--gradient-primary);
  transform: scaleY(0);
  transition: transform 0.2s ease;
}

.document-checkbox-item:hover {
  background: var(--bg-light);
  border-color: var(--primary-light);
  transform: translateX(4px);
  box-shadow: 0 2px 8px rgba(108, 92, 231, 0.1);
}

.document-checkbox-item:hover::before {
  transform: scaleY(1);
}

.document-checkbox-item.selected {
  background: linear-gradient(135deg, rgba(108, 92, 231, 0.05) 0%, rgba(155, 140, 255, 0.05) 100%);
  border-color: var(--primary);
  box-shadow: 0 2px 12px rgba(108, 92, 231, 0.15);
}

.document-checkbox-item.selected::before {
  transform: scaleY(1);
}

.checkbox-wrapper {
  position: relative;
  flex-shrink: 0;
  margin-top: 2px;
}

.document-checkbox {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  cursor: pointer;
}

.checkbox-custom {
  width: 20px;
  height: 20px;
  border: 2px solid #ddd;
  border-radius: 6px;
  background: var(--bg-white);
  transition: all 0.2s ease;
  position: relative;
  cursor: pointer;
}

.document-checkbox-item:hover .checkbox-custom {
  border-color: var(--primary);
  background: var(--primary-light);
}

.document-checkbox:checked + .checkbox-custom {
  background: var(--primary);
  border-color: var(--primary);
}

.document-checkbox:checked + .checkbox-custom::after {
  content: '✓';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 14px;
  font-weight: bold;
  line-height: 1;
}

.document-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.document-title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.doc-icon {
  flex-shrink: 0;
  color: var(--primary);
  stroke-width: 2;
}

.document-title {
  font-weight: 500;
  color: var(--text-dark);
  font-size: 0.95rem;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.document-checkbox-item.selected .document-title {
  color: var(--primary);
  font-weight: 600;
}

.document-meta-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  font-size: 0.85rem;
  color: var(--text-light);
  margin-left: 1.75rem;
}

.doc-size {
  font-weight: 500;
  color: var(--text-medium);
}

.doc-separator {
  color: var(--text-lighter);
}

.doc-date {
  color: var(--text-light);
}

.doc-extension {
  background: var(--primary-light);
  color: var(--primary);
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Responsive Design */
@media (max-width: 768px) {
  .documents-selector {
    max-height: 400px;
    padding: 0.5rem;
  }

  .document-checkbox-item {
    padding: 0.75rem;
    gap: 0.75rem;
  }

  .document-title-row {
    gap: 0.5rem;
  }

  .doc-icon {
    width: 16px;
    height: 16px;
  }

  .document-title {
    font-size: 0.9rem;
  }

  .document-meta-row {
    font-size: 0.8rem;
    margin-left: 1.5rem;
  }

  .documents-checkbox-list {
    gap: 0.5rem;
  }
}

@media (max-width: 480px) {
  .document-checkbox-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .checkbox-wrapper {
    align-self: flex-start;
  }

  .document-meta-row {
    margin-left: 0;
  }

  .empty-documents-state {
    padding: 2rem 1rem;
    min-height: 150px;
  }

  .empty-icon {
    width: 36px;
    height: 36px;
  }

  .empty-title {
    font-size: 1rem;
  }

  .empty-description {
    font-size: 0.85rem;
  }
}

/* Button disabled state */
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.btn-primary:disabled:hover {
  transform: none;
  box-shadow: none;
}

/* Add Documents Modal specific styles */
/* Override modal container size for add documents modal */
:deep(.modal-overlay:has(.documents-selector)) .modal-container {
  max-width: 800px;
  width: 95%;
}

@media (max-width: 768px) {
  :deep(.modal-overlay:has(.documents-selector)) .modal-container {
    max-width: 95%;
    margin: 1rem;
  }
}

@media (max-width: 480px) {
  :deep(.modal-overlay:has(.documents-selector)) .modal-container {
    max-width: 100%;
    margin: 0.5rem;
    max-height: 95vh;
  }
}

.form-label-large {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-dark);
  margin-bottom: 0.5rem;
}

.form-hint {
  font-size: 0.9rem;
  color: var(--text-light);
  margin: 0 0 1rem 0;
  line-height: 1.5;
}

/* Responsive modal */
@media (max-width: 768px) {
  :deep(.add-documents-modal .modal-container) {
    max-width: 95%;
    margin: 1rem;
  }
}

@media (max-width: 480px) {
  :deep(.add-documents-modal .modal-container) {
    max-width: 100%;
    margin: 0.5rem;
    max-height: 95vh;
  }

  .form-label-large {
    font-size: 0.95rem;
  }

  .form-hint {
    font-size: 0.85rem;
  }
}
</style>

