<template>
  <div class="chatbot-page">
    <div class="particles-background"></div>
    <h1 class="page-header">
      <span class="gradient-text">Chatbot Assistant</span>
    </h1>

    <div class="chat-container">
      <div class="chat-sidebar glass">
        <div class="sidebar-section">
          <h3>Document Groups</h3>
          <div class="group-selector">
            <select v-model="selectedGroup" @change="onGroupChange">
              <option value="">All Documents</option>
              <option
                v-for="group in accessibleGroups"
                :key="group.id"
                :value="group.id"
              >
                {{ group.name }}
              </option>
            </select>
          </div>
        </div>

        <div class="sidebar-section">
          <h3>Filters</h3>
          <div class="filter-group">
            <label>Tags</label>
            <input
              v-model="tagFilter"
              @keyup.enter="addTagFilter"
              placeholder="Press Enter to add"
            />
            <div class="selected-tags">
              <span
                v-for="tag in filters.tags"
                :key="tag"
                class="tag-badge"
              >
                {{ tag }}
                <button @click="removeTagFilter(tag)" class="tag-remove">×</button>
              </span>
            </div>
          </div>
          <div class="filter-group">
            <label>Type</label>
            <select v-model="filters.type">
              <option value="">All Types</option>
              <option value="application/pdf">PDF</option>
              <option value="application/vnd.openxmlformats-officedocument.wordprocessingml.document">DOCX</option>
              <option value="image/">Images</option>
            </select>
          </div>
          <div class="filter-group">
            <label>Date From</label>
            <input v-model="filters.date_from" type="date" />
          </div>
          <div class="filter-group">
            <label>Date To</label>
            <input v-model="filters.date_to" type="date" />
          </div>
        </div>

        <div class="sidebar-section">
          <h3>Source Documents</h3>
          <div class="source-documents">
            <div class="document-search-wrapper">
              <div class="document-search-input">
                <Search :size="16" class="search-icon" />
                <input
                  type="text"
                  v-model="documentSearchTerm"
                  placeholder="Search documents..."
                  class="document-search"
                />
                <button
                  v-if="documentSearchTerm"
                  @click="documentSearchTerm = ''"
                  class="search-clear-btn"
                  title="Clear search"
                >
                  <X :size="14" />
                </button>
              </div>
              <div v-if="documentSearchTerm" class="search-results-info">
                {{ filteredDocuments.length }} of {{ availableDocuments.length }} documents
              </div>
            </div>
            <div class="select-all-control">
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  v-model="selectAllDocuments"
                  @change="onSelectAllChange"
                />
                <span>Select All</span>
              </label>
            </div>
            <div class="source-documents-list" v-if="filteredDocuments.length > 0">
              <div
                v-for="doc in filteredDocuments"
                :key="doc.id"
                class="source-document-item"
              >
                <label class="checkbox-label">
                  <input
                    type="checkbox"
                    :value="doc.id"
                    v-model="selectedDocumentIds"
                    @change="onDocumentSelectionChange"
                  />
                  <div class="document-info">
                    <div class="document-title">{{ doc.title }}</div>
                    <div class="document-meta">
                      <span class="document-type">{{ doc.mime }}</span>
                      <span 
                        v-if="!doc.has_embedding" 
                        class="no-embedding-badge"
                        title="Document is not indexed. Vector search will not be used but the document can still be used."
                      >
                        <AlertTriangle :size="12" />
                        Not indexed
                      </span>
                    </div>
                  </div>
                </label>
              </div>
            </div>
            <div v-else-if="loadingDocuments" class="loading-documents">
              Loading documents...
            </div>
            <div v-else-if="documentSearchTerm && filteredDocuments.length === 0" class="empty-documents">
              <div>No documents found matching "{{ documentSearchTerm }}"</div>
              <div style="font-size: 0.8rem; margin-top: 0.5rem; color: #999;">
                Try a different search term
              </div>
            </div>
            <div v-else class="empty-documents">
              <div>No documents available</div>
              <div style="font-size: 0.8rem; margin-top: 0.5rem; color: #999;">
                Total: {{ availableDocuments.length }} documents
              </div>
            </div>
          </div>
        </div>

        <div class="sidebar-section">
          <h3>Chat History</h3>
          <div class="chat-history">
            <div
              v-for="session in sessions"
              :key="session.session_id || session.id"
              class="session-item"
              :class="{ active: currentSessionId === (session.session_id || session.id) }"
              @click="loadSession(session.session_id || session.id)"
            >
              <div class="session-title">
                {{ session.title || `Chat ${(session.session_id || session.id || '').slice(0, 8)}` }}
              </div>
              <div class="session-date">
                {{ formatDate(session.created_at) }}
              </div>
            </div>
            <div v-if="sessions.length === 0" class="empty-sessions">
              No previous chats
            </div>
          </div>
        </div>
      </div>

      <div class="chat-main">
        <div class="chat-header">
          <div class="session-info">
            <span v-if="currentSessionId" class="session-indicator">
              <Circle :size="8" />
              Active Session
            </span>
            <span v-else class="session-indicator new">
              <Circle :size="8" />
              New Session
            </span>
          </div>
          <div class="chat-actions">
            <button @click="clearChat" class="btn-small">
              <Trash2 :size="16" />
              Clear
            </button>
            <button @click="showHandoffModal = true" class="btn-small">
              <User :size="16" />
              Handoff
            </button>
          </div>
        </div>

        <div class="messages" ref="messagesContainer">
          <div v-if="messages.length === 0" class="welcome-message">
            <div class="welcome-icon-wrapper">
              <img src="/chatbot.png" alt="Chatbot" class="welcome-icon" />
              <div class="welcome-glow"></div>
            </div>
            <h3 class="gradient-text">Ask me anything about your documents</h3>
            <p>Select a document group and start asking questions</p>
          </div>
          <transition-group name="message" tag="div">
            <div
              v-for="(msg, idx) in messages"
              :key="msg.id || idx"
              :class="['message', msg.role]"
            >
              <div class="message-avatar">
                <div v-if="msg.role === 'user'" class="avatar-circle user-avatar">
                  <User :size="20" />
                </div>
                <div v-else class="avatar-circle ai-avatar">
                  <img src="/chatbot.png" alt="Chatbot" class="avatar-image" />
                  <div class="avatar-pulse"></div>
                </div>
              </div>
              <div class="message-content">
              <div class="message-text" v-html="formatMessage(msg.content)"></div>
              <div v-if="msg.response_time !== undefined" class="message-response-time">
                <Clock :size="12" />
                <span>{{ formatResponseTime(msg.response_time) }}</span>
              </div>
              <div v-if="msg.citations && msg.citations.length > 0" class="citations">
                <div class="citations-header">Sources:</div>
                <div
                  v-for="(cite, citeIdx) in msg.citations"
                  :key="citeIdx"
                  class="citation"
                >
                  <a
                    @click.prevent="viewDocument(cite.document_id || cite.doc_id)"
                    class="citation-link"
                  >
                    <FileText :size="14" />
                    {{ cite.title || cite.doc_title || `Document ${cite.document_id || cite.doc_id}` }}
                  </a>
                  <span v-if="cite.score" class="citation-score">
                    ({{ (cite.score * 100).toFixed(0) }}% match)
                  </span>
                  <div v-if="cite.snippet" class="citation-snippet">
                    {{ cite.snippet }}
                  </div>
                </div>
              </div>
              <div v-if="msg.role === 'assistant' && msg.id" class="message-feedback">
                <button
                  @click="submitFeedback(msg.id, 'positive')"
                  :class="['feedback-btn', { active: msg.feedback === 'positive' }]"
                  title="Helpful"
                >
                  <ThumbsUp :size="16" />
                </button>
                <button
                  @click="submitFeedback(msg.id, 'negative')"
                  :class="['feedback-btn', { active: msg.feedback === 'negative' }]"
                  title="Not helpful"
                >
                  <ThumbsDown :size="16" />
                </button>
              </div>
              <div v-if="msg.warning" class="message-warning">
                <AlertTriangle :size="16" />
                {{ msg.warning }}
              </div>
            </div>
            </div>
          </transition-group>
          <transition name="fade">
            <div v-if="sending" class="message assistant">
              <div class="message-avatar">
                <div class="avatar-circle ai-avatar">
                  <img src="/chatbot.png" alt="Chatbot" class="avatar-image" />
                  <div class="avatar-pulse animate-pulse"></div>
                </div>
              </div>
              <div class="message-content">
                <div class="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </transition>
        </div>

        <div class="chat-input-area glass">
          <div class="input-options">
            <button
              @click="requestSourceAccess"
              class="btn-link-small"
              title="Request source document access"
            >
              <FileText :size="16" />
              Request Sources
            </button>
          </div>
          <div class="input-group">
            <textarea
              v-model="inputMessage"
              @keydown.enter.exact.prevent="sendMessage"
              @keydown.shift.enter.exact="inputMessage += '\n'"
              placeholder="Ask about your documents..."
              class="chat-input"
              rows="2"
            ></textarea>
            <button
              @click="sendMessage"
              :disabled="sending || !inputMessage.trim()"
              class="btn-primary send-btn"
            >
              <Send :size="20" />
              <div class="send-glow"></div>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Handoff Modal -->
    <Modal v-model:show="showHandoffModal" title="Handoff to Human Agent">
      <div class="handoff-form">
        <div class="form-group">
          <label>Reason</label>
          <textarea
            v-model="handoffForm.reason"
            placeholder="Why do you need human assistance?"
            rows="4"
          ></textarea>
        </div>
        <div class="form-group">
          <label>Priority</label>
          <select v-model="handoffForm.priority">
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>
        <div class="form-group">
          <label>Context (will include chat history)</label>
          <input type="checkbox" v-model="handoffForm.include_context" checked />
        </div>
      </div>
      <template #footer>
        <button @click="showHandoffModal = false" class="btn-secondary">Cancel</button>
        <button @click="submitHandoff" class="btn-primary" :disabled="!handoffForm.reason">
          Submit Handoff
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '../store/chat'
import { useGroupsStore } from '../store/groups'
import { chatAPI, groupsAPI } from '../services/api'
import { Modal } from '../components'
import {
  MessageSquare,
  User,
  FileText,
  ThumbsUp,
  ThumbsDown,
  Send,
  Trash2,
  AlertTriangle,
  Circle,
  Search,
  X,
  Clock
} from 'lucide-vue-next'

const router = useRouter()
const chatStore = useChatStore()
const groupsStore = useGroupsStore()

const selectedGroup = ref('')
const accessibleGroups = ref([])
const messages = ref([])
const sessions = ref([])
const inputMessage = ref('')
const sending = ref(false)
const messagesContainer = ref(null)
const currentSessionId = ref(null)
const showHandoffModal = ref(false)
const tagFilter = ref('')
const availableDocuments = ref([])
const selectedDocumentIds = ref([])
const selectAllDocuments = ref(false) // Default: không chọn document nào
const loadingDocuments = ref(false)
const documentSearchTerm = ref('')
let documentsRefreshInterval = null

const filters = ref({
  tags: [],
  type: '',
  date_from: null,
  date_to: null
})

const handoffForm = ref({
  reason: '',
  priority: 'medium',
  include_context: true
})

// Filtered documents based on search term
const filteredDocuments = computed(() => {
  if (!documentSearchTerm.value.trim()) {
    return availableDocuments.value
  }
  
  const searchLower = documentSearchTerm.value.toLowerCase().trim()
  return availableDocuments.value.filter(doc => {
    const titleMatch = doc.title?.toLowerCase().includes(searchLower)
    const mimeMatch = doc.mime?.toLowerCase().includes(searchLower)
    return titleMatch || mimeMatch
  })
})

// Watch search term to update select all state
watch(documentSearchTerm, () => {
  if (filteredDocuments.value.length > 0) {
    const filteredIds = new Set(filteredDocuments.value.map(d => d.id))
    const selectedFilteredCount = selectedDocumentIds.value.filter(id => filteredIds.has(id)).length
    selectAllDocuments.value = selectedFilteredCount === filteredDocuments.value.length
  } else {
    selectAllDocuments.value = false
  }
})

onMounted(async () => {
  await loadGroups()
  await loadChatHistory()
  await loadAvailableDocuments()
  
  // Auto-refresh available documents every 30 seconds to catch embedding updates
  documentsRefreshInterval = setInterval(() => {
    loadAvailableDocuments()
  }, 30000) // 30 seconds
})

// Cleanup interval on unmount
onUnmounted(() => {
  try {
    if (documentsRefreshInterval) {
      clearInterval(documentsRefreshInterval)
      documentsRefreshInterval = null
    }
  } catch (error) {
    console.error('Error cleaning up documents refresh interval:', error)
  }
})

// Watch filters and group changes to reload available documents
watch([selectedGroup, () => filters.value.tags, () => filters.value.type, () => filters.value.date_from, () => filters.value.date_to], () => {
  loadAvailableDocuments()
}, { deep: true })

const loadGroups = async () => {
  try {
    await groupsStore.fetchGroups()
    accessibleGroups.value = groupsStore.groups
  } catch (e) {
    console.error('Failed to load groups', e)
  }
}

const loadChatHistory = async () => {
  try {
    await chatStore.fetchHistory({ group_id: selectedGroup.value || undefined })
    sessions.value = chatStore.sessions.map(s => ({
      ...s,
      id: s.session_id || s.id  // Ensure id exists for backward compatibility
    }))
  } catch (e) {
    console.error('Failed to load chat history', e)
  }
}

const onGroupChange = () => {
  currentSessionId.value = null
  messages.value = []
  loadChatHistory()
  loadAvailableDocuments()
}

const loadAvailableDocuments = async () => {
  loadingDocuments.value = true
  try {
    const params = {}
    if (selectedGroup.value) {
      params.group_id = selectedGroup.value
    }
    if (filters.value.tags.length > 0) {
      params.tags = filters.value.tags.join(',')
    }
    if (filters.value.type) {
      params.type = filters.value.type
    }
    if (filters.value.date_from) {
      params.date_from = filters.value.date_from
    }
    if (filters.value.date_to) {
      params.date_to = filters.value.date_to
    }
    
    const res = await chatAPI.availableDocuments(params)
    console.log('Available documents response:', res)
    
    if (res.is_success) {
      // Handle both response.data.documents and response.data structure
      const documents = res.data?.documents || res.data || []
      console.log('Loaded documents:', documents)
      
      availableDocuments.value = Array.isArray(documents) ? documents : []
      
      // If select all is true, select all document IDs
      if (selectAllDocuments.value) {
        selectedDocumentIds.value = availableDocuments.value.map(d => d.id)
      } else {
        // Keep only selected IDs that are still available
        selectedDocumentIds.value = selectedDocumentIds.value.filter(
          id => availableDocuments.value.some(d => d.id === id)
        )
      }
    } else {
      console.error('Failed to load documents:', res.message || 'Unknown error')
    }
  } catch (e) {
    console.error('Failed to load available documents', e)
    if (window.$toast) {
      window.$toast.show('Failed to load available documents', 'error')
    }
  } finally {
    loadingDocuments.value = false
  }
}

const onSelectAllChange = () => {
  if (selectAllDocuments.value) {
    // Select all filtered documents when search is active, otherwise all documents
    selectedDocumentIds.value = filteredDocuments.value.map(d => d.id)
  } else {
    // Deselect all filtered documents
    const filteredIds = new Set(filteredDocuments.value.map(d => d.id))
    selectedDocumentIds.value = selectedDocumentIds.value.filter(id => !filteredIds.has(id))
  }
}

const onDocumentSelectionChange = () => {
  // Update select all state based on current selection of filtered documents
  if (filteredDocuments.value.length > 0) {
    const filteredIds = new Set(filteredDocuments.value.map(d => d.id))
    const selectedFilteredCount = selectedDocumentIds.value.filter(id => filteredIds.has(id)).length
    selectAllDocuments.value = selectedFilteredCount === filteredDocuments.value.length
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || sending.value) return

  const userMsg = {
    id: Date.now(),
    role: 'user',
    content: inputMessage.value,
    timestamp: new Date().toISOString()
  }
  messages.value.push(userMsg)
  const question = inputMessage.value
  inputMessage.value = ''
  sending.value = true
  scrollToBottom()

  try {
    const chatData = {
      message: question,
      group_id: selectedGroup.value || undefined,
      session_id: currentSessionId.value
    }

    // Add filters
    if (filters.value.tags.length > 0 || filters.value.type || filters.value.date_from || filters.value.date_to) {
      chatData.filters = {}
      if (filters.value.tags.length > 0) {
        chatData.filters.tags = filters.value.tags
      }
      if (filters.value.type) {
        chatData.filters.type = filters.value.type
      }
      if (filters.value.date_from) {
        chatData.filters.date_from = filters.value.date_from
      }
      if (filters.value.date_to) {
        chatData.filters.date_to = filters.value.date_to
      }
    }

    // Add selected document IDs
    if (selectAllDocuments.value) {
      // Send null to indicate "select all"
      chatData.selected_document_ids = null
    } else if (selectedDocumentIds.value.length > 0) {
      // Send selected document IDs
      chatData.selected_document_ids = selectedDocumentIds.value
    } else {
      // No documents selected - send empty array to skip RAG
      chatData.selected_document_ids = []
    }

    const requestStartTime = Date.now()
    const res = await chatAPI.chat(chatData)
    if (res.is_success) {
      const botMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: res.data.answer,
        citations: res.data.citations || [],
        warning: res.data.warning,
        response_time: res.data.response_time, // Backend response time in seconds
        timestamp: new Date().toISOString()
      }
      messages.value.push(botMsg)
      if (res.data.session_id) {
        currentSessionId.value = res.data.session_id
      }
      scrollToBottom()
    }
  } catch (e) {
    console.error('Chat failed', e)
    const errorMsg = e.response?.data?.message || 'Sorry, I encountered an error. Please try again.'
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: errorMsg,
      timestamp: new Date().toISOString()
    })
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

const loadSession = async (sessionId) => {
  currentSessionId.value = sessionId
  try {
    await chatStore.fetchSession(sessionId)
    messages.value = chatStore.messages.map((msg, idx) => ({
      ...msg,
      id: idx,
      feedback: msg.feedback?.rating
    }))
    scrollToBottom()
  } catch (e) {
    console.error('Failed to load session', e)
    if (window.$toast) {
      window.$toast.show('Failed to load session', 'error')
    }
  }
}

const clearChat = () => {
  if (confirm('Clear current chat?')) {
    messages.value = []
    currentSessionId.value = null
    chatStore.clearMessages()
  }
}

const submitFeedback = async (messageId, rating) => {
  if (!currentSessionId.value) return
  try {
    await chatStore.submitFeedback(currentSessionId.value, {
      message_id: messageId,
      rating: rating
    })
    // Update message feedback
    const msg = messages.value.find(m => m.id === messageId)
    if (msg) {
      msg.feedback = rating
    }
    if (window.$toast) {
      window.$toast.show('Feedback submitted', 'success')
    }
  } catch (e) {
    console.error('Failed to submit feedback', e)
    if (window.$toast) {
      window.$toast.show('Failed to submit feedback', 'error')
    }
  }
}

const submitHandoff = async () => {
  if (!currentSessionId.value || !handoffForm.value.reason) return
  try {
    await chatStore.handoff(currentSessionId.value, {
      reason: handoffForm.value.reason,
      priority: handoffForm.value.priority,
      include_context: handoffForm.value.include_context,
      messages: handoffForm.value.include_context ? messages.value : []
    })
    if (window.$toast) {
      window.$toast.show('Handoff submitted successfully', 'success')
    }
    showHandoffModal.value = false
    handoffForm.value = { reason: '', priority: 'medium', include_context: true }
  } catch (e) {
    console.error('Failed to submit handoff', e)
    if (window.$toast) {
      window.$toast.show('Failed to submit handoff', 'error')
    }
  }
}

const requestSourceAccess = async () => {
  if (!currentSessionId.value) {
    if (window.$toast) {
      window.$toast.show('Please start a chat session first', 'info')
    }
    return
  }
  
  // Collect document IDs from citations in the last assistant message
  const lastAssistantMsg = [...messages.value].reverse().find(msg => msg.role === 'assistant')
  const sourceIds = []
  
  if (lastAssistantMsg && lastAssistantMsg.citations) {
    lastAssistantMsg.citations.forEach(cite => {
      const docId = cite.document_id || cite.doc_id
      if (docId && !sourceIds.includes(docId)) {
        sourceIds.push(docId)
      }
    })
  }
  
  if (sourceIds.length === 0) {
    if (window.$toast) {
      window.$toast.show('No sources available in current conversation', 'info')
    }
    return
  }
  
  try {
    const res = await chatAPI.sourceAccess(currentSessionId.value, {
      source_ids: sourceIds,
      access_type: 'preview'
    })
    if (res.is_success && res.data.sources) {
      // Show sources in a modal or sidebar
      if (window.$toast) {
        window.$toast.show(`${res.data.sources.length} sources available`, 'success')
      }
    }
  } catch (e) {
    console.error('Failed to request source access', e)
    if (window.$toast) {
      window.$toast.show('Failed to request source access', 'error')
    }
  }
}

const addTagFilter = () => {
  if (tagFilter.value.trim() && !filters.value.tags.includes(tagFilter.value.trim())) {
    filters.value.tags.push(tagFilter.value.trim())
    tagFilter.value = ''
  }
}

const removeTagFilter = (tag) => {
  filters.value.tags = filters.value.tags.filter(t => t !== tag)
}

const viewDocument = (docId) => {
  router.push(`/documents/${docId}`)
}

const formatMessage = (content) => {
  // Simple markdown-like formatting
  return content
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>')
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}

const formatResponseTime = (timeInSeconds) => {
  if (timeInSeconds === undefined || timeInSeconds === null) return ''
  
  // Convert to milliseconds for display
  const ms = timeInSeconds * 1000
  
  if (ms < 1000) {
    return `${Math.round(ms)}ms`
  } else {
    return `${timeInSeconds.toFixed(2)}s`
  }
}
</script>

<style scoped>
.chatbot-page {
  max-width: 1600px;
  margin: 0 auto;
  position: relative;
  min-height: calc(100vh - 200px);
}

.particles-background {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--gradient-ai-soft);
  opacity: 0.4;
  z-index: 0;
  pointer-events: none;
  animation: shimmer 8s ease-in-out infinite;
}

.particles-background::before,
.particles-background::after {
  content: '';
  position: absolute;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0, 217, 255, 0.3) 0%, transparent 70%);
  animation: float 6s ease-in-out infinite;
}

.particles-background::before {
  top: 20%;
  left: 10%;
  animation-delay: 0s;
}

.particles-background::after {
  bottom: 20%;
  right: 10%;
  animation-delay: 3s;
}

.chat-container {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: var(--space-xl);
  height: calc(100vh - 200px);
  position: relative;
  z-index: 1;
}

.chat-sidebar {
  padding: var(--space-lg);
  border-radius: var(--radius-xl);
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
  overflow-y: auto;
  position: relative;
}

.sidebar-section h3 {
  margin: 0 0 1rem 0;
  color: var(--primary);
  font-size: 1rem;
}

.group-selector select {
  width: 100%;
  padding: var(--space-md) var(--space-lg);
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-lg);
  background: var(--bg-white);
  font-size: 0.95rem;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
}

.group-selector select:focus {
  outline: none;
  border-color: var(--ai-cyan);
  box-shadow: var(--shadow-md), 0 0 0 3px rgba(0, 217, 255, 0.1);
}

.filter-group {
  margin-bottom: var(--space-lg);
}

.filter-group label {
  display: block;
  margin-bottom: var(--space-sm);
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-dark);
}

.filter-group input,
.filter-group select {
  width: 100%;
  padding: var(--space-md) var(--space-lg);
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-lg);
  background: var(--bg-white);
  font-size: 0.95rem;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
  position: relative;
}

.filter-group input[type="date"] {
  padding-right: var(--space-xl);
  cursor: pointer;
  position: relative;
}

.filter-group input[type="date"]::-webkit-calendar-picker-indicator {
  cursor: pointer;
  opacity: 0.6;
  filter: grayscale(1);
  transition: all var(--transition-base);
  padding: var(--space-xs);
  border-radius: var(--radius-sm);
}

.filter-group input[type="date"]::-webkit-calendar-picker-indicator:hover {
  opacity: 1;
  filter: grayscale(0);
  background: var(--gradient-ai-soft);
}

.filter-group input:focus,
.filter-group select:focus {
  outline: none;
  border-color: var(--ai-cyan);
  box-shadow: var(--shadow-md), 0 0 0 3px rgba(0, 217, 255, 0.1);
}

.filter-group input[type="date"]:focus::-webkit-calendar-picker-indicator {
  opacity: 1;
  filter: grayscale(0);
}

.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.tag-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--primary-light);
  color: var(--primary);
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-lg);
  font-size: 0.85rem;
}

.tag-remove {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--primary);
  font-size: 1.2rem;
  line-height: 1;
  padding: 0;
}

.chat-history {
  max-height: 300px;
  overflow-y: auto;
}

.session-item {
  padding: 0.75rem;
  background: var(--bg-light);
  border-radius: var(--radius-md);
  margin-bottom: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.session-item:hover {
  background: var(--primary-light);
}

.session-item.active {
  background: var(--primary);
  color: white;
}

.session-title {
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.session-date {
  font-size: 0.85rem;
  opacity: 0.7;
}

.empty-sessions {
  text-align: center;
  padding: 2rem;
  color: #666;
  font-size: 0.9rem;
}

.source-documents {
  max-height: 400px;
  overflow-y: auto;
}

.document-search-wrapper {
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.document-search-input {
  position: relative;
  display: flex;
  align-items: center;
  background: var(--bg-white);
  border: 2px solid rgba(0, 0, 0, 0.08);
  border-radius: var(--radius-lg);
  padding: var(--space-sm) var(--space-md);
  transition: all var(--transition-base);
  margin-bottom: var(--space-xs);
}

.document-search-input:focus-within {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.1);
}

.search-icon {
  color: var(--text-light);
  flex-shrink: 0;
  margin-right: var(--space-sm);
}

.document-search {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.9rem;
  color: var(--text-dark);
  font-family: inherit;
}

.document-search::placeholder {
  color: var(--text-lighter);
}

.search-clear-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-light);
  border: none;
  border-radius: var(--radius-full);
  width: 20px;
  height: 20px;
  cursor: pointer;
  color: var(--text-light);
  transition: all var(--transition-base);
  flex-shrink: 0;
  margin-left: var(--space-xs);
  padding: 0;
}

.search-clear-btn:hover {
  background: var(--primary-light);
  color: var(--primary);
  transform: scale(1.1);
}

.search-results-info {
  font-size: 0.75rem;
  color: var(--text-light);
  text-align: right;
  padding-top: var(--space-xs);
  font-weight: 500;
}

.select-all-control {
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.checkbox-label {
  display: flex;
  align-items: flex-start;
  gap: var(--space-sm);
  cursor: pointer;
  padding: var(--space-sm);
  border-radius: var(--radius-md);
  transition: background-color var(--transition-base);
}

.checkbox-label:hover {
  background-color: var(--bg-light);
}

.checkbox-label input[type="checkbox"] {
  margin-top: 0.25rem;
  cursor: pointer;
  width: 18px;
  height: 18px;
  accent-color: var(--primary);
}

.source-documents-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.source-document-item {
  margin-bottom: var(--space-xs);
}

.source-document-item .checkbox-label {
  width: 100%;
}

.document-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.document-title {
  font-weight: 500;
  font-size: 0.9rem;
  color: var(--text-dark);
  line-height: 1.4;
  word-break: break-word;
}

.document-meta {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 0.75rem;
  color: var(--text-light);
}

.document-type {
  padding: 0.125rem 0.5rem;
  background: var(--bg-light);
  border-radius: var(--radius-sm);
}

.no-embedding-badge {
  padding: 0.125rem 0.5rem;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #92400e;
  border-radius: var(--radius-sm);
  font-size: 0.7rem;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border: 1px solid rgba(245, 158, 11, 0.3);
  cursor: help;
  transition: all var(--transition-base);
}

.no-embedding-badge:hover {
  background: linear-gradient(135deg, #fde68a 0%, #fcd34d 100%);
  border-color: #f59e0b;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(245, 158, 11, 0.2);
}

.loading-documents,
.empty-documents {
  text-align: center;
  padding: 2rem;
  color: #666;
  font-size: 0.9rem;
}

.chat-main {
  background: var(--bg-white);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.chat-main::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--gradient-ai);
  z-index: 1;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-lg) var(--space-xl);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  background: linear-gradient(to bottom, var(--bg-white) 0%, rgba(255, 255, 255, 0.95) 100%);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 10;
}

.session-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-medium);
  padding: var(--space-xs) var(--space-md);
  background: var(--bg-light);
  border-radius: var(--radius-lg);
}

.session-indicator.new {
  color: var(--primary);
  background: var(--gradient-ai-soft);
}

.session-indicator svg {
  animation: pulse 2s var(--ease-in-out) infinite;
}

.chat-actions {
  display: flex;
  gap: var(--space-sm);
}

.btn-small {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: var(--bg-white);
  border: 2px solid rgba(0, 0, 0, 0.08);
  border-radius: var(--radius-lg);
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-dark);
  cursor: pointer;
  transition: all var(--transition-base);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.btn-small:hover {
  background: var(--gradient-ai-soft);
  border-color: var(--ai-cyan);
  color: var(--primary);
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0, 217, 255, 0.15);
}

.btn-small:active {
  transform: translateY(0);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-xl) var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  background: linear-gradient(to bottom, rgba(248, 249, 255, 0.5) 0%, rgba(255, 255, 255, 0.5) 100%);
}

.messages::-webkit-scrollbar {
  width: 8px;
}

.messages::-webkit-scrollbar-track {
  background: transparent;
}

.messages::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-full);
}

.messages::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}

.welcome-message {
  text-align: center;
  padding: var(--space-3xl) var(--space-xl);
  color: var(--text-medium);
  animation: fadeInUp var(--transition-slow) var(--ease-out);
  max-width: 600px;
  margin: 0 auto;
}

.welcome-icon-wrapper {
  position: relative;
  width: 140px;
  height: 140px;
  margin: 0 auto var(--space-xl);
}

.welcome-icon {
  width: 90px;
  height: 90px;
  position: relative;
  z-index: 2;
  animation: float 3s var(--ease-in-out) infinite;
  filter: drop-shadow(0 0 30px rgba(0, 217, 255, 0.5));
  object-fit: contain;
  border-radius: 50%;
  background: var(--gradient-cyan-purple);
  padding: 8px;
  box-sizing: border-box;
}

.welcome-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  background: var(--gradient-cyan-purple);
  border-radius: var(--radius-full);
  transform: translate(-50%, -50%);
  opacity: 0.4;
  filter: blur(30px);
  animation: glow-pulse 3s var(--ease-in-out) infinite;
}

.welcome-message h3 {
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 var(--space-md) 0;
  background: var(--gradient-ai);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.3;
}

.welcome-message p {
  font-size: 1.05rem;
  color: var(--text-medium);
  margin: 0;
  line-height: 1.6;
}

.message {
  display: flex;
  gap: var(--space-lg);
  align-items: flex-start;
  margin-bottom: var(--space-xl);
  animation: fadeInUp var(--transition-base) var(--ease-out);
  padding: 0 var(--space-md);
}

.message-enter-active {
  transition: all var(--transition-base) var(--ease-out);
}

.message-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
  position: relative;
}

.avatar-circle {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all var(--transition-base);
  border: 3px solid transparent;
  background-clip: padding-box;
  overflow: hidden;
}

.user-avatar {
  background: var(--gradient-primary);
  color: white;
  box-shadow: 0 4px 12px rgba(108, 92, 231, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1) inset;
}

.ai-avatar {
  background: transparent;
  padding: 0;
  box-shadow: 0 4px 12px rgba(0, 217, 255, 0.4);
}

.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 50%;
  display: block;
}

.avatar-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  border-radius: var(--radius-full);
  background: var(--gradient-cyan-purple);
  transform: translate(-50%, -50%);
  opacity: 0.4;
  animation: pulse 2s var(--ease-in-out) infinite;
  z-index: -1;
}

.message-content {
  flex: 1;
  max-width: 75%;
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.message.user .message-content {
  align-items: flex-end;
}

.message-text {
  background: var(--bg-light);
  padding: var(--space-lg) var(--space-xl);
  border-radius: var(--radius-xl);
  line-height: 1.8;
  position: relative;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all var(--transition-base);
  font-size: 0.95rem;
  word-wrap: break-word;
  border: 1px solid rgba(0, 0, 0, 0.03);
}

.message-text::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: var(--radius-xl);
  padding: 1px;
  background: var(--gradient-ai-soft);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0.3;
  transition: opacity var(--transition-base);
}

.message.assistant .message-text {
  background: linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%);
  border-left: 3px solid var(--ai-cyan);
}

.message.assistant .message-text::before {
  opacity: 0.5;
}

.message.user .message-text {
  background: var(--gradient-primary);
  color: white;
  box-shadow: 0 4px 16px rgba(108, 92, 231, 0.3), 0 2px 8px rgba(108, 92, 231, 0.2);
  border: none;
}

.message.user .message-text::before {
  display: none;
}

.message.user .message-text:hover {
  box-shadow: 0 6px 20px rgba(108, 92, 231, 0.4), 0 4px 12px rgba(108, 92, 231, 0.3);
  transform: translateY(-1px);
}

.citations {
  margin-top: var(--space-md);
  padding-top: var(--space-md);
  border-top: 2px solid rgba(0, 217, 255, 0.15);
  background: linear-gradient(135deg, rgba(0, 217, 255, 0.05) 0%, rgba(108, 92, 231, 0.05) 100%);
  padding: var(--space-md);
  border-radius: var(--radius-lg);
  margin-top: var(--space-md);
}

.citations-header {
  font-size: 0.8rem;
  font-weight: 700;
  margin-bottom: var(--space-sm);
  color: var(--primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.citations-header::before {
  content: '📎';
  font-size: 1rem;
}

.citation {
  font-size: 0.875rem;
  margin-top: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: white;
  border-radius: var(--radius-md);
  border: 1px solid rgba(0, 217, 255, 0.2);
  transition: all var(--transition-base);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.citation:hover {
  border-color: var(--ai-cyan);
  box-shadow: 0 2px 8px rgba(0, 217, 255, 0.15);
  transform: translateX(4px);
}

.citation-link {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: var(--primary);
  cursor: pointer;
  text-decoration: none;
  font-weight: 500;
  transition: all var(--transition-base);
}

.citation-link:hover {
  color: var(--ai-cyan);
  text-decoration: none;
}

.citation-link svg {
  transition: transform var(--transition-base);
}

.citation-link:hover svg {
  transform: scale(1.1);
}

.citation-score {
  font-size: 0.75rem;
  color: var(--text-light);
  background: var(--bg-light);
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-sm);
  display: inline-block;
  margin-left: auto;
}

.citation-snippet {
  font-size: 0.8rem;
  color: var(--text-medium);
  margin-top: var(--space-xs);
  font-style: italic;
  line-height: 1.5;
  padding-left: var(--space-md);
  border-left: 2px solid var(--ai-cyan);
  background: rgba(0, 217, 255, 0.03);
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.message-feedback {
  display: flex;
  gap: var(--space-xs);
  margin-top: var(--space-sm);
  padding-top: var(--space-sm);
}

.feedback-btn {
  padding: var(--space-xs) var(--space-sm);
  background: var(--bg-white);
  border: 2px solid rgba(0, 0, 0, 0.08);
  border-radius: var(--radius-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  transition: all var(--transition-base);
  font-size: 0.8rem;
  color: var(--text-medium);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.feedback-btn:hover {
  background: var(--bg-light);
  border-color: var(--primary);
  color: var(--primary);
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.feedback-btn.active {
  background: var(--gradient-primary);
  color: white;
  border-color: var(--primary);
  box-shadow: 0 2px 6px rgba(108, 92, 231, 0.3);
}

.message-response-time {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-top: var(--space-xs);
  padding: 0.25rem 0.5rem;
  background: rgba(0, 217, 255, 0.1);
  color: var(--ai-cyan);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 500;
  opacity: 0.8;
}

.message.user .message-response-time {
  display: none; /* Only show for assistant messages */
}

.message-warning {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-top: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #92400e;
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  border-left: 3px solid #f59e0b;
  box-shadow: 0 2px 4px rgba(245, 158, 11, 0.1);
}

.typing-indicator {
  display: flex;
  gap: 0.5rem;
  padding: var(--space-lg) var(--space-xl);
  align-items: center;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%);
  border-radius: var(--radius-xl);
  border-left: 3px solid var(--ai-cyan);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin: 0 var(--space-md) var(--space-xl);
}

.typing-indicator span {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  background: var(--gradient-cyan-purple);
  animation: typing 1.4s var(--ease-in-out) infinite;
  box-shadow: 0 0 12px rgba(0, 217, 255, 0.6);
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0) scale(1);
    opacity: 0.6;
  }
  30% {
    transform: translateY(-10px) scale(1.15);
    opacity: 1;
  }
}

.chat-input-area {
  padding: var(--space-xl);
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  position: relative;
  background: linear-gradient(to top, var(--bg-white) 0%, rgba(255, 255, 255, 0.95) 100%);
  backdrop-filter: blur(10px);
}

.input-options {
  margin-bottom: var(--space-md);
}

.btn-link-small {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: var(--bg-white);
  border: 2px solid rgba(0, 217, 255, 0.2);
  border-radius: var(--radius-lg);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--primary);
  cursor: pointer;
  text-decoration: none;
  transition: all var(--transition-base);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.btn-link-small:hover {
  background: var(--gradient-ai-soft);
  border-color: var(--ai-cyan);
  color: var(--primary);
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0, 217, 255, 0.2);
}

.input-group {
  display: flex;
  gap: var(--space-md);
  align-items: flex-end;
  position: relative;
  background: var(--bg-white);
  border-radius: var(--radius-2xl);
  padding: var(--space-xs);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(0, 0, 0, 0.05);
  transition: all var(--transition-base);
}

.input-group:focus-within {
  box-shadow: 0 6px 20px rgba(0, 217, 255, 0.15), 0 0 0 3px rgba(0, 217, 255, 0.1);
  border-color: var(--ai-cyan);
}

.chat-input {
  flex: 1;
  padding: var(--space-lg) var(--space-xl);
  border: none;
  border-radius: var(--radius-xl);
  font-size: 0.95rem;
  font-family: inherit;
  resize: none;
  background: transparent;
  transition: all var(--transition-base);
  line-height: 1.6;
  min-height: 52px;
  max-height: 200px;
}

.chat-input:focus {
  outline: none;
}

.chat-input::placeholder {
  color: var(--text-lighter);
}

.send-btn {
  padding: var(--space-md);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  min-width: 52px;
  height: 52px;
  border-radius: var(--radius-xl);
  background: var(--gradient-primary);
  border: none;
  color: white;
  cursor: pointer;
  transition: all var(--transition-base);
  box-shadow: 0 4px 12px rgba(108, 92, 231, 0.3);
}

.send-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  background: var(--gradient-cyan-purple);
  border-radius: var(--radius-full);
  transform: translate(-50%, -50%) scale(0);
  opacity: 0;
  transition: all var(--transition-base);
  filter: blur(12px);
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(108, 92, 231, 0.4);
}

.send-btn:hover:not(:disabled) .send-glow {
  transform: translate(-50%, -50%) scale(1.8);
  opacity: 0.5;
}

.send-btn:active:not(:disabled) {
  transform: translateY(0);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.handoff-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
}

.form-group textarea,
.form-group select {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: var(--radius-md);
  font-family: inherit;
}

.form-group input[type="checkbox"] {
  width: auto;
}

/* Responsive Design */
@media (max-width: 1024px) {
  .chat-container {
    grid-template-columns: 300px 1fr;
    gap: var(--space-lg);
  }
  
  .chat-sidebar {
    padding: var(--space-md);
  }
}

@media (max-width: 768px) {
  .chat-container {
    grid-template-columns: 1fr;
    height: auto;
    min-height: calc(100vh - 200px);
  }
  
  .chat-sidebar {
    order: 2;
    max-height: 400px;
  }
  
  .chat-main {
    order: 1;
  }
  
  .messages {
    padding: var(--space-md);
    gap: var(--space-md);
  }
  
  .message-content {
    max-width: 85%;
  }
  
  .chat-input-area {
    padding: var(--space-md);
  }
  
  .input-group {
    flex-direction: column;
    align-items: stretch;
  }
  
  .chat-input {
    width: 100%;
    margin-bottom: var(--space-sm);
  }
  
  .send-btn {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .chat-sidebar {
    padding: var(--space-sm);
  }
  
  .sidebar-section {
    margin-bottom: var(--space-md);
  }
  
  .message-content {
    max-width: 90%;
  }
}
</style>
