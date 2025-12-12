<template>
  <div class="admin-page">
    <h1 class="page-header">Settings</h1>

    <div class="settings-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        :class="['tab-btn', { 'tab-btn-active': activeTab === tab.id }]"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="settings-content">
      <!-- Retention Policies Tab -->
      <div v-if="activeTab === 'retention'" class="tab-content">
        <div class="section-header">
          <h2>Retention Policies</h2>
          <button @click="showRetentionModal = true" class="btn-primary">
            <Plus :size="20" />
            New Policy
          </button>
        </div>
        <div class="policies-list">
          <div
            v-for="policy in retentionPolicies"
            :key="policy.id"
            class="policy-card"
          >
            <div class="policy-header">
              <h3>{{ policy.name }}</h3>
              <div class="policy-actions">
                <button @click="editRetentionPolicy(policy)" class="btn-small">
                  <Edit :size="16" />
                  Edit
                </button>
                <button @click="deleteRetentionPolicy(policy)" class="btn-small btn-danger">
                  <Trash2 :size="16" />
                  Delete
                </button>
              </div>
            </div>
            <div class="policy-details">
              <div class="detail-item">
                <span class="label">Duration:</span>
                <span>{{ policy.duration_days }} days</span>
              </div>
              <div class="detail-item">
                <span class="label">Disposition:</span>
                <span>{{ policy.disposition }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Legal Hold:</span>
                <span>{{ policy.legal_hold ? 'Yes' : 'No' }}</span>
              </div>
            </div>
          </div>
          <div v-if="retentionPolicies.length === 0" class="empty-state">
            No retention policies. Create your first policy.
          </div>
        </div>
      </div>

      <!-- OCR/AI Providers Tab -->
      <div v-if="activeTab === 'providers'" class="tab-content">
        <div class="section-header">
          <h2>OCR/AI Providers</h2>
          <button @click="checkProviderHealth" class="btn-secondary">
            <Activity :size="20" />
            Check Health
          </button>
        </div>
        <div v-if="providers" class="providers-config">
          <div class="provider-section">
            <h3>OCR Providers</h3>
            <div class="provider-list">
              <div
                v-for="provider in providers.ocr || []"
                :key="provider.name"
                class="provider-item"
              >
                <div class="provider-info">
                  <h4>{{ provider.name }}</h4>
                  <StatusBadge :status="provider.health || 'unknown'" />
                </div>
                <div class="provider-config">
                  <label>
                    <input type="checkbox" v-model="provider.enabled" />
                    Enabled
                  </label>
                  <div v-if="provider.quota" class="quota-info">
                    Quota: {{ provider.quota.used }} / {{ provider.quota.limit }}
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="provider-section">
            <h3>Embedding Providers</h3>
            <div class="provider-list">
              <div
                v-for="provider in providers.embedding || []"
                :key="provider.name"
                class="provider-item"
              >
                <div class="provider-info">
                  <h4>{{ provider.name }}</h4>
                  <StatusBadge :status="provider.health || 'unknown'" />
                </div>
                <div class="provider-config">
                  <label>
                    <input type="checkbox" v-model="provider.enabled" />
                    Enabled
                  </label>
                </div>
              </div>
            </div>
          </div>
          <div class="provider-section">
            <h3>LLM Providers</h3>
            <div class="provider-list">
              <div
                v-for="provider in providers.llm || []"
                :key="provider.name"
                class="provider-item"
              >
                <div class="provider-info">
                  <h4>{{ provider.name }}</h4>
                  <StatusBadge :status="provider.health || 'unknown'" />
                </div>
                <div class="provider-config">
                  <label>
                    <input type="checkbox" v-model="provider.enabled" />
                    Enabled
                  </label>
                  <div v-if="provider.models" class="models-list">
                    <label>Available Models:</label>
                    <div class="models">
                      <span
                        v-for="model in provider.models"
                        :key="model"
                        class="model-badge"
                      >
                        {{ model }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="section-actions">
            <button @click="saveProviders" class="btn-primary">Save Providers</button>
          </div>
        </div>
        <div v-else class="loading">Loading providers...</div>
      </div>

      <!-- Chatbot Policies Tab -->
      <div v-if="activeTab === 'chatbot'" class="tab-content">
        <div class="section-header">
          <h2>Chatbot Policies</h2>
        </div>
        <div class="chatbot-policies">
          <div
            v-for="policy in chatbotPolicies"
            :key="policy.group_id"
            class="policy-card"
          >
            <div class="policy-header">
              <h3>{{ getGroupName(policy.group_id) }}</h3>
              <button @click="editChatbotPolicy(policy)" class="btn-small">
                <Edit :size="16" />
                Edit
              </button>
            </div>
            <div class="policy-details">
              <div class="detail-item">
                <span class="label">Allowed Sources:</span>
                <span>{{ policy.allowed_sources?.join(', ') || 'All' }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Allow Preview:</span>
                <span>{{ policy.allow_preview ? 'Yes' : 'No' }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Max Tokens:</span>
                <span>{{ policy.max_tokens || 'Unlimited' }}</span>
              </div>
            </div>
          </div>
          <div v-if="chatbotPolicies.length === 0" class="empty-state">
            No chatbot policies configured
          </div>
        </div>
      </div>
    </div>

    <!-- Retention Policy Modal -->
    <Modal
      v-model:show="showRetentionModal"
      :title="editingRetentionPolicy ? 'Edit Retention Policy' : 'Create Retention Policy'"
    >
      <div class="form-group">
        <label>Name *</label>
        <input v-model="retentionForm.name" required />
      </div>
      <div class="form-group">
        <label>Duration (days) *</label>
        <input v-model.number="retentionForm.duration_days" type="number" required />
      </div>
      <div class="form-group">
        <label>Disposition *</label>
        <select v-model="retentionForm.disposition" required>
          <option value="delete">Delete</option>
          <option value="archive">Archive</option>
          <option value="retain">Retain</option>
        </select>
      </div>
      <div class="form-group">
        <label>
          <input type="checkbox" v-model="retentionForm.legal_hold" />
          Legal Hold
        </label>
      </div>
      <template #footer>
        <button
          type="button"
          @click="showRetentionModal = false"
          class="btn-secondary"
        >
          Cancel
        </button>
        <button type="button" @click="saveRetentionPolicy" class="btn-primary">Save</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useSettingsStore } from '../../store/settings'
import { useGroupsStore } from '../../store/groups'
import { settingsAPI } from '../../services/api'
import { Modal, StatusBadge } from '../../components'
import { Plus, Edit, Trash2, Activity } from 'lucide-vue-next'

const settingsStore = useSettingsStore()
const groupsStore = useGroupsStore()

const activeTab = ref('retention')
const retentionPolicies = ref([])
const providers = ref(null)
const chatbotPolicies = ref([])
const showRetentionModal = ref(false)
const editingRetentionPolicy = ref(null)

const tabs = [
  { id: 'retention', label: 'Retention Policies' },
  { id: 'providers', label: 'OCR/AI Providers' },
  { id: 'chatbot', label: 'Chatbot Policies' }
]

const retentionForm = ref({
  name: '',
  duration_days: 30,
  disposition: 'delete',
  legal_hold: false
})

onMounted(async () => {
  await loadRetentionPolicies()
  await loadProviders()
  await loadChatbotPolicies()
  await loadGroups()
})

const loadRetentionPolicies = async () => {
  try {
    await settingsStore.fetchRetentionPolicies()
    retentionPolicies.value = settingsStore.retentionPolicies
  } catch (e) {
    console.error('Failed to load retention policies', e)
  }
}

const loadProviders = async () => {
  try {
    await settingsStore.fetchProviders()
    const rawProviders = settingsStore.providers
    
    // Normalize providers to ensure they are arrays of objects
    if (rawProviders) {
      providers.value = {
        ocr: Array.isArray(rawProviders.ocr) ? rawProviders.ocr : [],
        embedding: Array.isArray(rawProviders.embedding) ? rawProviders.embedding : [],
        llm: Array.isArray(rawProviders.llm) ? rawProviders.llm : [],
        search: Array.isArray(rawProviders.search) ? rawProviders.search : []
      }
    } else {
      providers.value = {
        ocr: [],
        embedding: [],
        llm: [],
        search: []
      }
    }
  } catch (e) {
    console.error('Failed to load providers', e)
    providers.value = {
      ocr: [],
      embedding: [],
      llm: [],
      search: []
    }
  }
}

const loadChatbotPolicies = async () => {
  try {
    await settingsStore.fetchChatbotPolicies()
    chatbotPolicies.value = settingsStore.chatbotPolicies
  } catch (e) {
    console.error('Failed to load chatbot policies', e)
  }
}

const loadGroups = async () => {
  try {
    await groupsStore.fetchGroups()
  } catch (e) {
    console.error('Failed to load groups', e)
  }
}

const editRetentionPolicy = (policy) => {
  editingRetentionPolicy.value = policy
  retentionForm.value = {
    name: policy.name,
    duration_days: policy.duration_days,
    disposition: policy.disposition,
    legal_hold: policy.legal_hold || false
  }
  showRetentionModal.value = true
}

const saveRetentionPolicy = async () => {
  try {
    if (editingRetentionPolicy.value) {
      await settingsStore.updateRetentionPolicy(
        editingRetentionPolicy.value.id,
        retentionForm.value
      )
    } else {
      await settingsStore.createRetentionPolicy(retentionForm.value)
    }
    await loadRetentionPolicies()
    showRetentionModal.value = false
    editingRetentionPolicy.value = null
    retentionForm.value = {
      name: '',
      duration_days: 30,
      disposition: 'delete',
      legal_hold: false
    }
    if (window.$toast) {
      window.$toast.show(
        editingRetentionPolicy.value ? 'Policy updated' : 'Policy created',
        'success'
      )
    }
  } catch (e) {
    console.error('Failed to save retention policy', e)
    if (window.$toast) {
      window.$toast.show('Failed to save retention policy', 'error')
    }
  }
}

const deleteRetentionPolicy = async (policy) => {
  if (confirm(`Delete retention policy "${policy.name}"?`)) {
    try {
      await settingsStore.deleteRetentionPolicy(policy.id)
      await loadRetentionPolicies()
      if (window.$toast) {
        window.$toast.show('Policy deleted', 'success')
      }
    } catch (e) {
      console.error('Failed to delete retention policy', e)
      if (window.$toast) {
        window.$toast.show('Failed to delete retention policy', 'error')
      }
    }
  }
}

const checkProviderHealth = async () => {
  try {
    // This would trigger health checks on backend
    await loadProviders()
    if (window.$toast) {
      window.$toast.show('Health check completed', 'success')
    }
  } catch (e) {
    console.error('Failed to check provider health', e)
    if (window.$toast) {
      window.$toast.show('Failed to check provider health', 'error')
    }
  }
}

const saveProviders = async () => {
  try {
    await settingsStore.updateProviders(providers.value)
    if (window.$toast) {
      window.$toast.show('Providers saved', 'success')
    }
  } catch (e) {
    console.error('Failed to save providers', e)
    if (window.$toast) {
      window.$toast.show('Failed to save providers', 'error')
    }
  }
}

const editChatbotPolicy = (policy) => {
  if (window.$toast) {
    window.$toast.show('Chatbot policy editing not yet implemented', 'info')
  }
}

const getGroupName = (groupId) => {
  const group = groupsStore.groups.find(g => g.id === groupId)
  return group ? group.name : `Group ${groupId}`
}
</script>

<style scoped>
.admin-page {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.settings-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  border-bottom: 2px solid #eee;
}

.tab-btn {
  padding: 0.75rem 1.5rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-weight: 500;
  color: #666;
  transition: all 0.2s;
  margin-bottom: -2px;
}

.tab-btn:hover {
  color: var(--primary);
}

.tab-btn-active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.settings-content {
  max-width: 1000px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.section-header h2 {
  margin: 0;
  color: var(--primary);
}

.policies-list,
.chatbot-policies {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.policy-card {
  background: var(--bg-light);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #eee;
}

.policy-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.policy-header h3 {
  margin: 0;
  color: var(--primary);
}

.policy-actions {
  display: flex;
  gap: 0.5rem;
}

.policy-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.detail-item {
  display: flex;
  gap: 0.5rem;
}

.detail-item .label {
  font-weight: 500;
  color: #666;
}

.providers-config {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.provider-section h3 {
  margin: 0 0 1rem 0;
  color: var(--primary);
}

.provider-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.provider-item {
  background: var(--bg-light);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #eee;
}

.provider-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.provider-info h4 {
  margin: 0;
  color: var(--primary);
}

.provider-config {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.provider-config label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.quota-info {
  font-size: 0.9rem;
  color: #666;
}

.models-list {
  margin-top: 0.5rem;
}

.models-list label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.models {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.model-badge {
  background: white;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  border: 1px solid #ddd;
}

.section-actions {
  margin-top: 2rem;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #666;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.form-group label input[type="checkbox"] {
  width: auto;
  margin-right: 0.5rem;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #666;
}
</style>
