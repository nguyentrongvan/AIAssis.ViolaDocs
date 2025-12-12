import { defineStore } from 'pinia'
import { foldersAPI } from '../services/api'

export const useFoldersStore = defineStore('folders', {
  state: () => ({
    folders: [],
    currentFolder: null,
    loading: false,
    error: null
  }),
  getters: {
    folderTree: (state) => {
      // Build hierarchical tree from flat list
      if (!state.folders || !Array.isArray(state.folders) || state.folders.length === 0) {
        return []
      }
      
      const folderMap = new Map()
      const roots = []
      
      state.folders.forEach(folder => {
        folderMap.set(folder.id, { ...folder, children: [] })
      })
      
      state.folders.forEach(folder => {
        const node = folderMap.get(folder.id)
        if (folder.parent_id && folderMap.has(folder.parent_id)) {
          folderMap.get(folder.parent_id).children.push(node)
        } else {
          roots.push(node)
        }
      })
      
      return roots
    },
    getFolderById: (state) => (id) => {
      return state.folders.find(f => f.id === id)
    }
  },
  actions: {
    async fetchFolders(params = {}) {
      this.loading = true
      this.error = null
      try {
        const res = await foldersAPI.list(params)
        if (res.is_success) {
          this.folders = res.data || []
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async fetchFolder(id) {
      this.loading = true
      this.error = null
      try {
        const res = await foldersAPI.get(id)
        if (res.is_success) {
          this.currentFolder = res.data
          // Update in folders list if exists
          const index = this.folders.findIndex(f => f.id === id)
          if (index >= 0) {
            this.folders[index] = res.data
          } else {
            this.folders.push(res.data)
          }
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async createFolder(data) {
      this.loading = true
      this.error = null
      try {
        const res = await foldersAPI.create(data)
        if (res.is_success) {
          this.folders.push(res.data)
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async updateFolder(id, data) {
      this.loading = true
      this.error = null
      try {
        const res = await foldersAPI.update(id, data)
        if (res.is_success) {
          const index = this.folders.findIndex(f => f.id === id)
          if (index >= 0) {
            this.folders[index] = res.data
          }
          if (this.currentFolder?.id === id) {
            this.currentFolder = res.data
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
    async deleteFolder(id) {
      this.loading = true
      this.error = null
      try {
        await foldersAPI.delete(id)
        this.folders = this.folders.filter(f => f.id !== id)
        if (this.currentFolder?.id === id) {
          this.currentFolder = null
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

