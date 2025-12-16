<template>
  <div class="recycle-bin-page">
    <div class="page-header">
      <h1>Recycle Bin</h1>
    </div>

    <!-- Filters -->
    <div class="filters-bar">
      <div class="filter-group">
        <label>Search</label>
        <input
          v-model="filters.search"
          @keyup.enter="loadDocuments"
          placeholder="Search deleted documents..."
          class="search-input"
        />
      </div>
      <button @click="loadDocuments" class="btn-secondary">
        <Search :size="16" />
        Filter
      </button>
      <button @click="clearFilters" class="btn-clear">
        <X :size="16" />
        Clear
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading">Loading deleted documents...</div>

    <!-- Documents Table -->
    <div v-else-if="documents.length > 0" class="documents-content">
      <div class="documents-table">
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Status</th>
              <th>Size</th>
              <th>Folder</th>
              <th>Deleted By</th>
              <th>Deleted At</th>
              <th>Days Until Purge</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="doc in documents"
              :key="doc.id"
              @click="$router.push(`/documents/${doc.id}`)"
              class="table-row"
            >
              <td>
                <div class="table-title">
                  <FileText :size="16" />
                  <div class="table-title-content">
                    <span class="table-title-text">{{ doc.title || 'Untitled Document' }}</span>
                    <span v-if="doc.document_type || doc.file_extension" class="doc-type-badge-small">
                      {{ getDocumentTypeLabel(doc) }}
                    </span>
                  </div>
                </div>
              </td>
              <td><StatusBadge :status="doc.status" /></td>
              <td>{{ formatSize(doc.size) }}</td>
              <td>{{ doc.folder?.name || '-' }}</td>
              <td>{{ doc.deleted_by?.name || 'Unknown' }}</td>
              <td>{{ formatDate(doc.deleted_at) }}</td>
              <td>
                <span :class="['days-badge', { 'days-warning': doc.days_until_purge <= 1 }]">
                  {{ doc.days_until_purge !== null ? `${doc.days_until_purge} day(s)` : 'N/A' }}
                </span>
              </td>
              <td>
                <div class="table-actions" @click.stop>
                  <button
                    @click="restoreDocument(doc)"
                    class="btn-link-small"
                  >
                    Restore
                  </button>
                  <button
                    v-if="isAdmin"
                    @click="confirmPermanentDelete(doc)"
                    class="btn-link-small btn-danger"
                  >
                    Delete Permanently
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <Pagination
        v-model:page="currentPage"
        :total-pages="totalPages"
        @change="loadDocuments"
      />
    </div>

    <!-- Empty State -->
    <div v-else-if="!loading && documents.length === 0" class="empty-state">
      <Trash2 :size="48" />
      <p>Recycle Bin is empty</p>
    </div>

    <!-- Restore Confirmation Modal -->
    <Modal
      :show="showRestoreModal"
      title="Restore Document"
      @update:show="showRestoreModal = $event"
    >
      <p v-if="documentToRestore">
        Are you sure you want to restore "{{ documentToRestore.title }}"?
      </p>
      <template #footer>
        <button @click="showRestoreModal = false" class="btn-secondary">Cancel</button>
        <button @click="restoreDocumentConfirm" class="btn-primary">Restore</button>
      </template>
    </Modal>

    <!-- Permanent Delete Confirmation Modal -->
    <Modal
      :show="showPermanentDeleteModal"
      title="Delete Permanently"
      @update:show="showPermanentDeleteModal = $event"
    >
      <p v-if="documentToDelete">
        Are you sure you want to permanently delete "{{ documentToDelete.title }}"? 
        This action cannot be undone. All files, embeddings, and related data will be permanently removed.
      </p>
      <template #footer>
        <button @click="showPermanentDeleteModal = false" class="btn-secondary">Cancel</button>
        <button @click="deletePermanently" class="btn-danger">Delete Permanently</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'
import { recycleBinAPI } from '../services/api'
import { StatusBadge, Pagination, Modal } from '../components'
import {
  Search,
  FileText,
  X,
  Trash2
} from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()

const documents = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showRestoreModal = ref(false)
const showPermanentDeleteModal = ref(false)
const documentToRestore = ref(null)
const documentToDelete = ref(null)

const filters = ref({
  search: ''
})

const isAdmin = computed(() => authStore.user?.role === 'admin')

const totalPages = computed(() => {
  return Math.ceil(total.value / pageSize.value)
})

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getDocumentTypeLabel = (doc) => {
  if (doc.file_extension) {
    const ext = doc.file_extension.toUpperCase()
    const typeMap = {
      'PDF': 'PDF',
      'DOCX': 'DOCX',
      'DOC': 'DOC',
      'XLSX': 'XLSX',
      'XLS': 'XLS',
      'PPTX': 'PPTX',
      'PPT': 'PPT',
      'PNG': 'PNG',
      'JPG': 'JPG',
      'JPEG': 'JPG',
      'GIF': 'GIF',
      'WEBP': 'WEBP'
    }
    return typeMap[ext] || ext
  }
  
  if (doc.document_type) {
    const typeMap = {
      'application': 'Document',
      'image': 'Image',
      'video': 'Video',
      'audio': 'Audio',
      'text': 'Text'
    }
    return typeMap[doc.document_type] || doc.document_type
  }
  
  return 'File'
}

const loadDocuments = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    
    if (filters.value.search) {
      params.search = filters.value.search
    }

    const res = await recycleBinAPI.list(params)
    if (res.is_success) {
      documents.value = res.data?.items || res.data || []
      total.value = res.data?.total || documents.value.length
    }
  } catch (e) {
    console.error('Failed to load deleted documents', e)
    if (window.$toast) {
      window.$toast.show('Failed to load deleted documents', 'error')
    }
  } finally {
    loading.value = false
  }
}

const clearFilters = () => {
  filters.value = {
    search: ''
  }
  currentPage.value = 1
  loadDocuments()
}

const confirmRestore = (doc) => {
  documentToRestore.value = doc
  showRestoreModal.value = true
}

const restoreDocument = async (doc) => {
  confirmRestore(doc)
}

const restoreDocumentConfirm = async () => {
  if (!documentToRestore.value) return
  
  try {
    const res = await recycleBinAPI.restore(documentToRestore.value.id)
    if (res.is_success) {
      if (window.$toast) {
        window.$toast.show('Document restored successfully', 'success')
      }
      showRestoreModal.value = false
      documentToRestore.value = null
      await loadDocuments()
    } else {
      if (window.$toast) {
        window.$toast.show(res.message || 'Failed to restore document', 'error')
      }
    }
  } catch (e) {
    console.error('Failed to restore document', e)
    if (window.$toast) {
      window.$toast.show('Failed to restore document', 'error')
    }
  }
}

const confirmPermanentDelete = (doc) => {
  documentToDelete.value = doc
  showPermanentDeleteModal.value = true
}

const deletePermanently = async () => {
  if (!documentToDelete.value) return
  
  try {
    const res = await recycleBinAPI.deletePermanently(documentToDelete.value.id)
    if (res.is_success) {
      if (window.$toast) {
        window.$toast.show('Document permanently deleted', 'success')
      }
      showPermanentDeleteModal.value = false
      documentToDelete.value = null
      await loadDocuments()
    } else {
      if (window.$toast) {
        window.$toast.show(res.message || 'Failed to delete document', 'error')
      }
    }
  } catch (e) {
    console.error('Failed to permanently delete document', e)
    if (window.$toast) {
      window.$toast.show('Failed to permanently delete document', 'error')
    }
  }
}

onMounted(async () => {
  await loadDocuments()
})
</script>

<style scoped>
.recycle-bin-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-xl);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-xl);
}

.page-header h1 {
  font-size: 2rem;
  font-weight: 700;
  margin: 0;
}

.filters-bar {
  display: flex;
  gap: var(--space-md);
  align-items: flex-end;
  margin-bottom: var(--space-lg);
  padding: var(--space-lg);
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.filter-group label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-medium);
}

.filter-group input,
.filter-group select {
  padding: var(--space-sm) var(--space-md);
  border: 1.5px solid #e5e7eb;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  background: var(--bg-white);
  transition: all var(--transition-base);
}

.filter-group input:hover,
.filter-group select:hover {
  border-color: var(--primary);
}

.filter-group input:focus,
.filter-group select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-light);
}

.search-input {
  min-width: 200px;
}

.btn-secondary {
  background: var(--primary);
  color: white;
  border: none;
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-base);
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  box-shadow: var(--shadow-sm);
}

.btn-secondary:hover {
  background: var(--primary-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-secondary:active {
  transform: translateY(0);
  box-shadow: var(--shadow-sm);
}

.btn-clear {
  background: var(--bg-white);
  border: 1.5px solid #e5e7eb;
  color: var(--text-medium);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-base);
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  box-shadow: var(--shadow-sm);
}

.btn-clear:hover {
  background: #fef2f2;
  border-color: #fca5a5;
  color: #dc2626;
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-clear:active {
  transform: translateY(0);
  box-shadow: var(--shadow-sm);
}

.documents-table {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow-x: auto;
}

.documents-table table {
  width: 100%;
  border-collapse: collapse;
}

.documents-table thead {
  background: var(--bg-light);
}

.documents-table th {
  padding: var(--space-md);
  text-align: left;
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-medium);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.documents-table td {
  padding: var(--space-md);
  border-top: 1px solid #e5e7eb;
}

.table-row {
  cursor: pointer;
  transition: background-color var(--transition-base);
}

.table-row:hover {
  background-color: var(--bg-light);
}

.table-title {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.table-title-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.table-title-text {
  font-weight: 500;
  color: var(--text-dark);
}

.doc-type-badge-small {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  background: var(--bg-light);
  border-radius: var(--radius-sm);
  color: var(--text-medium);
}

.table-actions {
  display: flex;
  gap: var(--space-sm);
}

.btn-link-small {
  padding: 0.25rem 0.5rem;
  background: none;
  border: none;
  color: var(--primary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: color var(--transition-base);
}

.btn-link-small:hover {
  color: var(--primary-dark);
}

.btn-link-small.btn-danger {
  color: var(--error);
}

.btn-link-small.btn-danger:hover {
  color: #c0392b;
}

.days-badge {
  padding: 0.25rem 0.75rem;
  background: var(--info-light);
  color: var(--info);
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-weight: 500;
}

.days-badge.days-warning {
  background: var(--warn-light);
  color: var(--warn);
}

.empty-state {
  text-align: center;
  padding: var(--space-3xl);
  color: var(--text-light);
}

.empty-state svg {
  margin-bottom: var(--space-md);
  opacity: 0.5;
}

.loading {
  text-align: center;
  padding: var(--space-3xl);
  color: var(--text-light);
}
</style>

