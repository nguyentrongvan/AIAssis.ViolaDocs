import { defineStore } from 'pinia'
import { rolesAPI } from '../services/api'

export const useRolesStore = defineStore('roles', {
  state: () => ({
    roles: [],
    currentRole: null,
    loading: false,
    error: null
  }),
  actions: {
    async fetchRoles() {
      this.loading = true
      this.error = null
      try {
        const res = await rolesAPI.list()
        if (res.is_success) {
          this.roles = res.data || []
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async fetchRole(id) {
      this.loading = true
      this.error = null
      try {
        const res = await rolesAPI.get(id)
        if (res.is_success) {
          this.currentRole = res.data
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async createRole(data) {
      this.loading = true
      this.error = null
      try {
        const res = await rolesAPI.create(data)
        if (res.is_success) {
          this.roles.push(res.data)
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async updateRole(id, data) {
      this.loading = true
      this.error = null
      try {
        const res = await rolesAPI.update(id, data)
        if (res.is_success) {
          const index = this.roles.findIndex(r => r.id === id)
          if (index >= 0) {
            this.roles[index] = res.data
          }
          if (this.currentRole?.id === id) {
            this.currentRole = res.data
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
    async deleteRole(id) {
      this.loading = true
      this.error = null
      try {
        await rolesAPI.delete(id)
        this.roles = this.roles.filter(r => r.id !== id)
        if (this.currentRole?.id === id) {
          this.currentRole = null
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async setPermissions(id, permissions) {
      this.loading = true
      this.error = null
      try {
        const res = await rolesAPI.setPermissions(id, permissions)
        if (res.is_success) {
          if (this.currentRole?.id === id) {
            this.currentRole.permissions = permissions
          }
          const index = this.roles.findIndex(r => r.id === id)
          if (index >= 0) {
            this.roles[index].permissions = permissions
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

