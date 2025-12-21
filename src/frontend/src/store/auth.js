import { defineStore } from 'pinia'
import api from '../services/api'
import { authAPI } from '../services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('access_token') || null,
    has_completed_onboarding: false
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
    isAdmin: (state) => state.user?.role === 'admin' || state.user?.roles?.includes('admin'),
    isStaff: (state) => state.user?.role === 'staff' || state.user?.roles?.includes('staff'),
    isMaintainer: (state) => state.user?.is_maintainer === true,
    // Check if user has a specific permission
    hasPermission: (state) => (permission) => {
      // Admin automatically has all permissions
      if (state.user?.role === 'admin') {
        return true
      }
      // Staff and regular users: check permissions from menu roles
      const permissions = state.user?.permissions || []
      return permissions.includes(permission)
    },
    // Check if user has any of the specified permissions
    hasAnyPermission: (state) => (permissions) => {
      // Admin automatically has all permissions
      if (state.user?.role === 'admin') {
        return true
      }
      // Staff and regular users: check permissions from menu roles
      const userPermissions = state.user?.permissions || []
      return permissions.some(perm => userPermissions.includes(perm))
    }
  },
  actions: {
    async login(email, password) {
      try {
        const res = await authAPI.login(email, password)
        if (res.is_success && res.data) {
          this.token = res.data.access_token
          localStorage.setItem('access_token', res.data.access_token)
          localStorage.setItem('refresh_token', res.data.refresh_token)
          // Set onboarding status from login response if available
          if (res.data.has_completed_onboarding !== undefined) {
            this.has_completed_onboarding = res.data.has_completed_onboarding
          }
          await this.fetchMe()
          return true
        }
        throw new Error(res.message || 'Login failed')
      } catch (error) {
        // Handle axios errors
        if (error.response) {
          const errorData = error.response.data
          throw new Error(errorData?.message || errorData?.data?.error?.message || 'Login failed')
        } else if (error.request) {
          throw new Error('Cannot connect to server. Please check if backend is running.')
        } else {
          throw error
        }
      }
    },
    async fetchMe() {
      try {
        const res = await api.get('/auth/me')
        if (res.is_success) {
          this.user = res.data
          this.has_completed_onboarding = res.data.has_completed_onboarding || false
        }
      } catch (e) {
        console.error('Failed to fetch user', e)
        // If token is invalid, clear it
        if (e.response?.status === 401) {
          this.logout()
        }
      }
    },
    async completeOnboarding() {
      try {
        const res = await authAPI.completeOnboarding()
        if (res.is_success) {
          this.has_completed_onboarding = true
          if (this.user) {
            this.user.has_completed_onboarding = true
          }
        }
      } catch (e) {
        console.error('Failed to complete onboarding', e)
        throw e
      }
    },
    async updateProfile(profileData) {
      try {
        const res = await api.put('/users/me/profile', profileData)
        if (res.is_success && res.data) {
          // Update user data in store
          if (this.user) {
            this.user = {
              ...this.user,
              ...res.data
            }
          }
          return true
        }
        return false
      } catch (e) {
        console.error('Failed to update profile', e)
        throw e
      }
    },
    async changePassword(currentPassword, newPassword, confirmPassword) {
      try {
        const res = await api.put('/users/me/password', {
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword
        })
        if (res.is_success) {
          return true
        }
        return false
      } catch (e) {
        console.error('Failed to change password', e)
        throw e
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






