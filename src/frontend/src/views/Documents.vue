<template>
  <div class="documents-page">
    <div class="page-header">
      <h1>Documents</h1>
      <div class="header-actions">
        <router-link to="/upload" class="btn-primary">
          <Upload :size="18" />
          Upload
        </router-link>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters-bar">
      <div class="filter-group">
        <label>Status</label>
        <select v-model="filters.status">
          <option value="">All</option>
          <option value="ready">Ready</option>
          <option value="processing">Processing</option>
          <option value="failed">Failed</option>
        </select>
      </div>
      <div class="filter-group">
        <label>Folder</label>
        <select v-model.number="filters.folder_id">
          <option :value="null">All Folders</option>
          <option v-for="f in folders" :key="f.id" :value="f.id">
            {{ f.name }}
          </option>
        </select>
      </div>
      <div class="filter-group">
        <label>Search</label>
        <input
          v-model="filters.search"
          @keyup.enter="loadDocuments"
          placeholder="Search documents..."
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

    <!-- View Options -->
    <div class="view-controls">
      <div class="view-options">
        <button
          @click="viewMode = 'cards'"
          :class="['view-btn', { active: viewMode === 'cards' }]"
        >
          <Grid :size="16" />
        </button>
        <button
          @click="viewMode = 'table'"
          :class="['view-btn', { active: viewMode === 'table' }]"
        >
          <List :size="16" />
        </button>
      </div>
      <div class="results-count">
        {{ total }} document{{ total !== 1 ? 's' : '' }}
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading">Loading documents...</div>

    <!-- Documents List -->
    <div v-else-if="documents.length > 0" class="documents-content">
      <!-- Card View -->
      <div v-if="viewMode === 'cards'" class="documents-grid">
        <div
          v-for="doc in documents"
          :key="doc.id"
          class="document-card"
          @click="$router.push(`/documents/${doc.id}`)"
        >
          <div class="card-thumbnail" v-if="doc.thumbnail_url">
            <img :src="doc.thumbnail_url" :alt="doc.title" />
          </div>
          <div class="card-thumbnail-placeholder" v-else>
            <FileText :size="32" />
          </div>
          <div class="card-content">
            <div class="card-header">
              <h3>{{ doc.title || 'Untitled Document' }}</h3>
              <span 
                v-if="doc.document_type || doc.file_extension" 
                :class="['doc-type-badge', getDocumentTypeClass(doc)]"
              >
                {{ getDocumentTypeLabel(doc) }}
              </span>
            </div>
            <div class="card-meta">
              <StatusBadge :status="doc.status" />
              <span>{{ formatSize(doc.size) }}</span>
              <span>{{ formatDate(doc.created_at) }}</span>
            </div>
            <div v-if="doc.folder" class="card-folder">
              <Folder :size="14" />
              {{ doc.folder.name }}
            </div>
            <div v-if="doc.tags && doc.tags.length > 0" class="card-tags">
              <span v-for="tag in doc.tags.slice(0, 3)" :key="tag" class="tag-small">
                {{ tag }}
              </span>
              <div v-if="doc.tags.length > 3" class="tag-more-wrapper">
                <span class="tag-more">+{{ doc.tags.length - 3 }}</span>
                <div class="tag-tooltip">
                  <div class="tag-tooltip-content">
                    <div class="tag-tooltip-title">All Tags</div>
                    <div class="tag-tooltip-tags">
                      <span v-for="tag in doc.tags" :key="tag" class="tag-tooltip-item">
                        {{ tag }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="card-actions">
            <button
              @click.stop="$router.push(`/documents/${doc.id}`)"
              class="btn-link-small"
            >
              View
            </button>
            <button
              @click.stop="downloadDocument(doc.id)"
              class="btn-link-small"
            >
              Download
            </button>
          </div>
        </div>
      </div>

      <!-- Table View -->
      <div v-else class="documents-table">
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Status</th>
              <th>Size</th>
              <th>Folder</th>
              <th>Created</th>
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
                    <span 
                      v-if="doc.document_type || doc.file_extension" 
                      :class="['doc-type-badge-small', getDocumentTypeClass(doc)]"
                    >
                      {{ getDocumentTypeLabel(doc) }}
                    </span>
                    <span class="table-title-text">{{ doc.title || 'Untitled Document' }}</span>
                  </div>
                </div>
              </td>
              <td><StatusBadge :status="doc.status" /></td>
              <td>{{ formatSize(doc.size) }}</td>
              <td>{{ doc.folder?.name || '-' }}</td>
              <td>{{ formatDate(doc.created_at) }}</td>
              <td>
                <div class="table-actions" @click.stop>
                  <button
                    @click="$router.push(`/documents/${doc.id}`)"
                    class="btn-link-small"
                  >
                    View
                  </button>
                  <button
                    @click="downloadDocument(doc.id)"
                    class="btn-link-small"
                  >
                    Download
                  </button>
                  <button
                    @click="confirmDelete(doc)"
                    class="btn-link-small btn-danger"
                  >
                    Delete
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
      <FileText :size="48" />
      <p>No documents found</p>
      <router-link to="/upload" class="btn-primary">
        Upload your first document
      </router-link>
    </div>

    <!-- Delete Confirmation Modal -->
    <Modal
      :show="showDeleteModal"
      title="Delete Document"
      @update:show="showDeleteModal = $event"
    >
      <p v-if="documentToDelete">
        Are you sure you want to delete "{{ documentToDelete.title }}"? 
        It will be permanently deleted after {{ purgeGracePeriodDays }} day(s).
      </p>
      <template #footer>
        <button @click="showDeleteModal = false" class="btn-secondary">Cancel</button>
        <button @click="deleteDocument" class="btn-danger">Delete</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDocumentsStore } from '../store/documents'
import { useFoldersStore } from '../store/folders'
import { documentsAPI, settingsAPI } from '../services/api'
import { StatusBadge, Pagination, Modal } from '../components'
import {
  Upload,
  Search,
  Grid,
  List,
  FileText,
  Folder,
  X,
  Trash2
} from 'lucide-vue-next'

const router = useRouter()
const documentsStore = useDocumentsStore()
const foldersStore = useFoldersStore()

const documents = ref([])
const folders = ref([])
const loading = ref(false)
const viewMode = ref('cards')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showDeleteModal = ref(false)
const documentToDelete = ref(null)
const purgeGracePeriodDays = ref(1)

const filters = ref({
  status: '',
  folder_id: null,
  search: ''
})

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
    day: 'numeric'
  })
}

const getDocumentTypeLabel = (doc) => {
  // First try file_extension if available
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
      'WEBP': 'WEBP',
      'CSV': 'CSV',
      'TXT': 'TXT'
    }
    return typeMap[ext] || ext
  }
  
  // If no file_extension, try to extract from MIME type
  if (doc.mime) {
    const mime = doc.mime.toLowerCase()
    if (mime === 'application/pdf') return 'PDF'
    if (mime.includes('wordprocessingml')) return 'DOCX'
    if (mime.includes('spreadsheetml')) return 'XLSX'
    if (mime.includes('presentationml')) return 'PPTX'
    if (mime === 'text/csv' || mime === 'application/csv') return 'CSV'
    if (mime === 'text/plain') return 'TXT'
    if (mime.startsWith('image/')) {
      const imgType = mime.split('/')[1]
      if (imgType === 'jpeg') return 'JPG'
      return imgType.toUpperCase()
    }
  }
  
  // Fallback to document_type
  if (doc.document_type) {
    const typeMap = {
      'application': 'DOC',
      'image': 'IMG',
      'video': 'VID',
      'audio': 'AUD',
      'text': 'TXT'
    }
    return typeMap[doc.document_type] || doc.document_type
  }
  
  return 'FILE'
}

const getDocumentTypeClass = (doc) => {
  // Get file extension or extract from MIME
  let ext = ''
  if (doc.file_extension) {
    ext = doc.file_extension.toLowerCase()
  } else if (doc.mime) {
    const mime = doc.mime.toLowerCase()
    if (mime === 'application/pdf') ext = 'pdf'
    else if (mime.includes('wordprocessingml')) ext = 'docx'
    else if (mime.includes('spreadsheetml')) ext = 'xlsx'
    else if (mime.includes('presentationml')) ext = 'pptx'
    else if (mime === 'text/csv' || mime === 'application/csv') ext = 'csv'
    else if (mime === 'text/plain') ext = 'txt'
    else if (mime.startsWith('image/')) {
      const imgType = mime.split('/')[1]
      if (imgType === 'jpeg') ext = 'jpg'
      else ext = imgType
    }
  }
  
  // Return color class based on extension
  const colorMap = {
    'pdf': 'type-pdf',        // Red
    'docx': 'type-docx',      // Blue
    'doc': 'type-docx',       // Blue
    'xlsx': 'type-xlsx',      // Green
    'xls': 'type-xlsx',       // Green
    'pptx': 'type-pptx',      // Orange
    'ppt': 'type-pptx',       // Orange
    'csv': 'type-csv',        // Gray
    'txt': 'type-txt',        // Gray
    'jpg': 'type-image',      // Purple
    'jpeg': 'type-image',     // Purple
    'png': 'type-image',      // Purple
    'gif': 'type-image',      // Purple
    'webp': 'type-image',     // Purple
    'tiff': 'type-image'      // Purple
  }
  
  return colorMap[ext] || 'type-default'
}

const loadDocuments = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    
    if (filters.value.status) {
      params.status = filters.value.status
    }
    if (filters.value.folder_id) {
      params.folder_id = filters.value.folder_id
    }
    if (filters.value.search) {
      params.search = filters.value.search
    }

    const res = await documentsAPI.list(params)
    if (res.is_success) {
      documents.value = res.data?.items || res.data || []
      total.value = res.data?.total || documents.value.length
    }
  } catch (e) {
    console.error('Failed to load documents', e)
    if (window.$toast) {
      window.$toast.show('Failed to load documents', 'error')
    }
  } finally {
    loading.value = false
  }
}

const clearFilters = () => {
  filters.value = {
    status: '',
    folder_id: null,
    search: ''
  }
  currentPage.value = 1
  loadDocuments()
}

const downloadDocument = async (docId) => {
  try {
    const response = await documentsAPI.download(docId)
    const blob = new Blob([response])
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `document-${docId}.pdf`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (e) {
    console.error('Failed to download document', e)
    if (window.$toast) {
      window.$toast.show('Failed to download document', 'error')
    }
  }
}

const confirmDelete = async (doc) => {
  // Load purge grace period
  try {
    const res = await settingsAPI.purgeGracePeriod.get()
    if (res.is_success && res.data) {
      purgeGracePeriodDays.value = res.data.days || 1
    }
  } catch (e) {
    console.error('Failed to load purge grace period', e)
  }
  
  documentToDelete.value = doc
  showDeleteModal.value = true
}

const deleteDocument = async () => {
  if (!documentToDelete.value) return
  
  try {
    const res = await documentsAPI.delete(documentToDelete.value.id)
    if (res.is_success) {
      if (window.$toast) {
        window.$toast.show('Document deleted successfully', 'success')
      }
      showDeleteModal.value = false
      documentToDelete.value = null
      await loadDocuments()
    } else {
      if (window.$toast) {
        window.$toast.show(res.message || 'Failed to delete document', 'error')
      }
    }
  } catch (e) {
    console.error('Failed to delete document', e)
    if (window.$toast) {
      window.$toast.show('Failed to delete document', 'error')
    }
  }
}

onMounted(async () => {
  await foldersStore.fetchFolders()
  folders.value = foldersStore.folders
  await loadDocuments()
})
</script>

<style scoped>
.documents-page {
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

.filter-group select,
.search-input {
  padding: var(--space-sm) var(--space-md);
  border: 1.5px solid #e5e7eb;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  background: var(--bg-white);
  transition: all var(--transition-base);
}

.filter-group select:hover,
.search-input:hover {
  border-color: var(--primary);
}

.filter-group select:focus,
.search-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-light);
}

.search-input {
  min-width: 200px;
}

.view-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-lg);
}

.view-options {
  display: flex;
  gap: var(--space-xs);
}

.view-btn {
  padding: var(--space-sm);
  border: 1px solid var(--border-color);
  background: var(--bg-white);
  border-radius: var(--radius-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all var(--transition-base);
}

.view-btn:hover {
  background: var(--bg-light);
  border-color: var(--primary);
}

.view-btn.active {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.results-count {
  color: var(--text-medium);
  font-size: 0.875rem;
}

.documents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-lg);
  margin-bottom: var(--space-xl);
}

.document-card {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  cursor: pointer;
  transition: all var(--transition-base);
  display: flex;
  flex-direction: column;
}

.document-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.card-thumbnail {
  width: 100%;
  height: 200px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
}

.card-thumbnail::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(108, 92, 231, 0.05) 0%, rgba(0, 217, 255, 0.05) 100%);
  z-index: 1;
}

.card-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  position: relative;
  z-index: 2;
  transition: transform var(--transition-base);
}

.document-card:hover .card-thumbnail img {
  transform: scale(1.05);
}

.card-thumbnail-placeholder {
  width: 100%;
  height: 200px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-light);
  position: relative;
  overflow: hidden;
}

.card-thumbnail-placeholder::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(108, 92, 231, 0.05) 0%, rgba(0, 217, 255, 0.05) 100%);
  z-index: 1;
}

.card-thumbnail-placeholder svg {
  position: relative;
  z-index: 2;
  opacity: 0.4;
  transition: all var(--transition-base);
}

.document-card:hover .card-thumbnail-placeholder svg {
  opacity: 0.6;
  transform: scale(1.1);
}

.card-content {
  padding: var(--space-md);
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-sm);
}

.card-content h3 {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
  color: var(--text-dark);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.doc-type-badge {
  padding: 0.25rem 0.5rem;
  color: white;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  white-space: nowrap;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
}

/* PDF - Red */
.doc-type-badge.type-pdf {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
}

/* Word (DOCX) - Blue */
.doc-type-badge.type-docx {
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
}

/* Excel (XLSX) - Green */
.doc-type-badge.type-xlsx {
  background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
}

/* PowerPoint (PPTX) - Orange */
.doc-type-badge.type-pptx {
  background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%);
}

/* CSV/TXT - Gray */
.doc-type-badge.type-csv,
.doc-type-badge.type-txt {
  background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
}

/* Images - Purple */
.doc-type-badge.type-image {
  background: linear-gradient(135deg, #9333ea 0%, #7e22ce 100%);
}

/* Default - Primary gradient */
.doc-type-badge.type-default {
  background: var(--gradient-primary);
}

/* Small badge variant - base styles */
.doc-type-badge-small {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: white;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  margin-right: 0.5rem;
  margin-left: 0;
  white-space: nowrap;
  flex-shrink: 0;
}

/* Small badge variant - same colors */
.doc-type-badge-small.type-pdf {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
}

.doc-type-badge-small.type-docx {
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
}

.doc-type-badge-small.type-xlsx {
  background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
}

.doc-type-badge-small.type-pptx {
  background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%);
}

.doc-type-badge-small.type-csv,
.doc-type-badge-small.type-txt {
  background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
}

.doc-type-badge-small.type-image {
  background: linear-gradient(135deg, #9333ea 0%, #7e22ce 100%);
}

.doc-type-badge-small.type-default {
  background: var(--gradient-primary);
}

.card-meta {
  display: flex;
  gap: var(--space-sm);
  align-items: center;
  flex-wrap: wrap;
  font-size: 0.75rem;
  color: var(--text-medium);
  margin-bottom: var(--space-sm);
}

.card-folder {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: 0.75rem;
  color: var(--text-medium);
  margin-bottom: var(--space-sm);
}

.card-tags {
  display: flex;
  gap: var(--space-xs);
  flex-wrap: wrap;
  align-items: center;
}

.tag-small {
  padding: 0.25rem 0.625rem;
  background: linear-gradient(135deg, var(--primary-light) 0%, rgba(108, 92, 231, 0.1) 100%);
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--primary-dark);
  border: 1px solid rgba(108, 92, 231, 0.2);
  transition: all var(--transition-base);
}

.tag-small:hover {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  color: white;
  border-color: var(--primary);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.tag-more-wrapper {
  position: relative;
  display: inline-block;
}

.tag-more {
  padding: 0.25rem 0.625rem;
  background: var(--bg-light);
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-medium);
  border: 1px solid #e5e7eb;
  cursor: pointer;
  transition: all var(--transition-base);
}

.tag-more:hover {
  background: var(--primary-light);
  color: var(--primary-dark);
  border-color: var(--primary);
}

.tag-tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: var(--space-xs);
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: all var(--transition-base);
  z-index: var(--z-tooltip);
}

.tag-more-wrapper:hover .tag-tooltip {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
  transform: translateX(-50%) translateY(-4px);
}

.tag-tooltip-content {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-md);
  box-shadow: var(--shadow-lg), var(--shadow-glow);
  border: 1px solid rgba(108, 92, 231, 0.2);
  min-width: 200px;
  max-width: 300px;
}

.tag-tooltip-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-medium);
  margin-bottom: var(--space-sm);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.tag-tooltip-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.tag-tooltip-item {
  padding: 0.25rem 0.5rem;
  background: linear-gradient(135deg, var(--primary-light) 0%, rgba(108, 92, 231, 0.1) 100%);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--primary-dark);
  border: 1px solid rgba(108, 92, 231, 0.2);
}

.tag-tooltip::before {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 6px solid var(--bg-white);
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.card-actions {
  padding: var(--space-md);
  border-top: 1px solid var(--border-color);
  display: flex;
  gap: var(--space-md);
  justify-content: flex-end;
}

.documents-table {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-xl);
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
  border-top: 1px solid var(--border-color);
}

.table-row {
  cursor: pointer;
  transition: background var(--transition-base);
}

.table-row:hover {
  background: var(--bg-light);
}

.table-title {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-weight: 500;
  color: var(--text-dark);
}

.table-title-content {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  flex-wrap: wrap;
}

.table-title-text {
  flex: 1;
  min-width: 0;
}

.table-actions {
  display: flex;
  gap: var(--space-xs);
}

.table-actions .btn-link-small {
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--primary);
  padding: var(--space-xs) var(--space-sm);
  font-size: 0.875rem;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  border-radius: var(--radius-sm);
  transition: all var(--transition-base);
  text-decoration: none;
}

.table-actions .btn-link-small:hover {
  background: var(--primary-light);
  color: var(--primary-dark);
  transform: translateY(-1px);
}

.table-actions .btn-link-small:active {
  transform: translateY(0);
}

.card-actions .btn-link-small {
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--primary);
  padding: var(--space-xs) var(--space-sm);
  font-size: 0.875rem;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  border-radius: var(--radius-sm);
  transition: all var(--transition-base);
  text-decoration: none;
}

.card-actions .btn-link-small:hover {
  background: var(--primary-light);
  color: var(--primary-dark);
  transform: translateY(-1px);
}

.card-actions .btn-link-small:active {
  transform: translateY(0);
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

.empty-state {
  text-align: center;
  padding: var(--space-3xl);
  color: var(--text-medium);
}

.empty-state svg {
  margin-bottom: var(--space-lg);
  opacity: 0.5;
}

.empty-state p {
  font-size: 1.125rem;
  margin-bottom: var(--space-lg);
}

.loading {
  text-align: center;
  padding: var(--space-3xl);
  color: var(--text-medium);
}
</style>

