<template>
  <div class="loading-spinner" :class="{ 'spinner-small': size === 'small', 'spinner-large': size === 'large' }">
    <div class="spinner-ring"></div>
    <div class="spinner-ring"></div>
    <div class="spinner-ring"></div>
    <div v-if="text" class="spinner-text">{{ text }}</div>
  </div>
</template>

<script setup>
defineProps({
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  },
  text: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-lg);
  padding: var(--space-xl);
}

.spinner-ring {
  width: 60px;
  height: 60px;
  border: 4px solid rgba(0, 217, 255, 0.2);
  border-top-color: var(--ai-cyan);
  border-right-color: var(--primary);
  border-radius: var(--radius-full);
  animation: spin 1s linear infinite;
  position: absolute;
}

.spinner-ring:nth-child(2) {
  width: 50px;
  height: 50px;
  border-top-color: var(--primary);
  border-right-color: var(--ai-pink);
  animation-duration: 0.8s;
  animation-direction: reverse;
}

.spinner-ring:nth-child(3) {
  width: 40px;
  height: 40px;
  border-top-color: var(--ai-pink);
  border-right-color: var(--ai-cyan);
  animation-duration: 0.6s;
}

.spinner-small .spinner-ring {
  width: 30px;
  height: 30px;
  border-width: 3px;
}

.spinner-small .spinner-ring:nth-child(2) {
  width: 25px;
  height: 25px;
}

.spinner-small .spinner-ring:nth-child(3) {
  width: 20px;
  height: 20px;
}

.spinner-large .spinner-ring {
  width: 80px;
  height: 80px;
  border-width: 5px;
}

.spinner-large .spinner-ring:nth-child(2) {
  width: 70px;
  height: 70px;
}

.spinner-large .spinner-ring:nth-child(3) {
  width: 60px;
  height: 60px;
}

.spinner-text {
  font-size: 0.9rem;
  color: var(--text-medium);
  font-weight: 500;
  margin-top: var(--space-md);
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>

