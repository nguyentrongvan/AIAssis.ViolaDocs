import { defineStore } from 'pinia'
import { documentsAPI } from '../services/api'

export const useDocumentsStore = defineStore('documents', {
  state: () => ({
    documents: [],
    currentDocument: null,
    versions: [],
    comments: [],
    loading: false,
    error: null,
    pagination: {
      page: 1,
      size: 20,
      total: 0
    }
  }),
  getters: {
    hasMore: (state) => {
      return state.pagination.page * state.pagination.size < state.pagination.total
    }
  },
  actions: {
    async fetchDocuments(params = {}) {
      this.loading = true
      this.error = null
      try {
        const res = await documentsAPI.list(params)
        if (res.is_success) {
          this.documents = res.data?.items || res.data || []
          if (res.data?.pagination) {
            this.pagination = { ...this.pagination, ...res.data.pagination }
          }
        }
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async fetchDocument(id) {
      this.loading = true
      this.error = null
      try {
        const res = await documentsAPI.get(id)
        if (res.is_success) {
          this.currentDocument = res.data
          this.versions = res.data.versions || []
          // Store preview URL if available
          if (res.data.preview_url) {
            this.currentDocument.preview_url = res.data.preview_url
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
    async fetchVersions(id) {
      try {
        const res = await documentsAPI.versions(id)
        if (res.is_success) {
          this.versions = res.data || []
          return this.versions
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },
    async fetchComments(id) {
      try {
        const res = await documentsAPI.comments(id)
        if (res.is_success) {
          this.comments = res.data || []
          return this.comments
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },
    async createComment(id, data) {
      try {
        const res = await documentsAPI.createComment(id, data)
        if (res.is_success) {
          this.comments.push(res.data)
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },
    async updateComment(id, commentId, data) {
      try {
        const res = await documentsAPI.updateComment(id, commentId, data)
        if (res.is_success) {
          const index = this.comments.findIndex(c => c.id === commentId)
          if (index >= 0) {
            this.comments[index] = res.data
          }
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },
    async deleteComment(id, commentId) {
      try {
        await documentsAPI.deleteComment(id, commentId)
        this.comments = this.comments.filter(c => c.id !== commentId)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },
    async compareVersions(id, v1, v2) {
      try {
        const res = await documentsAPI.compareVersions(id, v1, v2)
        if (res.is_success) {
          return res.data
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },
    async updateDocument(id, data) {
      this.loading = true
      this.error = null
      try {
        const res = await documentsAPI.update(id, data)
        if (res.is_success) {
          if (this.currentDocument?.id === id) {
            this.currentDocument = { ...this.currentDocument, ...res.data }
          }
          const index = this.documents.findIndex(d => d.id === id)
          if (index >= 0) {
            this.documents[index] = { ...this.documents[index], ...res.data }
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
    async deleteDocument(id) {
      this.loading = true
      this.error = null
      try {
        await documentsAPI.delete(id)
        this.documents = this.documents.filter(d => d.id !== id)
        if (this.currentDocument?.id === id) {
          this.currentDocument = null
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

