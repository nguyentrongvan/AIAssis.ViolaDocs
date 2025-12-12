<template>
  <div class="chatbot-page">
    <h1 class="page-header">Chatbot Assistant</h1>

    <div class="chat-container">
      <div class="chat-sidebar">
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
          <h3>Chat History</h3>
          <div class="chat-history">
            <div
              v-for="session in sessions"
              :key="session.id"
              class="session-item"
              :class="{ active: currentSessionId === session.id }"
              @click="loadSession(session.id)"
            >
              <div class="session-title">
                {{ session.title || `Chat ${session.id.slice(0, 8)}` }}
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
            <MessageSquare :size="48" />
            <h3>Ask me anything about your documents</h3>
            <p>Select a document group and start asking questions</p>
          </div>
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            :class="['message', msg.role]"
          >
            <div class="message-avatar">
              <User v-if="msg.role === 'user'" :size="20" />
              <MessageSquare v-else :size="20" />
            </div>
            <div class="message-content">
              <div class="message-text" v-html="formatMessage(msg.content)"></div>
              <div v-if="msg.citations && msg.citations.length > 0" class="citations">
                <div class="citations-header">Sources:</div>
                <div
                  v-for="(cite, citeIdx) in msg.citations"
                  :key="citeIdx"
                  class="citation"
                >
                  <a
                    @click.prevent="viewDocument(cite.doc_id)"
                    class="citation-link"
                  >
                    <FileText :size="14" />
                    {{ cite.doc_title || `Document ${cite.doc_id}` }}
                  </a>
                  <span v-if="cite.score" class="citation-score">
                    ({{ (cite.score * 100).toFixed(0) }}% match)
                  </span>
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
          <div v-if="sending" class="message assistant">
            <div class="message-avatar">
              <MessageSquare :size="20" />
            </div>
            <div class="message-content">
              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>

        <div class="chat-input-area">
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
import { ref, computed, onMounted, nextTick, watch } from 'vue'
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
  Circle
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

onMounted(async () => {
  await loadGroups()
  await loadChatHistory()
})

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
    sessions.value = chatStore.sessions
  } catch (e) {
    console.error('Failed to load chat history', e)
  }
}

const onGroupChange = () => {
  currentSessionId.value = null
  messages.value = []
  loadChatHistory()
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
    if (filters.value.tags.length > 0) {
      chatData.filters = { ...chatData.filters, tags: filters.value.tags }
    }
    if (filters.value.type) {
      chatData.filters = { ...chatData.filters, type: filters.value.type }
    }
    if (filters.value.date_from) {
      chatData.filters = { ...chatData.filters, date_from: filters.value.date_from }
    }
    if (filters.value.date_to) {
      chatData.filters = { ...chatData.filters, date_to: filters.value.date_to }
    }

    const res = await chatAPI.chat(chatData)
    if (res.is_success) {
      const botMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: res.data.answer,
        citations: res.data.citations || [],
        warning: res.data.warning,
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
  try {
    const res = await chatAPI.sourceAccess(currentSessionId.value, {
      request_type: 'documents'
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
</script>

<style scoped>
.chatbot-page {
  max-width: 1600px;
  margin: 0 auto;
}

.chat-container {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 2rem;
  height: calc(100vh - 200px);
}

.chat-sidebar {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  gap: 2rem;
  overflow-y: auto;
}

.sidebar-section h3 {
  margin: 0 0 1rem 0;
  color: var(--primary);
  font-size: 1rem;
}

.group-selector select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.filter-group {
  margin-bottom: 1rem;
}

.filter-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  font-size: 0.9rem;
}

.filter-group input,
.filter-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
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
  border-radius: 12px;
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
  border-radius: 6px;
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

.chat-main {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #eee;
}

.session-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #666;
}

.session-indicator.new {
  color: var(--primary);
}

.chat-actions {
  display: flex;
  gap: 0.5rem;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.welcome-message {
  text-align: center;
  padding: 4rem 2rem;
  color: #666;
}

.welcome-message svg {
  margin-bottom: 1rem;
  color: var(--primary);
  opacity: 0.5;
}

.message {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
}

.message.user .message-avatar {
  background: var(--primary);
  color: white;
}

.message-content {
  flex: 1;
  max-width: 70%;
}

.message.user .message-content {
  text-align: right;
}

.message-text {
  background: var(--bg-light);
  padding: 1rem;
  border-radius: 12px;
  line-height: 1.6;
}

.message.user .message-text {
  background: var(--primary);
  color: white;
}

.citations {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.citations-header {
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: #666;
}

.citation {
  font-size: 0.85rem;
  margin-top: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.citation-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--primary);
  cursor: pointer;
  text-decoration: none;
}

.citation-link:hover {
  text-decoration: underline;
}

.citation-score {
  font-size: 0.75rem;
  color: #666;
}

.message-feedback {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.feedback-btn {
  padding: 0.25rem 0.5rem;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all 0.2s;
}

.feedback-btn:hover {
  background: var(--bg-light);
}

.feedback-btn.active {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.message-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #fef3c7;
  color: #92400e;
  border-radius: 4px;
  font-size: 0.85rem;
}

.typing-indicator {
  display: flex;
  gap: 0.25rem;
  padding: 1rem;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #999;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.7;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

.chat-input-area {
  padding: 1.5rem;
  border-top: 1px solid #eee;
}

.input-options {
  margin-bottom: 0.5rem;
}

.input-group {
  display: flex;
  gap: 0.75rem;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
  font-family: inherit;
  resize: none;
}

.send-btn {
  padding: 0.75rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
  border-radius: 6px;
  font-family: inherit;
}

.form-group input[type="checkbox"] {
  width: auto;
}
</style>
