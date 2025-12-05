<template>
  <Layout>
    <template #header>
      <h1>Chatbot Assistant</h1>
    </template>
    <div class="chatbot-page">
      <div class="chat-container">
        <div class="chat-sidebar">
          <div class="group-selector">
            <label>Document Group:</label>
            <select v-model="selectedGroup" @change="loadChatHistory">
              <option value="">All Documents</option>
              <option v-for="group in groups" :key="group.id" :value="group.id">{{ group.name }}</option>
            </select>
          </div>
          <div class="chat-history">
            <h4>Recent Chats</h4>
            <div v-for="session in sessions" :key="session.id" class="session-item" @click="loadSession(session.id)">
              {{ session.title || 'Chat ' + session.id }}
            </div>
          </div>
        </div>
        <div class="chat-main">
          <div class="messages" ref="messagesContainer">
            <div v-for="msg in messages" :key="msg.id" :class="['message', msg.role]">
              <div class="message-content">
                <div v-html="msg.content"></div>
                <div v-if="msg.citations && msg.citations.length > 0" class="citations">
                  <div v-for="(cite, idx) in msg.citations" :key="idx" class="citation">
                    <a @click.prevent="viewDocument(cite.doc_id)">{{ cite.doc_title }}</a>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="chat-input-area">
            <input v-model="inputMessage" @keyup.enter="sendMessage" placeholder="Ask about your documents..." class="chat-input" />
            <button @click="sendMessage" :disabled="sending" class="btn-primary">Send</button>
          </div>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import Layout from '../components/Layout.vue'
import api from '../services/api'

const router = useRouter()

const selectedGroup = ref('')
const groups = ref([])
const messages = ref([])
const sessions = ref([])
const inputMessage = ref('')
const sending = ref(false)
const messagesContainer = ref(null)
const currentSessionId = ref(null)

onMounted(async () => {
  await loadGroups()
  await loadChatHistory()
})

const loadGroups = async () => {
  try {
    const res = await api.get('/groups')
    if (res.is_success) {
      groups.value = res.data || []
    }
  } catch (e) {
    console.error('Failed to load groups', e)
  }
}

const loadChatHistory = async () => {
  try {
    const res = await api.get('/chat/history', {
      params: { group_id: selectedGroup.value || undefined }
    })
    if (res.is_success) {
      sessions.value = res.data.sessions || []
      if (res.data.messages) {
        messages.value = res.data.messages
      }
    }
  } catch (e) {
    console.error('Failed to load chat history', e)
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || sending.value) return
  const userMsg = {
    id: Date.now(),
    role: 'user',
    content: inputMessage.value
  }
  messages.value.push(userMsg)
  const question = inputMessage.value
  inputMessage.value = ''
  sending.value = true
  scrollToBottom()
  try {
    const res = await api.post('/chat', {
      message: question,
      group_id: selectedGroup.value || undefined,
      session_id: currentSessionId.value
    })
    if (res.is_success) {
      const botMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: res.data.answer,
        citations: res.data.citations || []
      }
      messages.value.push(botMsg)
      if (res.data.session_id) {
        currentSessionId.value = res.data.session_id
      }
    }
  } catch (e) {
    console.error('Chat failed', e)
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: 'Sorry, I encountered an error. Please try again.'
    })
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const loadSession = async (sessionId) => {
  currentSessionId.value = sessionId
  try {
    const res = await api.get(`/chat/session/${sessionId}`)
    if (res.is_success) {
      messages.value = res.data.messages || []
    }
  } catch (e) {
    console.error('Failed to load session', e)
  }
}

const viewDocument = (docId) => {
  router.push(`/documents/${docId}`)
}
</script>

<style scoped>
.chatbot-page {
  max-width: 1400px;
  margin: 0 auto;
}
.chat-container {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 2rem;
  height: calc(100vh - 200px);
}
.chat-sidebar {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
}
.group-selector {
  margin-bottom: 2rem;
}
.group-selector label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}
.group-selector select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}
.chat-history h4 {
  margin: 0 0 1rem 0;
}
.session-item {
  padding: 0.75rem;
  background: var(--bg-light);
  border-radius: 6px;
  margin-bottom: 0.5rem;
  cursor: pointer;
  transition: background 0.2s;
}
.session-item:hover {
  background: var(--primary-light);
}
.chat-main {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}
.message {
  margin-bottom: 1.5rem;
}
.message.user {
  text-align: right;
}
.message-content {
  display: inline-block;
  max-width: 70%;
  padding: 1rem;
  border-radius: 12px;
  background: var(--bg-light);
}
.message.user .message-content {
  background: var(--primary);
  color: white;
}
.citations {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid rgba(0,0,0,0.1);
}
.citation {
  font-size: 0.85rem;
  margin-top: 0.25rem;
}
.citation a {
  color: var(--primary);
  cursor: pointer;
  text-decoration: underline;
}
.chat-input-area {
  padding: 1.5rem;
  border-top: 1px solid #eee;
  display: flex;
  gap: 1rem;
}
.chat-input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
}
</style>

