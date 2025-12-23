import { defineStore } from 'pinia'
import { usersAPI } from '../services/api'
import { applyPreferences, calculateThemeColors, applyThemeColors } from '../utils/theme'

export const usePreferencesStore = defineStore('preferences', {
  state: () => ({
    preferences: {
      primary_color: null,
      font_size: 'medium',
      border_radius: 'medium',
      animation_speed: 'normal',
      compact_mode: false
    },
    loaded: false
  }),

  getters: {
    themeColors: (state) => {
      if (state.preferences.primary_color) {
        return calculateThemeColors(state.preferences.primary_color)
      }
      return {}
    }
  },

  actions: {
    async fetchPreferences() {
      try {
        const res = await usersAPI.preferences.get()
        if (res.is_success && res.data) {
          this.preferences = {
            primary_color: res.data.primary_color || null,
            font_size: res.data.font_size || 'medium',
            border_radius: res.data.border_radius || 'medium',
            animation_speed: res.data.animation_speed || 'normal',
            compact_mode: res.data.compact_mode || false
          }
          this.loaded = true
          // Apply preferences immediately
          this.applyTheme()
          // Cache in localStorage
          localStorage.setItem('user_preferences', JSON.stringify(this.preferences))
        }
      } catch (e) {
        console.error('Failed to fetch preferences', e)
        // Try to load from cache
        const cached = localStorage.getItem('user_preferences')
        if (cached) {
          try {
            this.preferences = JSON.parse(cached)
            this.applyTheme()
          } catch (err) {
            console.error('Failed to parse cached preferences', err)
          }
        }
      }
    },

    async updatePreferences(newPreferences) {
      try {
        const res = await usersAPI.preferences.update(newPreferences)
        if (res.is_success && res.data) {
          this.preferences = {
            ...this.preferences,
            ...res.data
          }
          // Apply theme immediately
          this.applyTheme()
          // Cache in localStorage
          localStorage.setItem('user_preferences', JSON.stringify(this.preferences))
          return true
        }
        return false
      } catch (e) {
        console.error('Failed to update preferences', e)
        throw e
      }
    },

    applyTheme() {
      applyPreferences(this.preferences)
    },

    resetTheme() {
      // Reset all CSS variables to defaults
      const root = document.documentElement
      const defaultVars = [
        '--primary',
        '--primary-dark',
        '--primary-light',
        '--gradient-start',
        '--gradient-end',
        '--gradient-primary',
        '--gradient-cyan-purple',
        '--gradient-purple-pink',
        '--gradient-ai',
        '--gradient-ai-soft',
        '--font-size-base',
        '--space-xs',
        '--space-sm',
        '--space-md',
        '--space-lg',
        '--space-xl',
        '--space-2xl',
        '--space-3xl',
        '--radius-sm',
        '--radius-md',
        '--radius-lg',
        '--radius-xl',
        '--radius-2xl',
        '--transition-fast',
        '--transition-base',
        '--transition-slow'
      ]
      
      defaultVars.forEach(varName => {
        root.style.removeProperty(varName)
      })
      
      // Reset body font size
      document.body.style.fontSize = ''
    }
  }
})

