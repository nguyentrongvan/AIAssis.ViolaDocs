<template>
  <div v-if="loading" class="loading">Loading...</div>
  <div v-else-if="document" class="document-detail">
    <div class="page-header">
      <h1>{{ document?.title || 'Document' }}</h1>
      <StatusBadge :status="document.status" />
    </div>

    <div class="detail-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        :class="['tab-btn', { 'tab-btn-active': activeTab === tab.id }]"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="detail-content">
      <!-- Preview Tab -->
      <div v-if="activeTab === 'preview'" class="tab-content">
        <div class="preview-controls">
          <div class="preview-options">
            <button
              @click="showOcrText = !showOcrText"
              :class="['btn-small', { 'btn-active': showOcrText }]"
            >
              {{ showOcrText ? 'Hide' : 'Show' }} OCR Text
            </button>
            <select v-model="selectedVersion" @change="loadVersionPreview" class="version-select">
              <option v-for="v in versions" :key="v.id" :value="v.id">
                Version {{ v.version_no }}
              </option>
            </select>
          </div>
        </div>
        <div class="preview-area">
          <iframe v-if="previewUrl && !showOcrText" :src="previewUrl" class="preview-frame"></iframe>
          <div v-else-if="showOcrText" class="ocr-text-view">
            <div v-if="ocrText" class="ocr-text-content">
              <div class="ocr-text-header">
                <span>OCR Text</span>
                <button @click="copyOcrText" class="btn-small">
                  <Copy :size="14" />
                  Copy
                </button>
              </div>
              <pre class="ocr-text-pre">{{ ocrText }}</pre>
            </div>
            <div v-else class="ocr-text-empty">
              <p>OCR text not available for this version</p>
            </div>
          </div>
          <div v-else class="preview-placeholder">Preview not available</div>
        </div>
      </div>

      <!-- Metadata Tab -->
      <div v-if="activeTab === 'metadata'" class="tab-content">
        <div class="metadata-form">
          <div class="form-group">
            <label>Title *</label>
            <input v-model="metadataForm.title" />
          </div>
          <div class="form-group">
            <label>Folder</label>
            <select v-model.number="metadataForm.folder_id">
              <option :value="null">None</option>
              <option v-for="f in folders" :key="f.id" :value="f.id">
                {{ f.name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>Retention Policy</label>
            <select v-model.number="metadataForm.retention_policy_id">
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
          <div class="form-group">
            <label>Tags</label>
            <input
              v-model="tagInput"
              @keyup.enter="addTag"
              placeholder="Press Enter to add tag"
            />
            <div class="tags-list">
              <span
                v-for="tag in metadataForm.tags"
                :key="tag"
                class="tag-badge"
              >
                {{ tag }}
                <button @click="removeTag(tag)" class="tag-remove">×</button>
              </span>
            </div>
          </div>
          <div class="form-group">
            <label>Owner</label>
            <span>{{ document.owner?.name || 'Unknown' }}</span>
          </div>
          <div class="form-group">
            <label>Created</label>
            <span>{{ formatDate(document.created_at) }}</span>
          </div>
          <div class="form-group">
            <label>Size</label>
            <span>{{ formatSize(document.size) }}</span>
          </div>
          <div class="form-actions">
            <button @click="saveMetadata" class="btn-primary">Save Changes</button>
          </div>
        </div>
      </div>

      <!-- Comments Tab -->
      <div v-if="activeTab === 'comments'" class="tab-content">
        <div class="comments-section">
          <div class="comments-list">
            <div
              v-for="comment in comments"
              :key="comment.id"
              class="comment-item"
              :class="{ 'comment-annotation': comment.type === 'annotation' }"
            >
              <div class="comment-header">
                <div class="comment-author">
                  <User :size="16" />
                  <span>{{ comment.user?.name || 'Unknown' }}</span>
                </div>
                <span class="comment-date">{{ formatDate(comment.created_at) }}</span>
                <button
                  v-if="comment.user_id === authStore.user?.id"
                  @click="deleteComment(comment.id)"
                  class="btn-link-small"
                >
                  <Trash2 :size="14" />
                </button>
              </div>
              <div class="comment-content">{{ comment.content }}</div>
              <div v-if="comment.position" class="comment-position">
                Position: {{ JSON.stringify(comment.position) }}
              </div>
            </div>
            <div v-if="comments.length === 0" class="empty-state">
              No comments yet
            </div>
          </div>
          <div class="comment-form">
            <div class="comment-type-selector">
              <label>
                <input
                  type="radio"
                  v-model="commentForm.type"
                  value="comment"
                />
                Comment
              </label>
              <label>
                <input
                  type="radio"
                  v-model="commentForm.type"
                  value="annotation"
                />
                Annotation
              </label>
            </div>
            <textarea
              v-model="commentForm.content"
              placeholder="Add a comment or annotation..."
              rows="3"
            ></textarea>
            <div v-if="commentForm.type === 'annotation'" class="annotation-position">
              <label>Position (JSON):</label>
              <input
                v-model="commentForm.position"
                placeholder='{"page": 1, "x": 100, "y": 200}'
              />
            </div>
            <button @click="addComment" class="btn-primary" :disabled="!commentForm.content">
              Add {{ commentForm.type === 'annotation' ? 'Annotation' : 'Comment' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Versions Tab -->
      <div v-if="activeTab === 'versions'" class="tab-content">
        <div class="versions-timeline">
          <div
            v-for="version in versions"
            :key="version.id"
            class="version-timeline-item"
          >
            <div class="version-marker"></div>
            <div class="version-content">
              <div class="version-header">
                <div>
                  <h4>Version {{ version.version_no }}</h4>
                  <div class="version-meta">
                    <span>{{ version.created_by_user?.name || 'Unknown' }}</span>
                    <span>{{ formatDate(version.created_at) }}</span>
                    <span v-if="version.source">Source: {{ version.source }}</span>
                    <span v-if="version.device">Device: {{ version.device }}</span>
                  </div>
                </div>
                <div class="version-actions">
                  <button @click="viewVersion(version)" class="btn-small">
                    <Eye :size="16" />
                    View
                  </button>
                  <button
                    v-if="versions.length > 1"
                    @click="compareWithVersion(version)"
                    class="btn-small"
                  >
                    <GitCompare :size="16" />
                    Compare
                  </button>
                  <button @click="downloadVersion(version)" class="btn-small">
                    <Download :size="16" />
                    Download
                  </button>
                  <button
                    v-if="authStore.isAdmin && version.version_no !== latestVersion"
                    @click="restoreVersion(version)"
                    class="btn-small"
                  >
                    <RotateCcw :size="16" />
                    Restore
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Share Tab -->
      <div v-if="activeTab === 'share'" class="tab-content">
        <div class="share-section">
          <h3>Share Document</h3>
          <div class="share-form">
            <div class="form-group">
              <label>Share with Users</label>
              <input
                v-model="shareForm.userEmails"
                placeholder="Enter email addresses (comma-separated)"
              />
            </div>
            <div class="form-group">
              <label>Share with Roles</label>
              <select v-model="shareForm.roleIds" multiple>
                <option v-for="role in roles" :key="role.id" :value="role.id">
                  {{ role.name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>Permission</label>
              <select v-model="shareForm.permission">
                <option value="read">Read</option>
                <option value="write">Write</option>
              </select>
            </div>
            <div class="form-group">
              <label>Expires At (optional)</label>
              <input v-model="shareForm.expires_at" type="datetime-local" />
            </div>
            <button @click="shareDocument" class="btn-primary">Share</button>
          </div>
          <div v-if="shares.length > 0" class="shares-list">
            <h4>Current Shares</h4>
            <div v-for="share in shares" :key="share.id" class="share-item">
              <div class="share-info">
                <span v-if="share.user">{{ share.user.name }}</span>
                <span v-else-if="share.role">{{ share.role.name }}</span>
                <span class="share-permission">{{ share.permission }}</span>
              </div>
              <button @click="removeShare(share.id)" class="btn-small btn-danger">
                Remove
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Activity Tab -->
      <div v-if="activeTab === 'activity'" class="tab-content">
        <div class="activity-log">
          <div
            v-for="activity in activities"
            :key="activity.id"
            class="activity-item"
          >
            <div class="activity-icon">
              <component :is="getActivityIcon(activity.action)" :size="20" />
            </div>
            <div class="activity-content">
              <div class="activity-header">
                <span class="activity-action">{{ activity.action }}</span>
                <span class="activity-date">{{ formatDate(activity.created_at) }}</span>
              </div>
              <div class="activity-actor">
                by {{ activity.actor?.name || 'Unknown' }}
              </div>
              <div v-if="activity.metadata" class="activity-metadata">
                {{ JSON.stringify(activity.metadata) }}
              </div>
            </div>
          </div>
          <div v-if="activities.length === 0" class="empty-state">
            No activity recorded
          </div>
        </div>
      </div>
    </div>

    <!-- Version Compare Modal -->
    <VersionCompare
      v-model:show="showCompareModal"
      :document-id="document.id"
      :v1="compareV1"
      :v2="compareV2"
      @close="showCompareModal = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'
import { useDocumentsStore } from '../store/documents'
import { useFoldersStore } from '../store/folders'
import { useSettingsStore } from '../store/settings'
import { useRolesStore } from '../store/roles'
import { documentsAPI, foldersAPI, settingsAPI, rolesAPI } from '../services/api'
import { StatusBadge, VersionCompare } from '../components'
import {
  User,
  Trash2,
  Eye,
  GitCompare,
  Download,
  RotateCcw,
  FileText,
  Share2,
  Clock,
  MessageSquare,
  Copy
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const documentsStore = useDocumentsStore()
const foldersStore = useFoldersStore()
const settingsStore = useSettingsStore()
const rolesStore = useRolesStore()

const document = ref(null)
const versions = ref([])
const comments = ref([])
const shares = ref([])
const activities = ref([])
const folders = ref([])
const retentionPolicies = ref([])
const roles = ref([])
const loading = ref(true)
const activeTab = ref('preview')
const showOcrText = ref(false)
const previewUrl = ref('')
const ocrText = ref('')
const selectedVersion = ref(null)
const showCompareModal = ref(false)
const compareV1 = ref(null)
const compareV2 = ref(null)

const tabs = [
  { id: 'preview', label: 'Preview', icon: FileText },
  { id: 'metadata', label: 'Metadata', icon: FileText },
  { id: 'comments', label: 'Comments', icon: MessageSquare },
  { id: 'versions', label: 'Versions', icon: Clock },
  { id: 'share', label: 'Share', icon: Share2 },
  { id: 'activity', label: 'Activity', icon: Clock }
]

const metadataForm = ref({
  title: '',
  folder_id: null,
  retention_policy_id: null,
  tags: []
})

const tagInput = ref('')
const commentForm = ref({
  content: '',
  type: 'comment',
  position: null
})

const shareForm = ref({
  userEmails: '',
  roleIds: [],
  permission: 'read',
  expires_at: null
})

const latestVersion = computed(() => {
  if (versions.value.length === 0) return 0
  return Math.max(...versions.value.map(v => v.version_no))
})

onMounted(async () => {
  const docId = parseInt(route.params.id)
  await loadDocument(docId)
  await loadFolders()
  await loadRetentionPolicies()
  await loadRoles()
})

const loadDocument = async (docId) => {
  loading.value = true
  try {
    await documentsStore.fetchDocument(docId)
    document.value = documentsStore.currentDocument
    versions.value = documentsStore.versions

    if (versions.value.length > 0) {
      selectedVersion.value = versions.value[0].id
      await loadVersionPreview()
    }

    // Load preview URL from document or latest version
    if (document.value.preview_url) {
      previewUrl.value = document.value.preview_url
    } else if (versions.value.length > 0 && versions.value[0].renditions?.preview) {
      previewUrl.value = versions.value[0].renditions.preview
    }

    // Initialize metadata form
    metadataForm.value = {
      title: document.value.title || '',
      folder_id: document.value.folder_id,
      retention_policy_id: document.value.retention_policy_id,
      tags: document.value.tags || []
    }

    // Load comments
    await loadComments(docId)
  } catch (e) {
    console.error('Failed to load document', e)
    if (window.$toast) {
      window.$toast.show('Failed to load document', 'error')
    }
  } finally {
    loading.value = false
  }
}

const loadVersionPreview = async () => {
  if (!selectedVersion.value) return
  const version = versions.value.find(v => v.id === selectedVersion.value)
  if (!version) return
  
  // Load preview URL
  if (version?.renditions?.preview) {
    previewUrl.value = version.renditions.preview
  } else {
    previewUrl.value = ''
  }
  
  // Load OCR text if available
  if (version?.text_uri || version?.ocr_uri) {
    try {
      const res = await documentsAPI.rendition(document.value.id, 'text', { version_id: version.id })
      if (res.is_success && res.data) {
        // API now returns content directly in res.data.content
        ocrText.value = res.data.content || res.data || ''
      } else {
        ocrText.value = ''
      }
    } catch (e) {
      console.error('Failed to load OCR text', e)
      ocrText.value = ''
    }
  } else {
    ocrText.value = ''
  }
}

const copyOcrText = async () => {
  if (!ocrText.value) return
  try {
    await navigator.clipboard.writeText(ocrText.value)
    if (window.$toast) {
      window.$toast.show('OCR text copied to clipboard', 'success')
    }
  } catch (e) {
    console.error('Failed to copy text', e)
    if (window.$toast) {
      window.$toast.show('Failed to copy text', 'error')
    }
  }
}

const loadComments = async (docId) => {
  try {
    await documentsStore.fetchComments(docId)
    comments.value = documentsStore.comments
  } catch (e) {
    console.error('Failed to load comments', e)
  }
}

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
    roles.value = rolesStore.roles
  } catch (e) {
    console.error('Failed to load roles', e)
  }
}

const saveMetadata = async () => {
  try {
    await documentsStore.updateDocument(document.value.id, metadataForm.value)
    if (window.$toast) {
      window.$toast.show('Metadata saved', 'success')
    }
  } catch (e) {
    console.error('Failed to save metadata', e)
    if (window.$toast) {
      window.$toast.show('Failed to save metadata', 'error')
    }
  }
}

const addTag = () => {
  if (tagInput.value.trim() && !metadataForm.value.tags.includes(tagInput.value.trim())) {
    metadataForm.value.tags.push(tagInput.value.trim())
    tagInput.value = ''
  }
}

const removeTag = (tag) => {
  metadataForm.value.tags = metadataForm.value.tags.filter(t => t !== tag)
}

const addComment = async () => {
  if (!commentForm.value.content.trim()) return
  try {
    const data = {
      content: commentForm.value.content,
      type: commentForm.value.type
    }
    if (commentForm.value.type === 'annotation' && commentForm.value.position) {
      try {
        data.position = JSON.parse(commentForm.value.position)
      } catch (e) {
        if (window.$toast) {
          window.$toast.show('Invalid position JSON', 'error')
        }
        return
      }
    }
    await documentsStore.createComment(document.value.id, data)
    commentForm.value = { content: '', type: 'comment', position: null }
    if (window.$toast) {
      window.$toast.show('Comment added', 'success')
    }
  } catch (e) {
    console.error('Failed to add comment', e)
    if (window.$toast) {
      window.$toast.show('Failed to add comment', 'error')
    }
  }
}

const deleteComment = async (commentId) => {
  try {
    await documentsStore.deleteComment(document.value.id, commentId)
    if (window.$toast) {
      window.$toast.show('Comment deleted', 'success')
    }
  } catch (e) {
    console.error('Failed to delete comment', e)
    if (window.$toast) {
      window.$toast.show('Failed to delete comment', 'error')
    }
  }
}

const viewVersion = (version) => {
  selectedVersion.value = version.id
  loadVersionPreview()
  activeTab.value = 'preview'
}

const compareWithVersion = (version) => {
  const latest = versions.value.find(v => v.version_no === latestVersion.value)
  if (latest && version.id !== latest.id) {
    compareV1.value = latest.version_no
    compareV2.value = version.version_no
    showCompareModal.value = true
  }
}

const downloadVersion = (version) => {
  window.open(`/api/v1/documents/${document.value.id}/versions/${version.id}/download`, '_blank')
}

const restoreVersion = async (version) => {
  if (confirm(`Restore to version ${version.version_no}?`)) {
    try {
      // Implementation depends on backend API
      if (window.$toast) {
        window.$toast.show('Version restore not yet implemented', 'info')
      }
    } catch (e) {
      console.error('Failed to restore version', e)
    }
  }
}

const shareDocument = async () => {
  try {
    const data = {
      permission: shareForm.value.permission
    }
    if (shareForm.value.userEmails) {
      data.user_emails = shareForm.value.userEmails.split(',').map(e => e.trim())
    }
    if (shareForm.value.roleIds.length > 0) {
      data.role_ids = shareForm.value.roleIds
    }
    if (shareForm.value.expires_at) {
      data.expires_at = shareForm.value.expires_at
    }
    await documentsAPI.share(document.value.id, data)
    shareForm.value = { userEmails: '', roleIds: [], permission: 'read', expires_at: null }
    if (window.$toast) {
      window.$toast.show('Document shared', 'success')
    }
  } catch (e) {
    console.error('Failed to share document', e)
    if (window.$toast) {
      window.$toast.show('Failed to share document', 'error')
    }
  }
}

const removeShare = async (shareId) => {
  try {
    // Implementation depends on backend API
    if (window.$toast) {
      window.$toast.show('Remove share not yet implemented', 'info')
    }
  } catch (e) {
    console.error('Failed to remove share', e)
  }
}

const getActivityIcon = (action) => {
  const icons = {
    create: FileText,
    update: FileText,
    delete: Trash2,
    share: Share2,
    comment: MessageSquare
  }
  return icons[action] || Clock
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}
</script>

<style scoped>
.document-detail {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.detail-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #eee;
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
  margin-bottom: -2px;
}

.tab-btn:hover {
  color: var(--primary);
}

.tab-btn-active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.detail-content {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.tab-content {
  min-height: 400px;
}

.preview-controls {
  margin-bottom: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-options {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.version-select {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.preview-area {
  height: 800px;
  border: 1px solid #eee;
  border-radius: 6px;
  overflow: hidden;
}

.preview-frame {
  width: 100%;
  height: 100%;
  border: none;
}

.ocr-text-view {
  padding: 0;
  background: var(--bg-white);
  border-radius: 6px;
  max-height: 600px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.ocr-text-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.ocr-text-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-md);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-light);
  border-radius: 6px 6px 0 0;
}

.ocr-text-header span {
  font-weight: 600;
  color: var(--text-dark);
}

.ocr-text-pre {
  flex: 1;
  margin: 0;
  padding: var(--space-lg);
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  overflow-y: auto;
  background: var(--bg-white);
  color: var(--text-dark);
}

.ocr-text-empty {
  padding: var(--space-3xl);
  text-align: center;
  color: var(--text-medium);
}

.preview-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
}

.metadata-form {
  max-width: 600px;
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
  padding: var(--space-md) var(--space-lg);
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-lg);
  background: var(--bg-white);
  font-size: 0.95rem;
  font-family: inherit;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.form-group input[type="date"],
.form-group input[type="datetime-local"] {
  padding-right: var(--space-xl);
  cursor: pointer;
  position: relative;
}

.form-group input[type="date"]::-webkit-calendar-picker-indicator,
.form-group input[type="datetime-local"]::-webkit-calendar-picker-indicator {
  cursor: pointer;
  opacity: 0.6;
  filter: grayscale(1);
  transition: all var(--transition-base);
  padding: var(--space-xs);
  border-radius: var(--radius-sm);
}

.form-group input[type="date"]::-webkit-calendar-picker-indicator:hover,
.form-group input[type="datetime-local"]::-webkit-calendar-picker-indicator:hover {
  opacity: 1;
  filter: grayscale(0);
  background: var(--gradient-ai-soft);
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--ai-cyan);
  box-shadow: var(--shadow-md), 0 0 0 3px rgba(0, 217, 255, 0.1);
}

.form-group input[type="date"]:focus::-webkit-calendar-picker-indicator,
.form-group input[type="datetime-local"]:focus::-webkit-calendar-picker-indicator {
  opacity: 1;
  filter: grayscale(0);
}

.tags-list {
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

.comments-section {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.comment-item {
  padding: 1rem;
  background: var(--bg-light);
  border-radius: 6px;
  border-left: 3px solid var(--primary);
}

.comment-annotation {
  border-left-color: #f59e0b;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.comment-author {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
}

.comment-date {
  font-size: 0.85rem;
  color: #666;
}

.comment-content {
  margin-top: 0.5rem;
  white-space: pre-wrap;
}

.comment-position {
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #666;
  font-family: monospace;
}

.comment-form {
  padding: 1.5rem;
  background: var(--bg-light);
  border-radius: 6px;
}

.comment-type-selector {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.comment-type-selector label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.comment-form textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-family: inherit;
}

.annotation-position {
  margin-bottom: 1rem;
}

.annotation-position label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.annotation-position input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-family: monospace;
}

.versions-timeline {
  position: relative;
  padding-left: 2rem;
}

.versions-timeline::before {
  content: '';
  position: absolute;
  left: 0.5rem;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #eee;
}

.version-timeline-item {
  position: relative;
  margin-bottom: 2rem;
}

.version-marker {
  position: absolute;
  left: -1.75rem;
  top: 0.5rem;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--primary);
  border: 2px solid white;
  box-shadow: 0 0 0 2px var(--primary);
}

.version-content {
  background: var(--bg-light);
  padding: 1.5rem;
  border-radius: 6px;
}

.version-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.5rem;
}

.version-header h4 {
  margin: 0 0 0.5rem 0;
  color: var(--primary);
}

.version-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  color: #666;
  flex-wrap: wrap;
}

.version-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.share-section {
  max-width: 600px;
}

.share-form {
  margin-bottom: 2rem;
}

.shares-list {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #eee;
}

.shares-list h4 {
  margin: 0 0 1rem 0;
  color: var(--primary);
}

.share-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--bg-light);
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.share-info {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.share-permission {
  padding: 0.25rem 0.75rem;
  background: white;
  border-radius: 12px;
  font-size: 0.85rem;
}

.activity-log {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.activity-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: var(--bg-light);
  border-radius: 6px;
}

.activity-icon {
  flex-shrink: 0;
  color: var(--primary);
}

.activity-content {
  flex: 1;
}

.activity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
}

.activity-action {
  font-weight: 500;
  color: var(--primary);
}

.activity-date {
  font-size: 0.85rem;
  color: #666;
}

.activity-actor {
  font-size: 0.9rem;
  color: #666;
}

.activity-metadata {
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #999;
  font-family: monospace;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #666;
}

.loading {
  text-align: center;
  padding: 3rem;
}

.btn-small {
  background: var(--bg-white);
  border: 1.5px solid #e5e7eb;
  color: var(--text-dark);
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

.btn-small:hover {
  background: var(--primary-light);
  border-color: var(--primary);
  color: var(--primary-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-small:active {
  transform: translateY(0);
  box-shadow: var(--shadow-sm);
}

.btn-small.btn-active {
  background: var(--gradient-primary);
  color: white;
  border-color: transparent;
  box-shadow: var(--shadow-md), var(--shadow-glow);
}

.btn-small.btn-active:hover {
  background: var(--gradient-primary);
  color: white;
  transform: translateY(-1px);
  box-shadow: var(--shadow-lg), var(--shadow-glow);
}

.btn-link-small {
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

.btn-link-small:hover {
  background: var(--primary-light);
  color: var(--primary-dark);
  transform: translateY(-1px);
}

.btn-link-small:active {
  transform: translateY(0);
}
</style>
