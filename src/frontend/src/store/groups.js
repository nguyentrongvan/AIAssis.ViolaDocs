import { defineStore } from 'pinia'
import { groupsAPI } from '../services/api'

export const useGroupsStore = defineStore('groups', {
  state: () => ({
    groups: [],
    currentGroup: null,
    loading: false,
    error: null
  }),
  actions: {
    async fetchGroups(params = {}) {
      this.loading = true
      this.error = null
      try {
        const res = await groupsAPI.list(params)
        if (res.is_success) {
          this.groups = res.data || []
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async fetchGroup(id) {
      this.loading = true
      this.error = null
      try {
        const res = await groupsAPI.get(id)
        if (res.is_success) {
          this.currentGroup = res.data
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async createGroup(data) {
      this.loading = true
      this.error = null
      try {
        const res = await groupsAPI.create(data)
        if (res.is_success) {
          this.groups.push(res.data)
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async updateGroup(id, data) {
      this.loading = true
      this.error = null
      try {
        const res = await groupsAPI.update(id, data)
        if (res.is_success) {
          const index = this.groups.findIndex(g => g.id === id)
          if (index >= 0) {
            this.groups[index] = res.data
          }
          if (this.currentGroup?.id === id) {
            this.currentGroup = res.data
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
    async deleteGroup(id) {
      this.loading = true
      this.error = null
      try {
        await groupsAPI.delete(id)
        this.groups = this.groups.filter(g => g.id !== id)
        if (this.currentGroup?.id === id) {
          this.currentGroup = null
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async reindexGroup(id) {
      this.loading = true
      this.error = null
      try {
        const res = await groupsAPI.reindex(id)
        if (res.is_success) {
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

