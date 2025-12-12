import { defineStore } from 'pinia'
import { settingsAPI } from '../services/api'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    retentionPolicies: [],
    providers: null,
    chatbotPolicies: [],
    loading: false,
    error: null
  }),
  actions: {
    async fetchRetentionPolicies() {
      this.loading = true
      this.error = null
      try {
        const res = await settingsAPI.retention.list()
        if (res.is_success) {
          this.retentionPolicies = res.data || []
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async createRetentionPolicy(data) {
      this.loading = true
      this.error = null
      try {
        const res = await settingsAPI.retention.create(data)
        if (res.is_success) {
          this.retentionPolicies.push(res.data)
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async updateRetentionPolicy(id, data) {
      this.loading = true
      this.error = null
      try {
        const res = await settingsAPI.retention.update(id, data)
        if (res.is_success) {
          const index = this.retentionPolicies.findIndex(p => p.id === id)
          if (index >= 0) {
            this.retentionPolicies[index] = res.data
          }
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async deleteRetentionPolicy(id) {
      this.loading = true
      this.error = null
      try {
        await settingsAPI.retention.delete(id)
        this.retentionPolicies = this.retentionPolicies.filter(p => p.id !== id)
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async fetchProviders() {
      this.loading = true
      this.error = null
      try {
        const res = await settingsAPI.providers.get()
        if (res.is_success) {
          this.providers = res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async updateProviders(data) {
      this.loading = true
      this.error = null
      try {
        const res = await settingsAPI.providers.update(data)
        if (res.is_success) {
          this.providers = res.data
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async fetchChatbotPolicies() {
      this.loading = true
      this.error = null
      try {
        const res = await settingsAPI.chatbot.list()
        if (res.is_success) {
          this.chatbotPolicies = res.data || []
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async updateChatbotPolicy(data) {
      this.loading = true
      this.error = null
      try {
        const res = await settingsAPI.chatbot.update(data)
        if (res.is_success) {
          const index = this.chatbotPolicies.findIndex(p => p.group_id === data.group_id)
          if (index >= 0) {
            this.chatbotPolicies[index] = res.data
          } else {
            this.chatbotPolicies.push(res.data)
          }
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})

