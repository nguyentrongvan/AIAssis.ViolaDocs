<template>
  <div class="search-page">
    <h1 class="page-header">Search Documents</h1>

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
              placeholder="Search documents..."
              class="search-input"
            />
            <button @click="doSearch" class="btn-primary search-btn">
              <Search :size="18" />
              Search
            </button>
          </div>
          <div class="search-mode">
            <label>
              <input type="radio" v-model="mode" value="keyword" />
              Keyword
            </label>
            <label>
              <input type="radio" v-model="mode" value="vector" />
              Semantic
            </label>
            <label>
              <input type="radio" v-model="mode" value="hybrid" />
              Hybrid
            </label>
          </div>
        </div>

        <div v-if="selectedCount > 0" class="bulk-actions-bar">
          <span>{{ selectedCount }} selected</span>
          <div class="bulk-actions">
            <button @click="bulkShare" class="btn-small">
              <Share2 :size="16" />
              Share
            </button>
            <button @click="bulkMove" class="btn-small">
              <Folder :size="16" />
              Move
            </button>
            <button @click="bulkDelete" class="btn-small btn-danger">
              <Trash2 :size="16" />
              Delete
            </button>
            <button @click="clearSelection" class="btn-small">
              Clear
            </button>
          </div>
        </div>

        <div v-if="loading" class="loading">Searching...</div>
        <div v-else-if="results.length > 0" class="results">
          <div class="results-header">
            <span>{{ totalResults }} results found</span>
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
                  <span>{{ doc.owner?.name || 'Unknown' }}</span>
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
                  <StatusBadge :status="doc.status" />
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
                  <th>Title</th>
                  <th>Owner</th>
                  <th>Folder</th>
                  <th>Tags</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Actions</th>
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
                  <td>{{ doc.owner?.name || 'Unknown' }}</td>
                  <td>{{ doc.folder?.name || '-' }}</td>
                  <td>
                    <div class="tags">
                      <span v-for="tag in doc.tags" :key="tag" class="tag-small">{{ tag }}</span>
                    </div>
                  </td>
                  <td><StatusBadge :status="doc.status" /></td>
                  <td>{{ formatDate(doc.created_at) }}</td>
                  <td>
                    <button
                      @click.stop="$router.push(`/documents/${doc.id}`)"
                      class="btn-link-small"
                    >
                      View
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
          No documents found
        </div>
      </div>

      <!-- Filters Sidebar -->
      <div class="filters-sidebar">
        <div class="filters-header">
          <h3>Filters</h3>
          <button @click="clearFilters" class="btn-link-small">Clear All</button>
        </div>

        <div class="filter-section">
          <div class="filter-label">Type</div>
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
          <div class="filter-label">Status</div>
          <div class="filter-options">
            <label v-for="status in statuses" :key="status" class="checkbox-label">
              <input
                type="checkbox"
                :value="status"
                v-model="filters.statuses"
              />
              <span>{{ status }}</span>
            </label>
          </div>
        </div>

        <div class="filter-section">
          <div class="filter-label">Folder</div>
          <select v-model.number="filters.folder_id">
            <option :value="null">All Folders</option>
            <option v-for="f in folders" :key="f.id" :value="f.id">
              {{ f.name }}
            </option>
          </select>
        </div>

        <div class="filter-section">
          <div class="filter-label">Owner</div>
          <select v-model.number="filters.owner_id">
            <option :value="null">All Owners</option>
            <option v-for="u in users" :key="u.id" :value="u.id">
              {{ u.name }}
            </option>
          </select>
        </div>

        <div class="filter-section">
          <div class="filter-label">Tags</div>
          <input
            v-model="tagFilter"
            @keyup.enter="addTagFilter"
            placeholder="Press Enter to add"
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
          <div class="filter-label">Date Range</div>
          <input
            v-model="filters.date_from"
            type="date"
            placeholder="From"
          />
          <input
            v-model="filters.date_to"
            type="date"
            placeholder="To"
            style="margin-top: 0.5rem;"
          />
        </div>

        <div class="filter-section">
          <div class="filter-label">Retention Policy</div>
          <select v-model.number="filters.retention_policy_id">
            <option :value="null">All</option>
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
          Apply Filters
        </button>
      </div>
    </div>

    <!-- Bulk Move Modal -->
    <Modal v-model:show="showMoveModal" title="Move Documents">
      <FolderTree
        :folders="folderTree"
        @select="selectMoveFolder"
      />
      <template #footer>
        <button @click="showMoveModal = false" class="btn-secondary">Cancel</button>
        <button @click="confirmMove" class="btn-primary" :disabled="!moveFolderId">
          Move
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useFoldersStore } from '../store/folders'
import { useSettingsStore } from '../store/settings'
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
  await loadFolders()
  await loadUsers()
  await loadRetentionPolicies()
})

const loadFolders = async () => {
  try {
    await foldersStore.fetchFolders()
    folders.value = foldersStore.folders
  } catch (e) {
    console.error('Failed to load folders', e)
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

const loadRetentionPolicies = async () => {
  try {
    await settingsStore.fetchRetentionPolicies()
    retentionPolicies.value = settingsStore.retentionPolicies
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
    if (res.is_success) {
      results.value = res.data.results || res.data.items || []
      totalResults.value = res.data.total || results.value.length
      totalPages.value = res.data.pages || Math.ceil(totalResults.value / 20)
    }
  } catch (e) {
    console.error('Search failed', e)
    if (window.$toast) {
      window.$toast.show('Search failed', 'error')
    }
  } finally {
    loading.value = false
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
    window.$toast.show('Bulk share not yet implemented', 'info')
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
    if (window.$toast) {
      window.$toast.show(`${docIds.length} documents moved`, 'success')
    }
    selectedDocs.value.clear()
    showMoveModal.value = false
    moveFolderId.value = null
    doSearch()
  } catch (e) {
    console.error('Failed to move documents', e)
    if (window.$toast) {
      window.$toast.show('Failed to move documents', 'error')
    }
  }
}

const bulkDelete = async () => {
  const docIds = Array.from(selectedDocs.value)
  if (docIds.length === 0) return
  if (!confirm(`Delete ${docIds.length} documents?`)) return
  try {
    for (const docId of docIds) {
      await documentsAPI.delete(docId)
    }
    if (window.$toast) {
      window.$toast.show(`${docIds.length} documents deleted`, 'success')
    }
    selectedDocs.value.clear()
    doSearch()
  } catch (e) {
    console.error('Failed to delete documents', e)
    if (window.$toast) {
      window.$toast.show('Failed to delete documents', 'error')
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
  background: var(--primary-light);
  color: var(--primary);
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
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
  background: var(--primary-light);
  color: var(--primary);
  padding: 0.125rem 0.5rem;
  border-radius: 8px;
  font-size: 0.75rem;
  margin-right: 0.25rem;
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
  background: var(--primary-light);
  color: var(--primary);
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
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
