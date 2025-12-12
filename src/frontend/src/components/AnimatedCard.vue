<template>
  <div 
    :class="['animated-card', { 'card-hover': hover }]"
    :style="{ animationDelay: `${delay}ms` }"
    @mouseenter="hover = true"
    @mouseleave="hover = false"
  >
    <div class="card-glow"></div>
    <div class="card-content">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  delay: {
    type: Number,
    default: 0
  }
})

const hover = ref(false)
</script>

<style scoped>
.animated-card {
  position: relative;
  background: var(--bg-white);
  border-radius: var(--radius-xl);
  padding: var(--space-xl);
  box-shadow: var(--shadow-lg);
  border: 2px solid transparent;
  transition: all var(--transition-base);
  overflow: hidden;
  animation: fadeInUp var(--transition-base) var(--ease-out) both;
}

.animated-card::before {
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

.card-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(0, 217, 255, 0.2) 0%, transparent 70%);
  transform: translate(-50%, -50%);
  opacity: 0;
  transition: opacity var(--transition-base);
  pointer-events: none;
}

.card-hover::before {
  transform: scaleX(1);
}

.card-hover .card-glow {
  opacity: 1;
}

.card-hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: var(--shadow-2xl), var(--shadow-glow-cyan);
  border-color: var(--ai-cyan);
}

.card-content {
  position: relative;
  z-index: 1;
}
</style>

