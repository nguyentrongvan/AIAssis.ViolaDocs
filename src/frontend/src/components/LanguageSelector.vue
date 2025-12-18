<template>
  <div class="language-selector">
    <select v-model="currentLang" @change="handleLanguageChange" class="language-select">
      <option value="en">🇬🇧 English</option>
      <option value="vi">🇻🇳 Tiếng Việt</option>
      <option value="ja">🇯🇵 日本語</option>
      <option value="zh">🇨🇳 中文</option>
    </select>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLanguageStore } from '../store/language'

const { locale } = useI18n()
const languageStore = useLanguageStore()

const currentLang = ref(languageStore.currentLanguage)

const handleLanguageChange = () => {
  languageStore.setLanguage(currentLang.value)
  locale.value = currentLang.value
}

// Watch for language changes from store
watch(() => languageStore.currentLanguage, (newLang) => {
  currentLang.value = newLang
  locale.value = newLang
})

onMounted(() => {
  currentLang.value = languageStore.currentLanguage
  locale.value = languageStore.currentLanguage
})
</script>

<style scoped>
.language-selector {
  margin-bottom: var(--space-md);
}

.language-select {
  width: 100%;
  padding: var(--space-md) var(--space-lg);
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-lg);
  color: white;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-base);
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='white' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right var(--space-md) center;
  padding-right: calc(var(--space-xl) + 16px);
}

.language-select:hover {
  background-color: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
}

.language-select:focus {
  outline: none;
  background-color: rgba(255, 255, 255, 0.2);
  border-color: var(--ai-cyan);
  box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.2);
}

.language-select option {
  background: var(--gradient-primary);
  color: white;
  padding: var(--space-md);
}
</style>

