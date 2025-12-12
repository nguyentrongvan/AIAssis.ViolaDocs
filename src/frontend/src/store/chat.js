import { defineStore } from 'pinia'
import { chatAPI } from '../services/api'

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [],
    currentSession: null,
    messages: [],
    loading: false,
    error: null
  }),
  actions: {
    async sendMessage(data) {
      this.loading = true
      this.error = null
      try {
        const res = await chatAPI.chat(data)
        if (res.is_success) {
          const message = {
            role: 'user',
            content: data.message,
            timestamp: new Date().toISOString()
          }
          const response = {
            role: 'assistant',
            content: res.data.answer,
            citations: res.data.citations || [],
            timestamp: new Date().toISOString()
          }
          this.messages.push(message, response)
          if (res.data.session_id) {
            this.currentSession = res.data.session_id
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
    async fetchHistory(params = {}) {
      this.loading = true
      this.error = null
      try {
        const res = await chatAPI.history(params)
        if (res.is_success) {
          this.sessions = res.data || []
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async fetchSession(sessionId) {
      this.loading = true
      this.error = null
      try {
        const res = await chatAPI.session(sessionId)
        if (res.is_success) {
          this.currentSession = sessionId
          this.messages = res.data.messages || []
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async submitFeedback(sessionId, data) {
      try {
        const res = await chatAPI.feedback(sessionId, data)
        if (res.is_success) {
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },
    async handoff(sessionId, data) {
      try {
        const res = await chatAPI.handoff(sessionId, data)
        if (res.is_success) {
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },
    clearMessages() {
      this.messages = []
      this.currentSession = null
    }
  }
})

