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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useFoldersStore } from '../store/folders'
import { documentsAPI } from '../services/api'
import { FolderTree, Modal, StatusBadge } from '../components'
import { Folder, FolderPlus, Edit, Trash2 } from 'lucide-vue-next'

const router = useRouter()
const foldersStore = useFoldersStore()

const selectedFolder = ref(null)
const folderDocuments = ref([])
const showCreateModal = ref(false)
const editingFolder = ref(null)

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
</style>

