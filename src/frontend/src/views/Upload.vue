<template>
  <Layout>
    <template #header>
      <h1>Upload Documents</h1>
    </template>
    <div class="upload-page">
      <div class="upload-zone" @drop.prevent="handleDrop" @dragover.prevent>
        <input ref="fileInput" type="file" multiple @change="handleFileSelect" style="display: none" />
        <div class="upload-content">
          <div class="upload-icon">📤</div>
          <p>Drag & drop files here or <button @click="$refs.fileInput.click()" class="btn-link">browse</button></p>
          <p class="hint">Supports: PDF, DOCX, XLSX, Images</p>
        </div>
      </div>
      <div v-if="files.length > 0" class="file-list">
        <div v-for="(file, idx) in files" :key="idx" class="file-item">
          <div class="file-info">
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatSize(file.size) }}</span>
          </div>
          <div class="file-progress">
            <div class="progress-bar" :style="{ width: file.progress + '%' }"></div>
            <span>{{ file.progress }}%</span>
          </div>
          <div v-if="file.status === 'uploading'" class="file-status">Uploading...</div>
          <div v-else-if="file.status === 'processing'" class="file-status">Processing...</div>
          <div v-else-if="file.status === 'done'" class="file-status success">✓ Done</div>
          <div v-else-if="file.status === 'error'" class="file-status error">✗ Error</div>
        </div>
      </div>
      <div v-if="files.length > 0" class="upload-actions">
        <button @click="startUpload" :disabled="uploading" class="btn-primary">
          {{ uploading ? 'Uploading...' : 'Upload All' }}
        </button>
        <button @click="clearFiles" class="btn-secondary">Clear</button>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref } from 'vue'
import Layout from '../components/Layout.vue'
import api from '../services/api'

const fileInput = ref(null)
const files = ref([])
const uploading = ref(false)

const handleDrop = (e) => {
  const droppedFiles = Array.from(e.dataTransfer.files)
  addFiles(droppedFiles)
}

const handleFileSelect = (e) => {
  const selectedFiles = Array.from(e.target.files)
  addFiles(selectedFiles)
}

const addFiles = (fileList) => {
  fileList.forEach(file => {
    files.value.push({
      name: file.name,
      size: file.size,
      file,
      progress: 0,
      status: 'pending'
    })
  })
}

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

const startUpload = async () => {
  uploading.value = true
  for (const fileItem of files.value) {
    if (fileItem.status === 'done') continue
    try {
      fileItem.status = 'uploading'
      const initRes = await api.post('/uploads/init', {
        filename: fileItem.name,
        size: fileItem.size,
        mime: fileItem.file.type
      })
      if (initRes.is_success) {
        const { upload_id, upload_url } = initRes.data
        await uploadFile(fileItem.file, upload_url, (progress) => {
          fileItem.progress = progress
        })
        const finalizeRes = await api.post(`/uploads/${upload_id}/finalize`, {
          title: fileItem.name
        })
        if (finalizeRes.is_success) {
          fileItem.status = 'processing'
          setTimeout(() => {
            fileItem.status = 'done'
          }, 2000)
        }
      }
    } catch (e) {
      fileItem.status = 'error'
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
      if (xhr.status === 200) resolve()
      else reject(new Error('Upload failed'))
    })
    xhr.addEventListener('error', reject)
    xhr.open('PUT', url)
    xhr.send(file)
  })
}

const clearFiles = () => {
  files.value = []
}
</script>

<style scoped>
.upload-page {
  max-width: 800px;
  margin: 0 auto;
}
.upload-zone {
  border: 2px dashed var(--primary);
  border-radius: 12px;
  padding: 3rem;
  text-align: center;
  background: var(--bg-light);
  margin-bottom: 2rem;
  cursor: pointer;
}
.upload-content {
  pointer-events: none;
}
.upload-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
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
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.file-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}
.file-name {
  font-weight: 500;
}
.file-size {
  color: #666;
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
  font-size: 0.9rem;
}
.file-status.success {
  color: var(--success);
}
.file-status.error {
  color: var(--error);
}
.upload-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}
</style>

