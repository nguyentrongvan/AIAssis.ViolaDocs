<template>
  <div class="recycle-bin-page">
    <div class="page-header">
      <h1>{{ $t('recycleBin.title') }}</h1>
    </div>

    <!-- Filters -->
    <div class="filters-bar">
      <div class="filter-group">
        <label>{{ $t('common.search') }}</label>
        <input
          v-model="filters.search"
          @keyup.enter="loadDocuments"
          :placeholder="$t('recycleBin.title')"
          class="search-input"
        />
      </div>
      <button @click="loadDocuments" class="btn-secondary">
        <Search :size="16" />
        {{ $t('common.filter') }}
      </button>
      <button @click="clearFilters" class="btn-clear">
        <X :size="16" />
        {{ $t('common.clear') }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading">{{ $t('common.loading') }}</div>

    <!-- Documents Table -->
    <div v-else-if="documents.length > 0" class="documents-content">
      <div class="documents-table">
        <table>
          <thead>
            <tr>
              <th>{{ $t('common.title') }}</th>
              <th>{{ $t('common.status') }}</th>
              <th>{{ $t('common.size') }}</th>
              <th>{{ $t('common.folder') }}</th>
              <th>{{ $t('recycleBin.deletedBy') }}</th>
              <th>{{ $t('recycleBin.deletedAt') }}</th>
              <th>{{ $t('recycleBin.purgeAt') }}</th>
              <th>{{ $t('recycleBin.daysUntilPurge') }}</th>
              <th>{{ $t('common.actions') }}</th>
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
                    <span class="table-title-text">{{ doc.title || $t('documents.untitledDocument') }}</span>
                  </div>
                </div>
              </td>
              <td><StatusBadge :status="doc.status" /></td>
              <td>{{ formatSize(doc.size) }}</td>
              <td>{{ doc.folder?.name || $t('common.na') }}</td>
              <td>{{ doc.deleted_by?.name || $t('common.unknown') }}</td>
              <td>{{ formatDate(doc.deleted_at) }}</td>
              <td>
                <span v-if="doc.purge_at" :class="['purge-date', { 'purge-date-warning': doc.days_until_purge !== null && doc.days_until_purge <= 1 }]">
                  {{ formatDate(doc.purge_at) }}
                </span>
                <span v-else class="purge-date-na">{{ $t('common.na') }}</span>
              </td>
              <td>
                <span :class="['days-badge', { 'days-warning': doc.days_until_purge !== null && doc.days_until_purge <= 1 }]">
                  {{ doc.days_until_purge !== null ? `${doc.days_until_purge} ${$t('upload.days')}` : $t('common.na') }}
                </span>
              </td>
              <td>
                <div class="table-actions" @click.stop>
                  <button
                    @click="restoreDocument(doc)"
                    class="btn-link-small"
                  >
                    {{ $t('recycleBin.restore') }}
                  </button>
                  <button
                    v-if="isAdmin"
                    @click="confirmPermanentDelete(doc)"
                    class="btn-link-small btn-danger"
                  >
                    {{ $t('recycleBin.permanentDelete') }}
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
      <p>{{ $t('recycleBin.noItems') }}</p>
    </div>

    <!-- Restore Confirmation Modal -->
    <Modal
      :show="showRestoreModal"
      :title="$t('recycleBin.restore') + ' ' + $t('documents.title')"
      @update:show="showRestoreModal = $event"
    >
      <p v-if="documentToRestore">
        {{ $t('recycleBin.restoreConfirm') }} "{{ documentToRestore.title }}"?
      </p>
      <template #footer>
        <button @click="showRestoreModal = false" class="btn-secondary">{{ $t('common.cancel') }}</button>
        <button @click="restoreDocumentConfirm" class="btn-primary">{{ $t('recycleBin.restore') }}</button>
      </template>
    </Modal>

    <!-- Permanent Delete Confirmation Modal -->
    <Modal
      :show="showPermanentDeleteModal"
      :title="$t('recycleBin.permanentDelete')"
      @update:show="showPermanentDeleteModal = $event"
    >
      <p v-if="documentToDelete">
        {{ $t('recycleBin.permanentDeleteConfirm') }} "{{ documentToDelete.title }}"? 
        {{ $t('recycleBin.permanentDeleteWarning') }}
      </p>
      <template #footer>
        <button @click="showPermanentDeleteModal = false" class="btn-secondary">{{ $t('common.cancel') }}</button>
        <button @click="deletePermanently" class="btn-danger">{{ $t('recycleBin.permanentDelete') }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../store/auth'
import { recycleBinAPI } from '../services/api'
import { StatusBadge, Pagination, Modal } from '../components'

const { t } = useI18n()
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
  if (!dateString) return t('common.na')
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
      window.$toast.show(t('recycleBin.failedToLoadDeletedDocuments'), 'error')
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
        window.$toast.show(t('recycleBin.documentRestored'), 'success')
      }
      showRestoreModal.value = false
      documentToRestore.value = null
      await loadDocuments()
    } else {
      if (window.$toast) {
        window.$toast.show(res.message || t('recycleBin.failedToRestoreDocument'), 'error')
      }
    }
  } catch (e) {
    console.error('Failed to restore document', e)
    if (window.$toast) {
      window.$toast.show(t('recycleBin.failedToRestoreDocument'), 'error')
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
        window.$toast.show(t('recycleBin.documentPermanentlyDeleted'), 'success')
      }
      showPermanentDeleteModal.value = false
      documentToDelete.value = null
      await loadDocuments()
    } else {
      if (window.$toast) {
        window.$toast.show(res.message || t('recycleBin.failedToPermanentlyDeleteDocument'), 'error')
      }
    }
  } catch (e) {
    console.error('Failed to permanently delete document', e)
    if (window.$toast) {
      window.$toast.show(t('recycleBin.failedToPermanentlyDeleteDocument'), 'error')
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
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.02em;
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
  vertical-align: middle;
}

.documents-table td {
  padding: var(--space-md);
  border-top: 1px solid #e5e7eb;
  vertical-align: middle;
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
  align-items: center;
  gap: var(--space-xs);
  flex-wrap: wrap;
}

.table-title-text {
  font-weight: 500;
  color: var(--text-dark);
  flex: 1;
  min-width: 0;
}

.doc-type-badge-small {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  color: white;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-right: 0.5rem;
  margin-left: 0;
  flex-shrink: 0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

/* PDF - Red */
.doc-type-badge-small.type-pdf {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
}

/* Word (DOCX) - Blue */
.doc-type-badge-small.type-docx {
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
}

/* Excel (XLSX) - Green */
.doc-type-badge-small.type-xlsx {
  background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
}

/* PowerPoint (PPTX) - Orange */
.doc-type-badge-small.type-pptx {
  background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%);
}

/* CSV/TXT - Gray */
.doc-type-badge-small.type-csv,
.doc-type-badge-small.type-txt {
  background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
}

/* Images - Purple */
.doc-type-badge-small.type-image {
  background: linear-gradient(135deg, #9333ea 0%, #7e22ce 100%);
}

/* Default - Primary gradient */
.doc-type-badge-small.type-default {
  background: var(--gradient-primary);
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

.purge-date {
  font-size: 0.875rem;
  color: var(--text-medium);
  font-weight: 500;
}

.purge-date.purge-date-warning {
  color: var(--warn);
  font-weight: 600;
}

.purge-date-na {
  font-size: 0.875rem;
  color: var(--text-light);
  font-style: italic;
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

