import { defineStore } from 'pinia'
import api from '../services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('access_token') || null
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
    isAdmin: (state) => state.user?.role === 'admin' || state.user?.roles?.includes('admin'),
    isStaff: (state) => state.user?.role === 'staff' || state.user?.roles?.includes('staff')
  },
  actions: {
    async login(email, password) {
      const res = await api.post('/auth/login', { email, password })
      if (res.is_success && res.data) {
        this.token = res.data.access_token
        localStorage.setItem('access_token', res.data.access_token)
        localStorage.setItem('refresh_token', res.data.refresh_token)
        await this.fetchMe()
        return true
      }
      throw new Error(res.message || 'Login failed')
    },
    async fetchMe() {
      try {
        const res = await api.get('/auth/me')
        if (res.is_success) {
          this.user = res.data
        }
      } catch (e) {
        console.error('Failed to fetch user', e)
      }
    },
    logout() {
      this.user = null
      this.token = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
  }
})






