<template>
  <div class="upload-page">
    <h1 class="page-header">Upload Documents</h1>
    
    <!-- Upload Zone -->
    <div class="upload-zone" @drop.prevent="handleDrop" @dragover.prevent @click="openFileDialog">
      <input ref="fileInput" type="file" multiple @change="handleFileSelect" style="display: none" />
      <input ref="folderInput" type="file" webkitdirectory directory multiple @change="handleFileSelect" style="display: none" />
      <div class="upload-content">
        <Upload class="upload-icon" />
        <p>Drag & drop files here or 
          <button @click.stop="openFileDialog" class="btn-link">browse files</button>
          <span class="separator">|</span>
          <button @click.stop="openFolderDialog" class="btn-link">browse folder</button>
        </p>
        <p class="hint">Supports: PDF, DOCX, XLSX, Images</p>
      </div>
    </div>

    <!-- File List -->
    <div v-if="files.length > 0" class="file-list">
      <div v-for="(file, idx) in files" :key="idx" class="file-item">
        <div class="file-header">
          <div class="file-info">
            <span class="file-type-badge" :class="getFileTypeClass(file.file.type)">
              {{ getFileTypeLabel(file.file.type) }}
            </span>
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatSize(file.size) }}</span>
          </div>
          <button v-if="file.status === 'pending'" @click="removeFile(idx)" class="btn-remove">×</button>
        </div>
        
        <div v-if="file.status === 'pending'" class="file-metadata">
          <div class="form-group">
            <label>Title</label>
            <input v-model="file.metadata.title" type="text" :placeholder="file.name" />
          </div>
          <div class="form-group">
            <label>Tags (comma-separated)</label>
            <input v-model="file.metadata.tags" type="text" placeholder="e.g., invoice, 2024, important" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Folder ID</label>
              <input v-model.number="file.metadata.folder_id" type="number" placeholder="Optional" />
            </div>
            <div class="form-group">
              <label>Retention Policy ID</label>
              <input v-model.number="file.metadata.retention_policy_id" type="number" placeholder="Optional" />
            </div>
          </div>
          <div class="form-group">
            <label>Sensitivity</label>
            <select v-model="file.metadata.sensitivity">
              <option value="">None</option>
              <option value="public">Public</option>
              <option value="internal">Internal</option>
              <option value="confidential">Confidential</option>
              <option value="restricted">Restricted</option>
            </select>
          </div>
          <div class="form-group">
            <label>Workflow Template</label>
            <input v-model="file.metadata.workflow_template" type="text" placeholder="Optional workflow template name" />
          </div>
        </div>

        <div v-if="file.status === 'uploading' || file.status === 'processing'" class="file-progress">
          <div class="progress-bar" :style="{ width: file.progress + '%' }"></div>
          <span>{{ file.progress }}%</span>
        </div>
        
        <div class="file-status">
          <div v-if="file.status === 'calculating'" class="status-item">
            <Loader2 class="status-icon" /> Calculating checksum...
          </div>
          <div v-else-if="file.status === 'uploading'" class="status-item">
            <Loader2 class="status-icon" /> Uploading...
          </div>
          <div v-else-if="file.status === 'processing'" class="status-item">
            <Loader2 class="status-icon" /> Processing...
          </div>
          <div v-else-if="file.status === 'done'" class="status-item success">
            <CheckCircle class="status-icon" /> Done
            <a v-if="file.document_id" :href="`/documents/${file.document_id}`" class="doc-link">
              View Document
            </a>
          </div>
          <div v-else-if="file.status === 'error'" class="status-item error">
            <XCircle class="status-icon" /> {{ file.error || 'Error' }}
          </div>
        </div>
      </div>
    </div>

    <!-- Upload Actions -->
    <div v-if="files.length > 0" class="upload-actions">
      <button @click="startUpload" :disabled="uploading || files.every(f => f.status === 'done')" class="btn-primary">
        {{ uploading ? 'Uploading...' : 'Upload All' }}
      </button>
      <button @click="clearFiles" class="btn-secondary">Clear All</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../services/api'
import { Upload, Loader2, CheckCircle, XCircle } from 'lucide-vue-next'

const fileInput = ref(null)
const folderInput = ref(null)
const files = ref([])
const uploading = ref(false)

const handleDrop = (e) => {
  const droppedFiles = Array.from(e.dataTransfer.files)
  addFiles(droppedFiles)
}

const openFileDialog = () => {
  if (fileInput.value) {
    fileInput.value.click()
  }
}

const openFolderDialog = () => {
  if (folderInput.value) {
    folderInput.value.click()
  }
}

const handleFileSelect = (e) => {
  const selectedFiles = Array.from(e.target.files)
  addFiles(selectedFiles)
  // Reset input to allow selecting same file again
  e.target.value = ''
}

const addFiles = (fileList) => {
  fileList.forEach(file => {
    files.value.push({
      name: file.name,
      size: file.size,
      file,
      progress: 0,
      status: 'pending',
      checksum: null,
      document_id: null,
      error: null,
      metadata: {
        title: '',
        tags: '',
        folder_id: null,
        retention_policy_id: null,
        sensitivity: '',
        workflow_template: ''
      }
    })
  })
}

const removeFile = (index) => {
  files.value.splice(index, 1)
}

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

const getFileTypeLabel = (mimeType) => {
  if (mimeType === 'application/pdf') return 'PDF'
  if (mimeType.includes('wordprocessingml')) return 'DOCX'
  if (mimeType.includes('spreadsheetml')) return 'XLSX'
  if (mimeType.startsWith('image/')) return 'IMAGE'
  return 'FILE'
}

const getFileTypeClass = (mimeType) => {
  if (mimeType === 'application/pdf') return 'type-pdf'
  if (mimeType.includes('wordprocessingml')) return 'type-docx'
  if (mimeType.includes('spreadsheetml')) return 'type-xlsx'
  if (mimeType.startsWith('image/')) return 'type-image'
  return 'type-other'
}

// Calculate SHA-256 checksum
const calculateChecksum = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        const arrayBuffer = e.target.result
        const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer)
        const hashArray = Array.from(new Uint8Array(hashBuffer))
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
        resolve(hashHex)
      } catch (err) {
        reject(err)
      }
    }
    reader.onerror = reject
    reader.readAsArrayBuffer(file)
  })
}

const parseTags = (tagsString) => {
  if (!tagsString || !tagsString.trim()) return []
  return tagsString.split(',').map(t => t.trim()).filter(t => t.length > 0)
}

const startUpload = async () => {
  uploading.value = true
  
  for (const fileItem of files.value) {
    if (fileItem.status === 'done' || fileItem.status === 'uploading' || fileItem.status === 'processing') {
      continue
    }
    
    try {
      // Calculate checksum
      fileItem.status = 'calculating'
      fileItem.checksum = await calculateChecksum(fileItem.file)
      
      // Init upload
      fileItem.status = 'uploading'
      const initRes = await api.post('/uploads/init', {
        filename: fileItem.name,
        size: fileItem.size,
        mime: fileItem.file.type || 'application/octet-stream',
        checksum: fileItem.checksum
      })
      
      if (!initRes.is_success) {
        throw new Error(initRes.message || 'Failed to initialize upload')
      }
      
      const { upload_id, upload_url } = initRes.data
      
      // Upload file to MinIO
      await uploadFile(fileItem.file, upload_url, (progress) => {
        fileItem.progress = progress
      })
      
      // Prepare metadata for finalize
      const tags = parseTags(fileItem.metadata.tags)
      const finalizeData = {
        title: fileItem.metadata.title || fileItem.name,
        tags: tags,
        folder_id: fileItem.metadata.folder_id || null,
        retention_policy_id: fileItem.metadata.retention_policy_id || null,
        sensitivity: fileItem.metadata.sensitivity || null,
        workflow_template: fileItem.metadata.workflow_template || null
      }
      
      // Finalize upload
      fileItem.status = 'processing'
      const finalizeRes = await api.post(`/uploads/${upload_id}/finalize`, finalizeData)
      
      if (!finalizeRes.is_success) {
        throw new Error(finalizeRes.message || 'Failed to finalize upload')
      }
      
      fileItem.document_id = finalizeRes.data.document_id
      fileItem.status = 'done'
      fileItem.progress = 100
      
    } catch (e) {
      fileItem.status = 'error'
      fileItem.error = e.response?.data?.message || e.message || 'Upload failed'
      console.error('Upload failed', e)
    }
  }
  
  uploading.value = false
}

const uploadFile = (file, url, onProgress) => {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    })
    
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve()
      } else {
        reject(new Error(`Upload failed with status ${xhr.status}`))
      }
    })
    
    xhr.addEventListener('error', () => {
      reject(new Error('Network error during upload'))
    })
    
    xhr.addEventListener('abort', () => {
      reject(new Error('Upload aborted'))
    })
    
    xhr.open('PUT', url)
    xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream')
    xhr.send(file)
  })
}

const clearFiles = () => {
  files.value = []
}
</script>

<style scoped>
.upload-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
}

.upload-zone {
  border: 2px dashed var(--primary);
  border-radius: 12px;
  padding: 3rem;
  text-align: center;
  background: var(--bg-light);
  margin-bottom: 2rem;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-zone:hover {
  border-color: var(--primary-dark);
  background: var(--bg-light-hover);
}

.upload-content {
  pointer-events: none;
}

.upload-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 1rem;
  color: var(--primary);
  stroke-width: 1.5;
}

.hint {
  color: #666;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}

.file-list {
  margin-bottom: 2rem;
}

.file-item {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.file-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.file-type-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.type-pdf { background: #ff4444; color: white; }
.type-docx { background: #2b579a; color: white; }
.type-xlsx { background: #217346; color: white; }
.type-image { background: #4caf50; color: white; }
.type-other { background: #666; color: white; }

.file-name {
  font-weight: 500;
  flex: 1;
}

.file-size {
  color: #666;
  font-size: 0.9rem;
}

.btn-remove {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #999;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  line-height: 1;
}

.btn-remove:hover {
  color: var(--error);
}

.file-metadata {
  background: var(--bg-light);
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  font-size: 0.9rem;
  color: #333;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.file-progress {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: var(--primary);
  border-radius: 4px;
  transition: width 0.3s;
}

.file-status {
  margin-top: 0.5rem;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.status-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  stroke-width: 2;
}

.status-item.success {
  color: var(--success);
}

.status-item.error {
  color: var(--error);
}

.status-item .status-icon {
  animation: spin 1s linear infinite;
}

.status-item.success .status-icon,
.status-item.error .status-icon {
  animation: none;
}

.btn-link {
  background: none;
  border: none;
  color: var(--primary);
  cursor: pointer;
  text-decoration: underline;
  font-size: inherit;
  padding: 0;
  margin: 0;
}

.btn-link:hover {
  color: var(--primary-dark);
}

.separator {
  margin: 0 0.5rem;
  color: #999;
}

.doc-link {
  margin-left: 0.5rem;
  color: var(--primary);
  text-decoration: none;
}

.doc-link:hover {
  text-decoration: underline;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.upload-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
