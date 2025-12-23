<template>
  <div class="search-page">
    <h1 class="page-header">{{ $t('search.title') }}</h1>

    <div class="search-container">
      <div class="search-main">
        <div class="search-bar glass">
          <div class="search-input-group">
            <div class="search-icon-wrapper">
              <Search :size="24" class="search-icon" />
            </div>
            <input
              v-model="query"
              @keyup.enter="doSearch"
              @focus="onSearchFocus"
              @blur="onSearchBlur"
              :placeholder="$t('search.searchPlaceholder')"
              class="search-input"
            />
            <button @click="doSearch" class="btn-primary search-btn">
              <Search :size="18" />
              {{ $t('common.search') }}
            </button>
          </div>
          <div class="search-mode">
            <label>
              <input type="radio" v-model="mode" value="keyword" />
              {{ $t('search.keyword') }}
            </label>
            <label>
              <input type="radio" v-model="mode" value="vector" />
              {{ $t('search.semantic') }}
            </label>
            <label>
              <input type="radio" v-model="mode" value="hybrid" />
              {{ $t('search.hybrid') }}
            </label>
          </div>
        </div>

        <div v-if="selectedCount > 0" class="bulk-actions-bar">
          <span>{{ selectedCount }} {{ $t('search.selected') }}</span>
          <div class="bulk-actions">
            <button @click="bulkShare" class="btn-small">
              <Share2 :size="16" />
              {{ $t('common.share') }}
            </button>
            <button @click="bulkMove" class="btn-small">
              <Folder :size="16" />
              {{ $t('common.move') }}
            </button>
            <button @click="bulkDelete" class="btn-small btn-danger">
              <Trash2 :size="16" />
              {{ $t('common.delete') }}
            </button>
            <button @click="clearSelection" class="btn-small">
              {{ $t('common.clear') }}
            </button>
          </div>
        </div>

        <div v-if="loading" class="loading">{{ $t('search.searching') }}</div>
        <div v-else-if="results.length > 0" class="results">
          <div class="results-header">
            <span>{{ $t('search.resultsFound', { count: totalResults }) }}</span>
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
          </div>

          <!-- Card View -->
          <div v-if="viewMode === 'cards'" class="results-grid">
            <div
              v-for="doc in results"
              :key="doc.id"
              class="result-card"
              :class="{ selected: selectedDocs.has(doc.id) }"
              @click="toggleSelect(doc.id)"
            >
              <div class="card-checkbox">
                <input
                  type="checkbox"
                  :checked="selectedDocs.has(doc.id)"
                  @click.stop="toggleSelect(doc.id)"
                />
              </div>
              <div class="card-content" @click.stop="$router.push(`/documents/${doc.id}`)">
                <h3>{{ doc.title }}</h3>
                <p class="meta">
                  <span>{{ doc.owner?.name || $t('common.unknown') }}</span>
                  <span>•</span>
                  <span>{{ formatDate(doc.created_at) }}</span>
                  <span v-if="doc.folder">•</span>
                  <span v-if="doc.folder">{{ doc.folder.name }}</span>
                </p>
                <p v-if="doc.snippet" class="snippet" v-html="doc.snippet"></p>
                <div class="card-footer">
                  <div class="tags">
                    <span v-for="tag in doc.tags" :key="tag" class="tag">{{ tag }}</span>
                  </div>
                  <StatusBadge :status="doc.status || 'unknown'" />
                </div>
              </div>
            </div>
          </div>

          <!-- Table View -->
          <div v-else class="results-table">
            <table>
              <thead>
                <tr>
                  <th>
                    <input
                      type="checkbox"
                      :checked="allSelected"
                      @change="toggleSelectAll"
                    />
                  </th>
                  <th>{{ $t('search.tableTitle') }}</th>
                  <th>{{ $t('search.tableOwner') }}</th>
                  <th>{{ $t('search.tableFolder') }}</th>
                  <th>{{ $t('search.tableTags') }}</th>
                  <th>{{ $t('search.tableStatus') }}</th>
                  <th>{{ $t('search.tableCreated') }}</th>
                  <th>{{ $t('search.tableActions') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="doc in results"
                  :key="doc.id"
                  :class="{ selected: selectedDocs.has(doc.id) }"
                  @click="toggleSelect(doc.id)"
                >
                  <td>
                    <input
                      type="checkbox"
                      :checked="selectedDocs.has(doc.id)"
                      @click.stop="toggleSelect(doc.id)"
                    />
                  </td>
                  <td>
                    <a @click.stop="$router.push(`/documents/${doc.id}`)" class="doc-link">
                      {{ doc.title }}
                    </a>
                  </td>
                  <td>{{ doc.owner?.name || $t('common.unknown') }}</td>
                  <td>{{ doc.folder?.name || $t('common.na') }}</td>
                  <td>
                    <div class="tags">
                      <span v-for="tag in doc.tags" :key="tag" class="tag-small">{{ tag }}</span>
                    </div>
                  </td>
                  <td><StatusBadge :status="doc.status || 'unknown'" /></td>
                  <td>{{ formatDate(doc.created_at) }}</td>
                  <td>
                    <button
                      @click.stop="$router.push(`/documents/${doc.id}`)"
                      class="btn-link-small"
                    >
                      {{ $t('search.view') }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <Pagination
            v-model:page="currentPage"
            :total-pages="totalPages"
            @change="doSearch"
          />
        </div>
        <div v-else-if="searched" class="no-results">
          {{ $t('search.noDocumentsFound') }}
        </div>
      </div>

      <!-- Filters Sidebar -->
      <div class="filters-sidebar">
        <div class="filters-header">
          <h3>{{ $t('search.filters') }}</h3>
          <button @click="clearFilters" class="btn-link-small">{{ $t('search.clearAll') }}</button>
        </div>

        <div class="filter-section">
          <div class="filter-label">{{ $t('search.filterType') }}</div>
          <div class="filter-options">
            <label v-for="type in fileTypes" :key="type.value" class="checkbox-label">
              <input
                type="checkbox"
                :value="type.value"
                v-model="filters.types"
              />
              <span>{{ type.label }}</span>
            </label>
          </div>
        </div>

        <div class="filter-section">
          <div class="filter-label">{{ $t('search.filterStatus') }}</div>
          <div class="filter-options">
            <label v-for="status in statuses" :key="status" class="checkbox-label">
              <input
                type="checkbox"
                :value="status"
                v-model="filters.statuses"
              />
              <span>{{ $t(`status.${status}`) }}</span>
            </label>
          </div>
        </div>

        <div class="filter-section">
          <div class="filter-label">{{ $t('search.filterFolder') }}</div>
          <select v-model.number="filters.folder_id">
            <option :value="null">{{ $t('search.allFolders') }}</option>
            <option v-for="f in folders" :key="f.id" :value="f.id">
              {{ f.name }}
            </option>
          </select>
        </div>

        <div class="filter-section">
          <div class="filter-label">{{ $t('search.filterOwner') }}</div>
          <select v-model.number="filters.owner_id">
            <option :value="null">{{ $t('search.allOwners') }}</option>
            <option v-for="u in users" :key="u.id" :value="u.id">
              {{ u.name }}
            </option>
          </select>
        </div>

        <div class="filter-section">
          <div class="filter-label">{{ $t('search.filterTags') }}</div>
          <input
            v-model="tagFilter"
            @keyup.enter="addTagFilter"
            :placeholder="$t('search.pressEnterToAdd')"
          />
          <div class="selected-tags">
            <span
              v-for="tag in filters.tags"
              :key="tag"
              class="tag-badge"
            >
              {{ tag }}
              <button @click="removeTagFilter(tag)" class="tag-remove">×</button>
            </span>
          </div>
        </div>

        <div class="filter-section">
          <div class="filter-label">{{ $t('search.dateRange') }}</div>
          <input
            v-model="filters.date_from"
            type="date"
            :placeholder="$t('search.from')"
          />
          <input
            v-model="filters.date_to"
            type="date"
            :placeholder="$t('search.to')"
            style="margin-top: 0.5rem;"
          />
        </div>

        <div class="filter-section">
          <div class="filter-label">{{ $t('search.retentionPolicy') }}</div>
          <select v-model.number="filters.retention_policy_id">
            <option :value="null">{{ $t('common.all') }}</option>
            <option
              v-for="p in retentionPolicies"
              :key="p.id"
              :value="p.id"
            >
              {{ p.name }}
            </option>
          </select>
        </div>

        <button @click="applyFilters" class="btn-primary" style="width: 100%; margin-top: 1rem;">
          {{ $t('search.applyFilters') }}
        </button>
      </div>
    </div>

    <!-- Bulk Move Modal -->
    <Modal v-model:show="showMoveModal" :title="$t('search.moveDocuments')">
      <FolderTree
        :folders="folderTree"
        @select="selectMoveFolder"
      />
      <template #footer>
        <button @click="showMoveModal = false" class="btn-secondary">{{ $t('common.cancel') }}</button>
        <button @click="confirmMove" class="btn-primary" :disabled="!moveFolderId">
          {{ $t('search.move') }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useFoldersStore } from '../store/folders'
import { useSettingsStore } from '../store/settings'

const { t } = useI18n()
import { searchAPI, documentsAPI, usersAPI } from '../services/api'
import { StatusBadge, Pagination, Modal, FolderTree } from '../components'
import {
  Search,
  Share2,
  Folder,
  Trash2,
  Grid,
  List
} from 'lucide-vue-next'

const router = useRouter()
const foldersStore = useFoldersStore()
const settingsStore = useSettingsStore()

const query = ref('')
const mode = ref('hybrid')
const results = ref([])
const searched = ref(false)
const loading = ref(false)
const viewMode = ref('cards')
const selectedDocs = ref(new Set())
const currentPage = ref(1)
const totalResults = ref(0)
const totalPages = ref(1)
const showMoveModal = ref(false)
const moveFolderId = ref(null)
const tagFilter = ref('')

const folders = ref([])
const users = ref([])
const retentionPolicies = ref([])
const isMounted = ref(true)

const filters = ref({
  types: [],
  statuses: [],
  folder_id: null,
  owner_id: null,
  tags: [],
  date_from: null,
  date_to: null,
  retention_policy_id: null
})

const fileTypes = [
  { value: 'application/pdf', label: 'PDF' },
  { value: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', label: 'DOCX' },
  { value: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', label: 'XLSX' },
  { value: 'image/', label: 'Images' }
]

const statuses = ['ready', 'processing', 'failed', 'queued']

const selectedCount = computed(() => selectedDocs.value.size)

const allSelected = computed(() => {
  return results.value.length > 0 && results.value.every(doc => selectedDocs.value.has(doc.id))
})

const folderTree = computed(() => foldersStore.folderTree)

const onSearchFocus = () => {
  // Add focus animation if needed
}

const onSearchBlur = () => {
  // Add blur animation if needed
}

onMounted(async () => {
  isMounted.value = true
  await loadFolders()
  await loadUsers()
  await loadRetentionPolicies()
})

onBeforeUnmount(() => {
  isMounted.value = false
})

const loadFolders = async () => {
  try {
    await foldersStore.fetchFolders()
    if (isMounted.value) {
      folders.value = foldersStore.folders
    }
  } catch (e) {
    console.error('Failed to load folders', e)
  }
}

const loadUsers = async () => {
  try {
    const res = await usersAPI.list()
    if (res.is_success && isMounted.value) {
      users.value = res.data || []
    }
  } catch (e) {
    console.error('Failed to load users', e)
  }
}

const loadRetentionPolicies = async () => {
  try {
    await settingsStore.fetchRetentionPolicies()
    if (isMounted.value) {
      retentionPolicies.value = settingsStore.retentionPolicies
    }
  } catch (e) {
    console.error('Failed to load retention policies', e)
  }
}

const doSearch = async () => {
  if (!query.value.trim() && !hasActiveFilters()) return
  loading.value = true
  searched.value = true
  try {
    const searchData = {
      query: query.value || '',
      mode: mode.value,
      page: currentPage.value,
      limit: 20
    }

    // Add filters
    if (filters.value.types.length > 0) {
      searchData.filters = { ...searchData.filters, type: filters.value.types }
    }
    if (filters.value.statuses.length > 0) {
      searchData.filters = { ...searchData.filters, status: filters.value.statuses }
    }
    if (filters.value.folder_id) {
      searchData.filters = { ...searchData.filters, folder_id: filters.value.folder_id }
    }
    if (filters.value.owner_id) {
      searchData.filters = { ...searchData.filters, owner_id: filters.value.owner_id }
    }
    if (filters.value.tags.length > 0) {
      searchData.filters = { ...searchData.filters, tags: filters.value.tags }
    }
    if (filters.value.date_from) {
      searchData.filters = { ...searchData.filters, date_from: filters.value.date_from }
    }
    if (filters.value.date_to) {
      searchData.filters = { ...searchData.filters, date_to: filters.value.date_to }
    }
    if (filters.value.retention_policy_id) {
      searchData.filters = { ...searchData.filters, retention_policy_id: filters.value.retention_policy_id }
    }

    const res = await searchAPI.search(searchData)
    if (res.is_success && isMounted.value) {
      results.value = res.data.results || res.data.items || []
      totalResults.value = res.data.total || results.value.length
      totalPages.value = res.data.pages || Math.ceil(totalResults.value / 20)
    }
  } catch (e) {
    console.error('Search failed', e)
    if (window.$toast && isMounted.value) {
      window.$toast.show(t('search.searchFailed'), 'error')
    }
  } finally {
    if (isMounted.value) {
      loading.value = false
    }
  }
}

const hasActiveFilters = () => {
  return filters.value.types.length > 0 ||
    filters.value.statuses.length > 0 ||
    filters.value.folder_id ||
    filters.value.owner_id ||
    filters.value.tags.length > 0 ||
    filters.value.date_from ||
    filters.value.date_to ||
    filters.value.retention_policy_id
}

const applyFilters = () => {
  currentPage.value = 1
  doSearch()
}

const clearFilters = () => {
  filters.value = {
    types: [],
    statuses: [],
    folder_id: null,
    owner_id: null,
    tags: [],
    date_from: null,
    date_to: null,
    retention_policy_id: null
  }
  tagFilter.value = ''
  applyFilters()
}

const addTagFilter = () => {
  if (tagFilter.value.trim() && !filters.value.tags.includes(tagFilter.value.trim())) {
    filters.value.tags.push(tagFilter.value.trim())
    tagFilter.value = ''
  }
}

const removeTagFilter = (tag) => {
  filters.value.tags = filters.value.tags.filter(t => t !== tag)
}

const toggleSelect = (docId) => {
  if (selectedDocs.value.has(docId)) {
    selectedDocs.value.delete(docId)
  } else {
    selectedDocs.value.add(docId)
  }
}

const toggleSelectAll = () => {
  if (allSelected.value) {
    selectedDocs.value.clear()
  } else {
    results.value.forEach(doc => selectedDocs.value.add(doc.id))
  }
}

const clearSelection = () => {
  selectedDocs.value.clear()
}

const bulkShare = async () => {
  const docIds = Array.from(selectedDocs.value)
  if (docIds.length === 0) return
  // Implementation for bulk share
  if (window.$toast) {
    window.$toast.show(t('search.bulkShareNotImplemented'), 'info')
  }
}

const bulkMove = () => {
  if (selectedDocs.value.size === 0) return
  showMoveModal.value = true
}

const selectMoveFolder = (folder) => {
  moveFolderId.value = folder.id
}

const confirmMove = async () => {
  const docIds = Array.from(selectedDocs.value)
  if (docIds.length === 0 || !moveFolderId.value) return
  try {
    for (const docId of docIds) {
      await documentsAPI.update(docId, { folder_id: moveFolderId.value })
    }
    if (window.$toast && isMounted.value) {
      window.$toast.show(t('search.documentsMoved', { count: docIds.length }), 'success')
    }
    if (isMounted.value) {
      selectedDocs.value.clear()
      showMoveModal.value = false
      moveFolderId.value = null
      doSearch()
    }
  } catch (e) {
    console.error('Failed to move documents', e)
    if (window.$toast && isMounted.value) {
      window.$toast.show(t('search.failedToMoveDocuments'), 'error')
    }
  }
}

const bulkDelete = async () => {
  const docIds = Array.from(selectedDocs.value)
  if (docIds.length === 0) return
  if (!confirm(t('search.deleteDocumentsConfirm', { count: docIds.length }))) return
  try {
    for (const docId of docIds) {
      await documentsAPI.delete(docId)
    }
    if (window.$toast && isMounted.value) {
      window.$toast.show(t('search.documentsDeleted', { count: docIds.length }), 'success')
    }
    if (isMounted.value) {
      selectedDocs.value.clear()
      doSearch()
    }
  } catch (e) {
    console.error('Failed to delete documents', e)
    if (window.$toast && isMounted.value) {
      window.$toast.show(t('search.failedToDeleteDocuments'), 'error')
    }
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString()
}
</script>

<style scoped>
.search-page {
  max-width: 1600px;
  margin: 0 auto;
}

.search-container {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 2rem;
}

.search-main {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.search-bar {
  padding: var(--space-xl);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  position: relative;
  overflow: hidden;
}

.search-bar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gradient-ai);
  z-index: 1;
}

.search-input-group {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
  position: relative;
}

.search-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-full);
  background: var(--gradient-cyan-purple);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-glow-cyan);
  transition: all var(--transition-base);
  flex-shrink: 0;
}

.search-icon {
  color: white;
  flex-shrink: 0;
  animation: float 3s var(--ease-in-out) infinite;
}

.search-input {
  flex: 1;
  padding: var(--space-lg);
  font-size: 1.1rem;
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-xl);
  background: var(--bg-white);
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.search-input:focus {
  outline: none;
  border-color: var(--ai-cyan);
  box-shadow: var(--shadow-md), 0 0 0 3px rgba(0, 217, 255, 0.1);
}

.search-btn {
  position: relative;
  overflow: hidden;
}

.search-mode {
  display: flex;
  gap: 1rem;
}

.search-mode label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.bulk-actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--primary-light);
  border-radius: var(--radius-md);
}

.bulk-actions {
  display: flex;
  gap: 0.5rem;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.view-options {
  display: flex;
  gap: 0.5rem;
}

.view-btn {
  padding: 0.5rem;
  background: white;
  border: 1px solid #ddd;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.view-btn.active {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-xl);
  animation: fadeIn var(--transition-base) var(--ease-out);
}

.result-card {
  background: var(--bg-white);
  padding: var(--space-xl);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  cursor: pointer;
  transition: all var(--transition-base);
  border: 2px solid transparent;
  position: relative;
  overflow: hidden;
  animation: fadeInUp var(--transition-base) var(--ease-out) both;
}

.result-card::before {
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

.result-card:hover::before {
  transform: scaleX(1);
}

.result-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: var(--shadow-2xl), var(--shadow-glow);
  border-color: var(--ai-cyan);
}

.result-card.selected {
  border-color: var(--primary);
  background: var(--gradient-ai-soft);
  box-shadow: var(--shadow-lg), var(--shadow-glow);
}

.result-card.selected::before {
  transform: scaleX(1);
}

.card-checkbox {
  position: absolute;
  top: 1rem;
  right: 1rem;
}

.card-content {
  padding-right: 2rem;
}

.result-card h3 {
  margin: 0 0 0.5rem 0;
  color: var(--primary);
}

.meta {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.snippet {
  color: #333;
  margin-bottom: 1rem;
  line-height: 1.6;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tags {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 0.4375rem 0.9375rem;
  background: linear-gradient(135deg, rgba(108, 92, 231, 0.12) 0%, rgba(108, 92, 231, 0.08) 100%);
  color: #6c5ce7;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
  border: 1.5px solid rgba(108, 92, 231, 0.25);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  white-space: nowrap;
  box-shadow: 0 1px 3px rgba(108, 92, 231, 0.15);
  letter-spacing: 0.01em;
}

.tag:hover {
  background: linear-gradient(135deg, #6c5ce7 0%, #5a4fcf 100%);
  color: white;
  border-color: #6c5ce7;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(108, 92, 231, 0.3), 0 2px 4px rgba(108, 92, 231, 0.2);
}

.results-table {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.results-table table {
  width: 100%;
  border-collapse: collapse;
}

.results-table th,
.results-table td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.results-table th {
  background: var(--bg-light);
  font-weight: 600;
  color: var(--primary);
}

.results-table tr:hover {
  background: var(--bg-light);
}

.results-table tr.selected {
  background: var(--primary-light);
}

.doc-link {
  color: var(--primary);
  cursor: pointer;
  text-decoration: none;
}

.doc-link:hover {
  text-decoration: underline;
}

.tag-small {
  display: inline-flex;
  align-items: center;
  padding: 0.375rem 0.875rem;
  background: linear-gradient(135deg, rgba(108, 92, 231, 0.12) 0%, rgba(108, 92, 231, 0.08) 100%);
  color: #6c5ce7;
  border-radius: 20px;
  font-size: 0.8125rem;
  font-weight: 600;
  border: 1.5px solid rgba(108, 92, 231, 0.25);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  white-space: nowrap;
  box-shadow: 0 1px 2px rgba(108, 92, 231, 0.1);
  letter-spacing: 0.01em;
  margin-right: 0.25rem;
}

.tag-small:hover {
  background: linear-gradient(135deg, #6c5ce7 0%, #5a4fcf 100%);
  color: white;
  border-color: #6c5ce7;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(108, 92, 231, 0.3), 0 2px 4px rgba(108, 92, 231, 0.2);
}

.btn-link-small {
  background: none;
  border: none;
  color: var(--primary);
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
}

.filters-sidebar {
  padding: var(--space-xl);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  height: fit-content;
  position: sticky;
  top: var(--space-xl);
  background: var(--bg-white);
}

.filters-sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gradient-ai);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
}

.filters-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.filters-header h3 {
  margin: 0;
  color: var(--primary);
}

.filter-section {
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #eee;
}

.filter-section:last-child {
  border-bottom: none;
}

.filter-label {
  display: block;
  margin-bottom: 0.75rem;
  font-weight: 600;
  color: #333;
  font-size: 0.9rem;
}

.filter-options {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: normal;
  cursor: pointer;
  color: #555;
  font-size: 0.9rem;
}

/* Checkbox styles moved to theme.css */

.checkbox-label span {
  line-height: 1.2;
}

.filter-section select,
.filter-section input[type="text"],
.filter-section input[type="date"] {
  width: 100%;
  padding: var(--space-md) var(--space-lg);
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-lg);
  background: var(--bg-white);
  font-size: 0.95rem;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.filter-section input[type="date"] {
  padding-right: var(--space-xl);
  cursor: pointer;
  position: relative;
}

.filter-section input[type="date"]::-webkit-calendar-picker-indicator {
  cursor: pointer;
  opacity: 0.6;
  filter: grayscale(1);
  transition: all var(--transition-base);
  padding: var(--space-xs);
  border-radius: var(--radius-sm);
}

.filter-section input[type="date"]::-webkit-calendar-picker-indicator:hover {
  opacity: 1;
  filter: grayscale(0);
  background: var(--gradient-ai-soft);
}

.filter-section select:focus,
.filter-section input[type="text"]:focus,
.filter-section input[type="date"]:focus {
  outline: none;
  border-color: var(--ai-cyan);
  box-shadow: var(--shadow-md), 0 0 0 3px rgba(0, 217, 255, 0.1);
}

.filter-section input[type="date"]:focus::-webkit-calendar-picker-indicator {
  opacity: 1;
  filter: grayscale(0);
}

.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.tag-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4375rem 0.9375rem;
  background: linear-gradient(135deg, rgba(108, 92, 231, 0.12) 0%, rgba(108, 92, 231, 0.08) 100%);
  color: #6c5ce7;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
  border: 1.5px solid rgba(108, 92, 231, 0.25);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  white-space: nowrap;
  box-shadow: 0 1px 3px rgba(108, 92, 231, 0.15);
  letter-spacing: 0.01em;
}

.tag-badge:hover {
  background: linear-gradient(135deg, #6c5ce7 0%, #5a4fcf 100%);
  color: white;
  border-color: #6c5ce7;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(108, 92, 231, 0.3), 0 2px 4px rgba(108, 92, 231, 0.2);
}

.tag-remove {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--primary);
  font-size: 1.2rem;
  line-height: 1;
  padding: 0;
}

.loading,
.no-results {
  text-align: center;
  padding: 3rem;
  color: #666;
}
</style>
