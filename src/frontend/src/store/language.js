import { defineStore } from 'pinia'

export const useLanguageStore = defineStore('language', {
  state: () => ({
    currentLanguage: localStorage.getItem('language') || 'en'
  }),
  getters: {
    locale: (state) => state.currentLanguage
  },
  actions: {
    setLanguage(lang) {
      this.currentLanguage = lang
      localStorage.setItem('language', lang)
    }
  }
})


