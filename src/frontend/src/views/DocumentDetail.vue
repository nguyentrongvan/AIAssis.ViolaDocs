<template>
  <div v-if="loading" class="loading">Loading...</div>
  <div v-else-if="document" class="document-detail">
    <h1 class="page-header">{{ document?.title || 'Document' }}</h1>
      <div class="detail-grid">
        <div class="main-panel">
          <div class="preview-area">
            <iframe v-if="previewUrl" :src="previewUrl" class="preview-frame"></iframe>
            <div v-else class="preview-placeholder">Preview not available</div>
          </div>
        </div>
        <div class="sidebar-panel">
          <div class="section">
            <h3>Metadata</h3>
            <div class="meta-item">
              <label>Title:</label>
              <input v-model="document.title" @blur="saveMetadata" />
            </div>
            <div class="meta-item">
              <label>Owner:</label>
              <span>{{ document.owner?.name }}</span>
            </div>
            <div class="meta-item">
              <label>Created:</label>
              <span>{{ formatDate(document.created_at) }}</span>
            </div>
            <div class="meta-item">
              <label>Size:</label>
              <span>{{ formatSize(document.size) }}</span>
            </div>
          </div>
          <div class="section">
            <h3>Versions</h3>
            <div v-for="version in versions" :key="version.id" class="version-item">
              <div class="version-header">
                <span>v{{ version.version_no }}</span>
                <span class="version-date">{{ formatDate(version.created_at) }}</span>
              </div>
              <div class="version-actions">
                <button @click="viewVersion(version)" class="btn-small">View</button>
                <button @click="compareVersions(version)" class="btn-small">Compare</button>
              </div>
            </div>
          </div>
          <div class="section">
            <h3>Actions</h3>
            <button @click="shareDocument" class="btn-primary">Share</button>
            <button @click="downloadDocument" class="btn-secondary">Download</button>
            <button v-if="authStore.isAdmin" @click="deleteDocument" class="btn-danger">Delete</button>
          </div>
        </div>
      </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'
import api from '../services/api'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const document = ref(null)
const versions = ref([])
const loading = ref(true)
const previewUrl = ref('')

onMounted(async () => {
  const docId = route.params.id
  try {
    const res = await api.get(`/documents/${docId}`)
    if (res.is_success) {
      document.value = res.data
      versions.value = res.data.versions || []
      if (res.data.renditions?.preview) {
        previewUrl.value = res.data.renditions.preview
      }
    }
  } catch (e) {
    console.error('Failed to load document', e)
  } finally {
    loading.value = false
  }
})

const saveMetadata = async () => {
  try {
    await api.patch(`/documents/${document.value.id}`, {
      title: document.value.title
    })
  } catch (e) {
    console.error('Failed to save metadata', e)
  }
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleDateString()
}

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

const viewVersion = (version) => {
  // Navigate to version view
  console.log('View version', version)
}

const compareVersions = (version) => {
  // Open compare modal
  console.log('Compare version', version)
}

const shareDocument = () => {
  console.log('Share document')
}

const downloadDocument = () => {
  window.open(`/api/v1/documents/${document.value.id}/download`, '_blank')
}

const deleteDocument = async () => {
  if (confirm('Are you sure you want to delete this document?')) {
    try {
      await api.delete(`/documents/${document.value.id}`)
      router.push('/')
    } catch (e) {
      console.error('Failed to delete', e)
    }
  }
}
</script>

<style scoped>
.document-detail {
  max-width: 1400px;
  margin: 0 auto;
}
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: 2rem;
}
.main-panel {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.preview-area {
  height: 800px;
}
.preview-frame {
  width: 100%;
  height: 100%;
  border: none;
}
.preview-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
}
.sidebar-panel {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
.section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.section h3 {
  margin: 0 0 1rem 0;
  color: var(--primary);
}
.meta-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}
.meta-item label {
  font-weight: 500;
  color: #666;
}
.meta-item input {
  flex: 1;
  margin-left: 1rem;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.version-item {
  padding: 0.75rem;
  background: var(--bg-light);
  border-radius: 6px;
  margin-bottom: 0.5rem;
}
.version-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}
.version-actions {
  display: flex;
  gap: 0.5rem;
}
.btn-small {
  padding: 0.25rem 0.75rem;
  font-size: 0.85rem;
}
.loading {
  text-align: center;
  padding: 3rem;
}
</style>

