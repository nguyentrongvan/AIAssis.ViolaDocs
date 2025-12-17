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
            <div class="welcome-icon-wrapper">
              <MessageSquare class="welcome-icon" :size="64" />
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
                  <MessageSquare :size="20" />
                  <div class="avatar-pulse"></div>
                </div>
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
          </transition-group>
          <transition name="fade">
            <div v-if="sending" class="message assistant">
              <div class="message-avatar">
                <div class="avatar-circle ai-avatar">
                  <MessageSquare :size="20" />
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
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  background: var(--bg-white);
}

.session-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-medium);
}

.session-indicator.new {
  color: var(--primary);
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
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-lg);
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-dark);
  cursor: pointer;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.btn-small:hover {
  background: var(--gradient-ai-soft);
  border-color: var(--ai-cyan);
  color: var(--primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.btn-small:active {
  transform: translateY(0);
  box-shadow: var(--shadow-sm);
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
  padding: var(--space-3xl) var(--space-xl);
  color: var(--text-medium);
  animation: fadeInUp var(--transition-slow) var(--ease-out);
}

.welcome-icon-wrapper {
  position: relative;
  width: 120px;
  height: 120px;
  margin: 0 auto var(--space-xl);
}

.welcome-icon {
  width: 80px;
  height: 80px;
  color: var(--primary);
  position: relative;
  z-index: 2;
  animation: float 3s var(--ease-in-out) infinite;
  filter: drop-shadow(0 0 20px rgba(0, 217, 255, 0.4));
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
  opacity: 0.3;
  filter: blur(20px);
  animation: glow-pulse 2s var(--ease-in-out) infinite;
}

.welcome-message h3 {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 var(--space-md) 0;
}

.welcome-message p {
  font-size: 1rem;
  color: var(--text-light);
  margin: 0;
}

.message {
  display: flex;
  gap: var(--space-md);
  align-items: flex-start;
  animation: fadeInUp var(--transition-base) var(--ease-out);
}

.message-enter-active {
  transition: all var(--transition-base) var(--ease-out);
}

.message-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.avatar-circle {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all var(--transition-base);
}

.user-avatar {
  background: var(--gradient-primary);
  color: white;
  box-shadow: var(--shadow-glow);
}

.ai-avatar {
  background: var(--gradient-cyan-purple);
  color: white;
  box-shadow: var(--shadow-glow-cyan);
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
  opacity: 0.6;
  animation: pulse 2s var(--ease-in-out) infinite;
}

.message-content {
  flex: 1;
  max-width: 70%;
  position: relative;
}

.message.user .message-content {
  text-align: right;
}

.message-text {
  background: var(--bg-light);
  padding: var(--space-lg);
  border-radius: var(--radius-xl);
  line-height: 1.7;
  position: relative;
  box-shadow: var(--shadow-md);
  transition: all var(--transition-base);
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
  opacity: 0;
  transition: opacity var(--transition-base);
}

.message.assistant .message-text::before {
  opacity: 1;
}

.message.user .message-text {
  background: var(--gradient-primary);
  color: white;
  box-shadow: var(--shadow-lg), var(--shadow-glow);
}

.message.user .message-text::before {
  display: none;
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
  border-radius: var(--radius-sm);
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
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
}

.typing-indicator {
  display: flex;
  gap: 0.5rem;
  padding: var(--space-lg);
  align-items: center;
}

.typing-indicator span {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  background: var(--gradient-cyan-purple);
  animation: typing 1.4s var(--ease-in-out) infinite;
  box-shadow: 0 0 10px rgba(0, 217, 255, 0.5);
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
    opacity: 0.7;
  }
  30% {
    transform: translateY(-12px) scale(1.2);
    opacity: 1;
  }
}

.chat-input-area {
  padding: var(--space-lg);
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  position: relative;
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
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-lg);
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-dark);
  cursor: pointer;
  text-decoration: none;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.btn-link-small:hover {
  background: var(--gradient-ai-soft);
  border-color: var(--ai-cyan);
  color: var(--primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.input-group {
  display: flex;
  gap: var(--space-md);
  align-items: flex-end;
  position: relative;
}

.chat-input {
  flex: 1;
  padding: var(--space-lg);
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-xl);
  font-size: 1rem;
  font-family: inherit;
  resize: none;
  background: var(--bg-white);
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.chat-input:focus {
  outline: none;
  border-color: var(--ai-cyan);
  box-shadow: var(--shadow-md), 0 0 0 3px rgba(0, 217, 255, 0.1);
}

.send-btn {
  padding: var(--space-lg) var(--space-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  min-width: 56px;
  height: 56px;
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
  filter: blur(10px);
}

.send-btn:hover:not(:disabled) .send-glow {
  transform: translate(-50%, -50%) scale(1.5);
  opacity: 0.6;
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
