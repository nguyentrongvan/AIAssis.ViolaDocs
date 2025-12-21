<template>
  <div class="avatar-upload">
    <div class="avatar-preview" @click="triggerFileInput">
      <img
        v-if="displayAvatarUrl && !imageError"
        :src="displayAvatarUrl"
        alt="Avatar"
        class="avatar-image"
        @error="handleImageError"
        @load="imageError = false"
      />
      <div v-else class="avatar-placeholder">
        <User :size="40" />
      </div>
      <div class="avatar-overlay">
        <Camera :size="24" />
        <span>{{ $t('profile.changeAvatar') }}</span>
      </div>
    </div>
    <input
      ref="fileInput"
      type="file"
      accept="image/jpeg,image/png,image/webp"
      @change="handleFileSelect"
      style="display: none"
    />
    <div v-if="uploading" class="upload-progress">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${uploadProgress}%` }"></div>
      </div>
      <span>{{ uploadProgress }}%</span>
    </div>
    <p v-if="error" class="error-message">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { User, Camera } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  avatarUrl: {
    type: String,
    default: null
  },
  userId: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['uploaded'])

const { t } = useI18n()
const fileInput = ref(null)
const previewUrl = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const error = ref(null)
const imageError = ref(false)

const avatarBlobUrl = ref(null)

const displayAvatarUrl = computed(() => {
  // Use blob URL if available (loaded via fetch with auth)
  if (avatarBlobUrl.value) {
    return avatarBlobUrl.value
  }
  
  // Use preview if available
  if (previewUrl.value) {
    return previewUrl.value
  }
  
  return null
})

// Load avatar using fetch with Authorization header
const loadAvatar = async () => {
  if (!props.avatarUrl) return
  
  try {
    const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1'
    const baseUrl = API_BASE.replace('/api/v1', '')
    
    let avatarEndpoint = `${baseUrl}/api/v1/users/me/avatar`
    
    // If avatar_url contains object parameter, pass it along
    if (props.avatarUrl.includes('?object=')) {
      const url = new URL(props.avatarUrl, 'http://dummy.com')
      const objectParam = url.searchParams.get('object')
      if (objectParam) {
        avatarEndpoint += `?object=${encodeURIComponent(objectParam)}`
      }
    }
    
    // Add cache busting
    avatarEndpoint += `${avatarEndpoint.includes('?') ? '&' : '?'}_t=${Date.now()}`
    
    // Fetch with Authorization header
    const token = localStorage.getItem('access_token')
    const response = await fetch(avatarEndpoint, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (response.ok) {
      const blob = await response.blob()
      // Create blob URL
      if (avatarBlobUrl.value) {
        URL.revokeObjectURL(avatarBlobUrl.value)
      }
      avatarBlobUrl.value = URL.createObjectURL(blob)
      imageError.value = false
    } else {
      throw new Error(`Failed to load avatar: ${response.status}`)
    }
  } catch (e) {
    console.error('Failed to load avatar', e)
    imageError.value = true
  }
}

// Watch for avatarUrl changes and load avatar
watch(() => props.avatarUrl, (newUrl) => {
  if (newUrl && !previewUrl.value) {
    loadAvatar()
  }
}, { immediate: true })

const handleImageError = async (e) => {
  imageError.value = true
  console.error('Failed to load avatar image', e)
  // Try to reload avatar
  await loadAvatar()
}

// Cleanup blob URL on unmount
onUnmounted(() => {
  if (avatarBlobUrl.value) {
    URL.revokeObjectURL(avatarBlobUrl.value)
  }
})

const triggerFileInput = () => {
  if (fileInput.value) {
    fileInput.value.click()
  }
}

const handleFileSelect = async (e) => {
  const file = e.target.files[0]
  if (!file) return

  error.value = null

  // Validate file type
  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    error.value = t('profile.invalidImageType')
    return
  }

  // Validate file size (5MB)
  const maxSize = 5 * 1024 * 1024
  if (file.size > maxSize) {
    error.value = t('profile.imageTooLarge')
    return
  }

  // Create preview
  const reader = new FileReader()
  reader.onload = (e) => {
    previewUrl.value = e.target.result
  }
  reader.readAsDataURL(file)

  // Upload file
  await uploadAvatar(file)
}

const uploadAvatar = async (file) => {
  uploading.value = true
  uploadProgress.value = 0
  error.value = null

  try {
    const formData = new FormData()
    formData.append('file', file)

    const { usersAPI } = await import('../services/api')
    const res = await usersAPI.profile.uploadAvatar(formData)

    if (res.is_success && res.data) {
      uploadProgress.value = 100
      emit('uploaded', res.data.avatar_url)
      // Clear preview after a moment
      setTimeout(() => {
        previewUrl.value = null
      }, 1000)
    } else {
      throw new Error(res.message || t('profile.uploadFailed'))
    }
  } catch (e) {
    error.value = e.message || t('profile.uploadFailed')
    previewUrl.value = null
  } finally {
    uploading.value = false
    uploadProgress.value = 0
    // Reset file input
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  }
}
</script>

<style scoped>
.avatar-upload {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
}

.avatar-preview {
  position: relative;
  width: 120px;
  height: 120px;
  border-radius: var(--radius-full);
  overflow: hidden;
  cursor: pointer;
  border: 3px solid var(--primary);
  transition: all var(--transition-base);
  background: var(--bg-light);
}

.avatar-preview:hover {
  transform: scale(1.05);
  box-shadow: var(--shadow-lg);
}

.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gradient-primary);
  color: white;
}

.avatar-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-xs);
  opacity: 0;
  transition: opacity var(--transition-base);
  color: white;
  font-size: 0.875rem;
  font-weight: 600;
}

.avatar-preview:hover .avatar-overlay {
  opacity: 1;
}

.upload-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-xs);
  width: 100%;
  max-width: 200px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--bg-light);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--gradient-primary);
  transition: width var(--transition-base);
}

.error-message {
  color: var(--error);
  font-size: 0.875rem;
  text-align: center;
}
</style>

