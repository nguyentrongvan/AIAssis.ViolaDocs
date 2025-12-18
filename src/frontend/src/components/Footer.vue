<template>
  <footer :class="['app-footer', { 'footer-fixed': fixed }]">
    <div class="footer-gradient"></div>
    <div class="footer-content">
      <p class="copyright">
        {{ $t('footer.copyright', { year: currentYear }) }}
      </p>
      <div class="footer-divider"></div>
      <span class="version">
        <span class="version-label">{{ $t('footer.version') }}</span>
        <span class="version-number">1.0.0</span>
      </span>
    </div>
  </footer>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  fixed: {
    type: Boolean,
    default: false
  }
})

const currentYear = computed(() => new Date().getFullYear())
</script>

<style scoped>
.app-footer {
  position: relative;
  width: 100%;
  height: 72px;
  background: linear-gradient(135deg, 
    rgba(255, 255, 255, 0.95) 0%, 
    rgba(250, 250, 255, 0.92) 50%,
    rgba(255, 255, 255, 0.95) 100%);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-top: 1px solid rgba(62, 47, 166, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  box-shadow: 
    0 -8px 32px rgba(0, 0, 0, 0.04),
    0 -2px 8px rgba(62, 47, 166, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  margin-top: auto;
  overflow: hidden;
  opacity: 0.92;
}

.app-footer.footer-fixed {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 100;
  margin-top: 0;
}

.footer-gradient {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, 
    transparent,
    rgba(62, 47, 166, 0.25),
    rgba(0, 217, 255, 0.35),
    rgba(62, 47, 166, 0.25),
    transparent);
  z-index: 0;
  opacity: 0.7;
}

.footer-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-xl);
  width: 100%;
  max-width: 1400px;
  padding: 0 var(--space-2xl);
  position: relative;
  z-index: 1;
}

.copyright {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  color: var(--text-dark);
  font-size: 0.9rem;
  font-weight: 500;
  letter-spacing: -0.01em;
  margin: 0;
  opacity: 0.75;
}

.footer-divider {
  width: 1px;
  height: 24px;
  background: linear-gradient(180deg, 
    transparent 0%,
    rgba(62, 47, 166, 0.12) 20%,
    rgba(62, 47, 166, 0.2) 50%,
    rgba(62, 47, 166, 0.12) 80%,
    transparent 100%);
  flex-shrink: 0;
  opacity: 0.6;
}

.version {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 0.9rem;
}

.version-label {
  font-weight: 500;
  color: var(--text-dark);
  letter-spacing: -0.01em;
  opacity: 0.75;
}

.version-number {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 0.85rem;
  color: white;
  background: var(--gradient-primary);
  padding: 6px 14px;
  border-radius: var(--radius-lg);
  box-shadow: 
    0 4px 12px rgba(62, 47, 166, 0.25),
    0 2px 4px rgba(62, 47, 166, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  letter-spacing: 0.5px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  opacity: 0.9;
}

/* Responsive */
@media (max-width: 768px) {
  .app-footer {
    height: 64px;
  }

  .footer-content {
    flex-direction: column;
    gap: var(--space-sm);
    padding: var(--space-md) var(--space-lg);
  }

  .footer-divider {
    display: none;
  }

  .copyright,
  .version {
    font-size: 0.8rem;
  }

  .version-number {
    font-size: 0.75rem;
    padding: 5px 12px;
  }
}

@media (max-width: 480px) {
  .app-footer {
    height: 60px;
  }

  .footer-content {
    gap: var(--space-xs);
    padding: var(--space-sm) var(--space-md);
  }

  .copyright,
  .version {
    font-size: 0.75rem;
  }

  .version-number {
    font-size: 0.7rem;
    padding: 4px 10px;
  }
}
</style>

