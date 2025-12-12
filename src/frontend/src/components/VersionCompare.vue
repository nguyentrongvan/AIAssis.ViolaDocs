<template>
  <Modal :show="show" @update:show="$emit('update:show', $event)" title="Version Comparison" :close-on-overlay="false">
    <div v-if="loading" class="loading">Loading comparison...</div>
    <div v-else-if="comparison" class="version-compare">
      <div class="compare-header">
        <div class="version-info">
          <h4>Version {{ v1 }}</h4>
          <span class="version-date">{{ formatDate(comparison.version1?.created_at) }}</span>
        </div>
        <div class="version-info">
          <h4>Version {{ v2 }}</h4>
          <span class="version-date">{{ formatDate(comparison.version2?.created_at) }}</span>
        </div>
      </div>

      <div class="compare-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="['tab-btn', { 'tab-btn-active': activeTab === tab.id }]"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="compare-content">
        <!-- Text Diff -->
        <div v-if="activeTab === 'text' && comparison.text_diff" class="diff-view">
          <div class="diff-content" v-html="formatDiff(comparison.text_diff)"></div>
        </div>

        <!-- Metadata Diff -->
        <div v-if="activeTab === 'metadata' && comparison.metadata_diff" class="metadata-diff">
          <div
            v-for="change in comparison.metadata_diff"
            :key="change.field"
            class="diff-item"
          >
            <div class="diff-field">{{ change.field }}</div>
            <div class="diff-values">
              <div class="diff-old">
                <span class="diff-label">Old:</span>
                <span>{{ change.old_value || '(empty)' }}</span>
              </div>
              <div class="diff-new">
                <span class="diff-label">New:</span>
                <span>{{ change.new_value || '(empty)' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- ACL Diff -->
        <div v-if="activeTab === 'acl' && comparison.acl_diff" class="acl-diff">
          <div class="diff-section">
            <h5>Added</h5>
            <div v-if="comparison.acl_diff.added?.length">
              <div
                v-for="item in comparison.acl_diff.added"
                :key="item.id"
                class="acl-item"
              >
                {{ item.name || item.email }}
              </div>
            </div>
            <div v-else class="no-changes">No additions</div>
          </div>
          <div class="diff-section">
            <h5>Removed</h5>
            <div v-if="comparison.acl_diff.removed?.length">
              <div
                v-for="item in comparison.acl_diff.removed"
                :key="item.id"
                class="acl-item"
              >
                {{ item.name || item.email }}
              </div>
            </div>
            <div v-else class="no-changes">No removals</div>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="error">Failed to load comparison</div>

    <template #footer>
      <button @click="$emit('close')" class="btn-secondary">Close</button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { documentsAPI } from '../services/api'
import { Modal } from './index'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  documentId: {
    type: Number,
    required: true
  },
  v1: {
    type: Number,
    required: true
  },
  v2: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['update:show', 'close'])

const loading = ref(false)
const comparison = ref(null)
const activeTab = ref('text')

const tabs = [
  { id: 'text', label: 'Text Diff' },
  { id: 'metadata', label: 'Metadata' },
  { id: 'acl', label: 'ACL Changes' }
]

watch(
  () => props.show,
  async (newVal) => {
    if (newVal && props.documentId && props.v1 && props.v2) {
      await loadComparison()
    }
  }
)

const loadComparison = async () => {
  loading.value = true
  comparison.value = null
  try {
    const res = await documentsAPI.compareVersions(props.documentId, props.v1, props.v2)
    if (res.is_success) {
      comparison.value = res.data
    }
  } catch (e) {
    console.error('Failed to load comparison', e)
    if (window.$toast) {
      window.$toast.show('Failed to load comparison', 'error')
    }
  } finally {
    loading.value = false
  }
}

const formatDiff = (diffLines) => {
  if (!diffLines || !Array.isArray(diffLines)) {
    return '<pre>No diff available</pre>'
  }
  return diffLines
    .map((line) => {
      if (line.startsWith('+')) {
        return `<div class="diff-line diff-add">${escapeHtml(line)}</div>`
      } else if (line.startsWith('-')) {
        return `<div class="diff-line diff-remove">${escapeHtml(line)}</div>`
      } else if (line.startsWith('@')) {
        return `<div class="diff-line diff-header">${escapeHtml(line)}</div>`
      } else {
        return `<div class="diff-line">${escapeHtml(line)}</div>`
      }
    })
    .join('')
}

const escapeHtml = (text) => {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}
</script>

<style scoped>
.version-compare {
  min-height: 400px;
}

.compare-header {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #eee;
}

.version-info h4 {
  margin: 0 0 0.25rem 0;
  color: var(--primary);
}

.version-date {
  font-size: 0.85rem;
  color: #666;
}

.compare-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid #eee;
}

.tab-btn {
  padding: 0.75rem 1.5rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-weight: 500;
  color: #666;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: var(--primary);
}

.tab-btn-active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.compare-content {
  max-height: 500px;
  overflow-y: auto;
}

.diff-view {
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 6px;
}

.diff-content {
  white-space: pre-wrap;
}

.diff-line {
  padding: 0.25rem 0;
  line-height: 1.5;
}

.diff-add {
  background: #d1fae5;
  color: #065f46;
}

.diff-remove {
  background: #fee2e2;
  color: #991b1b;
}

.diff-header {
  background: #dbeafe;
  color: #1e40af;
  font-weight: bold;
}

.metadata-diff,
.acl-diff {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.diff-item {
  padding: 1rem;
  background: var(--bg-light);
  border-radius: 6px;
}

.diff-field {
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--primary);
}

.diff-values {
  display: flex;
  gap: 1rem;
}

.diff-old,
.diff-new {
  flex: 1;
  padding: 0.5rem;
  background: white;
  border-radius: 4px;
}

.diff-label {
  font-weight: 500;
  margin-right: 0.5rem;
  color: #666;
}

.diff-section {
  padding: 1rem;
  background: var(--bg-light);
  border-radius: 6px;
}

.diff-section h5 {
  margin: 0 0 0.75rem 0;
  color: var(--primary);
}

.acl-item {
  padding: 0.5rem;
  background: white;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.no-changes {
  color: #999;
  font-style: italic;
}

.loading,
.error {
  text-align: center;
  padding: 3rem;
  color: #666;
}
</style>

