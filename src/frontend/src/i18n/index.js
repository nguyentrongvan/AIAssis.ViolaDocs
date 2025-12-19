import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import vi from './locales/vi.json'
import ja from './locales/ja.json'
import zh from './locales/zh.json'

// Get language from localStorage or default to 'en'
const getDefaultLocale = () => {
  try {
    return localStorage.getItem('language') || 'en'
  } catch (e) {
    return 'en'
  }
}

const i18n = createI18n({
  legacy: false,
  locale: getDefaultLocale(),
  fallbackLocale: 'en',
  messages: {
    en,
    vi,
    ja,
    zh
  },
  globalInjection: true
})

export default i18n

