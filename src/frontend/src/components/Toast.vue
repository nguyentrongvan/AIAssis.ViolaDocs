<template>
  <Teleport to="body">
    <TransitionGroup name="toast" tag="div" class="toast-container">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="['toast', `toast-${toast.type}`]"
      >
        <div class="toast-content">
          <component v-if="toast.icon" :is="toast.icon" :size="20" />
          <span>{{ toast.message }}</span>
        </div>
        <button @click="remove(toast.id)" class="toast-close">
          <X :size="16" />
        </button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { X, CheckCircle, XCircle, AlertCircle, Info } from 'lucide-vue-next'

const toasts = ref([])

const icons = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertCircle,
  info: Info
}

const show = (message, type = 'info', duration = 5000) => {
  const id = Date.now()
  const toast = {
    id,
    message,
    type,
    icon: icons[type]
  }
  toasts.value.push(toast)
  
  if (duration > 0) {
    setTimeout(() => {
      remove(id)
    }, duration)
  }
  
  return id
}

const remove = (id) => {
  const index = toasts.value.findIndex(t => t.id === id)
  if (index >= 0) {
    toasts.value.splice(index, 1)
  }
}

const clear = () => {
  toasts.value = []
}

// Expose methods globally
onMounted(() => {
  window.$toast = { show, remove, clear }
})

defineExpose({ show, remove, clear })
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  pointer-events: none;
}

.toast {
  background: white;
  border-radius: 8px;
  padding: 1rem 1.25rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-width: 300px;
  max-width: 500px;
  pointer-events: auto;
  border-left: 4px solid;
}

.toast-success {
  border-left-color: #10b981;
}

.toast-error {
  border-left-color: #ef4444;
}

.toast-warning {
  border-left-color: #f59e0b;
}

.toast-info {
  border-left-color: #3b82f6;
}

.toast-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.toast-close {
  background: none;
  border: none;
  cursor: pointer;
  color: #666;
  padding: 0.25rem;
  display: flex;
  align-items: center;
  border-radius: 4px;
  transition: background 0.2s;
}

.toast-close:hover {
  background: #f0f0f0;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>

