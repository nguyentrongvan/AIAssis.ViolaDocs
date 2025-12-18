<template>
  <div class="language-selector" @click.stop>
    <div 
      class="language-trigger" 
      :class="{ 'is-open': isOpen }"
      @click="toggleDropdown"
    >
      <span class="language-name">{{ getCurrentLanguage().name }}</span>
      <div class="language-code">{{ getCurrentLanguage().code }}</div>
      <svg 
        class="dropdown-icon" 
        :class="{ 'rotated': isOpen }"
        width="16" 
        height="16" 
        viewBox="0 0 16 16" 
        fill="none"
      >
        <path 
          d="M4 6L8 10L12 6" 
          stroke="currentColor" 
          stroke-width="2" 
          stroke-linecap="round" 
          stroke-linejoin="round"
        />
      </svg>
    </div>
    
    <Transition name="dropdown">
      <div v-if="isOpen" class="language-dropdown">
        <div 
          v-for="lang in languages" 
          :key="lang.value"
          class="language-option"
          :class="{ 'is-selected': currentLang === lang.value }"
          @click="selectLanguage(lang.value)"
        >
          <span class="language-name">{{ lang.name }}</span>
          <div class="language-code">{{ lang.code }}</div>
          <div v-if="currentLang === lang.value" class="selected-indicator">
            <svg 
              class="check-icon"
              width="14" 
              height="14" 
              viewBox="0 0 14 14" 
              fill="none"
            >
              <path 
                d="M11.6667 3.5L5.25 9.91667L2.33333 7" 
                stroke="currentColor" 
                stroke-width="2" 
                stroke-linecap="round" 
                stroke-linejoin="round"
              />
            </svg>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLanguageStore } from '../store/language'

const { locale } = useI18n()
const languageStore = useLanguageStore()

const currentLang = ref(languageStore.currentLanguage)
const isOpen = ref(false)

const languages = [
  { value: 'en', name: 'English', code: 'EN' },
  { value: 'vi', name: 'Tiếng Việt', code: 'VI' },
  { value: 'ja', name: '日本語', code: 'JA' },
  { value: 'zh', name: '中文', code: 'ZH' }
]

const getCurrentLanguage = () => {
  return languages.find(lang => lang.value === currentLang.value) || languages[0]
}

const toggleDropdown = () => {
  isOpen.value = !isOpen.value
}

const selectLanguage = (langValue) => {
  currentLang.value = langValue
  languageStore.setLanguage(langValue)
  locale.value = langValue
  isOpen.value = false
}

const closeDropdown = (event) => {
  if (!event.target.closest('.language-selector')) {
    isOpen.value = false
  }
}

// Watch for language changes from store
watch(() => languageStore.currentLanguage, (newLang) => {
  currentLang.value = newLang
  locale.value = newLang
})

onMounted(() => {
  currentLang.value = languageStore.currentLanguage
  locale.value = languageStore.currentLanguage
  document.addEventListener('click', closeDropdown)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeDropdown)
})
</script>

<style scoped>
.language-selector {
  position: relative;
  margin-bottom: var(--space-lg);
  z-index: var(--z-dropdown);
}

.language-trigger {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  width: 100%;
  padding: var(--space-md) var(--space-lg);
  background: linear-gradient(135deg, rgba(62, 47, 166, 0.35) 0%, rgba(0, 217, 255, 0.2) 100%);
  backdrop-filter: var(--backdrop-blur);
  border: 2px solid rgba(0, 217, 255, 0.4);
  border-radius: var(--radius-lg);
  color: white;
  cursor: pointer;
  transition: all var(--transition-base);
  user-select: none;
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.language-trigger::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.2), transparent);
  transition: left var(--transition-slow);
}

.language-trigger:hover::before {
  left: 100%;
}

.language-trigger:hover {
  background: linear-gradient(135deg, rgba(62, 47, 166, 0.45) 0%, rgba(0, 217, 255, 0.3) 100%);
  border-color: rgba(0, 217, 255, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 217, 255, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.language-trigger.is-open {
  background: linear-gradient(135deg, rgba(62, 47, 166, 0.5) 0%, rgba(0, 217, 255, 0.35) 100%);
  border-color: var(--ai-cyan);
  box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.4), 0 8px 24px rgba(0, 217, 255, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.25);
}

.language-name {
  flex: 1;
  text-align: left;
  font-size: 0.9rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: 0.01em;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.language-code {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 4px 8px;
  background: rgba(0, 217, 255, 0.3);
  border: 1px solid rgba(0, 217, 255, 0.4);
  border-radius: 6px;
  color: var(--ai-cyan);
  letter-spacing: 0.05em;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 217, 255, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2);
  text-shadow: 0 0 8px rgba(0, 217, 255, 0.5);
}

.dropdown-icon {
  flex-shrink: 0;
  color: rgba(255, 255, 255, 0.9);
  transition: transform var(--transition-base);
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
}

.dropdown-icon.rotated {
  transform: rotate(180deg);
}

.language-dropdown {
  position: absolute;
  top: calc(100% + var(--space-xs));
  left: 0;
  right: 0;
  background: linear-gradient(135deg, rgba(26, 26, 46, 0.98) 0%, rgba(30, 30, 60, 0.98) 100%);
  backdrop-filter: var(--backdrop-blur-strong);
  border: 1px solid rgba(0, 217, 255, 0.2);
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(0, 217, 255, 0.1);
  overflow: hidden;
  z-index: var(--z-dropdown);
}

.language-option {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-lg);
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  position: relative;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.language-option:last-child {
  border-bottom: none;
}

.language-option::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--ai-cyan);
  transform: scaleY(0);
  transition: transform var(--transition-base);
}

.language-option:hover {
  background: linear-gradient(90deg, rgba(0, 217, 255, 0.1) 0%, transparent 100%);
  color: white;
  padding-left: calc(var(--space-lg) + 4px);
}

.language-option:hover::before {
  transform: scaleY(1);
}

.language-option.is-selected {
  background: linear-gradient(90deg, rgba(0, 217, 255, 0.15) 0%, rgba(108, 92, 231, 0.1) 100%);
  color: var(--ai-cyan);
  padding-left: calc(var(--space-lg) + 4px);
}

.language-option.is-selected::before {
  transform: scaleY(1);
}

.language-option.is-selected .language-name {
  font-weight: 600;
}

.language-option.is-selected .language-code {
  background: rgba(0, 217, 255, 0.3);
  color: var(--ai-cyan);
  box-shadow: 0 0 8px rgba(0, 217, 255, 0.3);
}

.language-option .language-name {
  flex: 1;
  text-align: left;
  letter-spacing: 0.01em;
}

.language-option .language-code {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 0.05em;
  flex-shrink: 0;
  transition: all var(--transition-fast);
}

.language-option:hover .language-code {
  background: rgba(0, 217, 255, 0.2);
  color: var(--ai-cyan);
}

.selected-indicator {
  margin-left: auto;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: rgba(0, 217, 255, 0.2);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.check-icon {
  color: var(--ai-cyan);
  filter: drop-shadow(0 0 4px rgba(0, 217, 255, 0.5));
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(0, 217, 255, 0.4);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(0, 217, 255, 0);
  }
}

/* Dropdown animation */
.dropdown-enter-active {
  transition: all var(--transition-base);
}

.dropdown-leave-active {
  transition: all var(--transition-fast);
}

.dropdown-enter-from {
  opacity: 0;
  transform: translateY(-8px) scale(0.95);
}

.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.95);
}

.dropdown-enter-to,
.dropdown-leave-from {
  opacity: 1;
  transform: translateY(0) scale(1);
}
</style>

