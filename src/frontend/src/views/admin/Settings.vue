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
        <!-- Document Deletion Settings Section -->
        <div class="deletion-settings-section">
          <h2>Document Deletion Settings</h2>
          <div class="form-section">
            <div class="form-group">
              <label for="purge_grace_period">Purge Grace Period (days) *</label>
              <input
                id="purge_grace_period"
                v-model.number="purgeGracePeriodForm.days"
                type="number"
                min="0"
                max="365"
                placeholder="1"
              />
              <small>Number of days before soft-deleted documents are permanently purged. Default: 1 day. Min: 0, Max: 365.</small>
            </div>
            <div class="form-actions">
              <button @click="savePurgeGracePeriod" class="btn-primary" :disabled="savingPurgeGracePeriod">
                <Save :size="16" />
                {{ savingPurgeGracePeriod ? 'Saving...' : 'Save Settings' }}
              </button>
              <button @click="loadPurgeGracePeriod" class="btn-secondary" :disabled="savingPurgeGracePeriod">
                <RefreshCw :size="16" />
                Reset
              </button>
            </div>
          </div>
        </div>

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
        
        <!-- OCR Settings Section -->
        <div class="ocr-settings-section">
          <h3>OCR Settings</h3>
          <div class="form-section">
            <div class="form-group">
              <label for="ocr_provider">OCR Provider *</label>
              <select id="ocr_provider" v-model="ocrForm.provider">
                <option value="paddle">PaddleOCR</option>
                <option value="tesseract">Tesseract</option>
                <option value="easyocr">EasyOCR</option>
                <option value="auto">Auto (Try all)</option>
              </select>
              <small>Select the OCR provider to use for document processing</small>
            </div>
            
            <div class="form-group">
              <label>Languages *</label>
              <div class="language-checkboxes">
                <label v-for="lang in availableLanguages" :key="lang.code" class="language-checkbox">
                  <input 
                    type="checkbox" 
                    :value="lang.code" 
                    v-model="ocrForm.languages"
                  />
                  <span>{{ lang.name }} ({{ lang.code }})</span>
                </label>
              </div>
              <small>Select languages for OCR recognition</small>
            </div>
            
            <div class="form-actions">
              <button @click="saveOCRSettings" class="btn-primary" :disabled="savingOCR">
                <Save :size="16" />
                {{ savingOCR ? 'Saving...' : 'Save OCR Settings' }}
              </button>
              <button @click="loadOCRSettings" class="btn-secondary" :disabled="savingOCR">
                <RefreshCw :size="16" />
                Reset
              </button>
            </div>
          </div>
        </div>
        
        <div v-if="providers" class="providers-config">
          <div class="provider-section">
            <h3>OCR Providers</h3>
            <div class="provider-list">
              <div
                v-for="provider in providers.ocr || []"
                :key="provider.name"
                class="provider-item"
                :class="{ 'provider-error': provider.health === 'error' || provider.health === 'system_not_found' }"
              >
                <div class="provider-info">
                  <h4>{{ provider.name }}</h4>
                  <StatusBadge :status="provider.health || 'unknown'" />
                  <div v-if="provider.description && (provider.health === 'error' || provider.health === 'system_not_found')" class="provider-error-message">
                    <AlertTriangle :size="16" />
                    <span>{{ provider.description }}</span>
                  </div>
                </div>
                <div class="provider-config">
                  <label>
                    <input type="checkbox" v-model="provider.enabled" />
                    Enabled
                  </label>
                  <div v-if="provider.quota" class="quota-info">
                    Quota: {{ provider.quota.used }} / {{ provider.quota.limit }}
                  </div>
                  <div v-if="provider.health === 'error' || provider.health === 'system_not_found'" class="provider-actions">
                    <button 
                      v-if="provider.can_auto_fix" 
                      @click="fixProvider(provider.name)" 
                      class="btn-small btn-primary"
                      :disabled="fixingProvider === provider.name"
                    >
                      {{ fixingProvider === provider.name ? 'Fixing...' : 'Auto Fix' }}
                    </button>
                    <button 
                      @click="showFixGuide(provider)" 
                      class="btn-small btn-secondary"
                    >
                      View Guide
                    </button>
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

      <!-- LLM Settings Tab -->
      <div v-if="activeTab === 'llm'" class="tab-content">
        <div class="section-header">
          <h2>LLM Settings (Ollama)</h2>
        </div>
        <div class="llm-settings-form">
          <div class="config-warning">
            <AlertTriangle :size="20" />
            <div>
              <strong>Note:</strong> Changes require server restart to take effect. 
              API key is optional for local Ollama instances.
            </div>
          </div>
          
          <div v-if="llmSettings" class="form-section">
            <div class="form-group">
              <label for="ollama_base_url">Ollama Base URL *</label>
              <input
                id="ollama_base_url"
                v-model="llmForm.ollama_base_url"
                type="text"
                placeholder="http://localhost:11434"
              />
              <small>Use http://ollama:11434 in docker, http://localhost:11434 for local</small>
            </div>
            
            <div class="form-group">
              <label for="ollama_api_key">Ollama API Key (Optional)</label>
              <input
                id="ollama_api_key"
                v-model="llmForm.ollama_api_key"
                type="password"
                placeholder="Leave empty for local Ollama"
              />
              <small>Current value is hidden. Enter new value to update.</small>
            </div>
            
            <div class="form-group">
              <label for="ollama_llm_model">LLM Model *</label>
              <input
                id="ollama_llm_model"
                v-model="llmForm.ollama_llm_model"
                type="text"
                placeholder="llama3.2"
              />
              <small>Model name for chat (e.g., llama3.2, mistral, qwen2.5)</small>
            </div>
            
            <div class="form-group">
              <label for="ollama_embedding_model">Embedding Model *</label>
              <input
                id="ollama_embedding_model"
                v-model="llmForm.ollama_embedding_model"
                type="text"
                placeholder="nomic-text-embedding"
              />
              <small>Model name for embeddings (default: nomic-text-embedding)</small>
            </div>
            
            <div class="form-actions">
              <button @click="saveLLMSettings" class="btn-primary" :disabled="savingLLM">
                <Save :size="16" />
                {{ savingLLM ? 'Saving...' : 'Save LLM Settings' }}
              </button>
              <button @click="loadLLMSettings" class="btn-secondary" :disabled="savingLLM">
                <RefreshCw :size="16" />
                Reset
              </button>
            </div>
          </div>
          
          <div v-else class="loading">Loading LLM settings...</div>
        </div>
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

    <!-- Fix Guide Modal -->
    <Modal
      v-model:show="showFixGuideModal"
      :title="fixGuideModalTitle"
      size="large"
    >
      <div v-if="currentFixGuide" class="fix-guide-content">
        <div v-if="currentFixGuide.description" class="fix-guide-description">
          <p>{{ currentFixGuide.description }}</p>
        </div>
        
        <div v-if="currentFixGuide.steps && currentFixGuide.steps.length > 0" class="fix-guide-steps">
          <h4>Steps to Fix:</h4>
          <ol class="steps-list">
            <li v-for="step in currentFixGuide.steps" :key="step.step" class="step-item">
              <div class="step-header">
                <strong>{{ step.step }}. {{ step.title }}</strong>
              </div>
              <div class="step-description">{{ step.description }}</div>
              <div v-if="step.action" class="step-action">
                <strong>Action:</strong> {{ step.action }}
              </div>
              <div v-if="step.command" class="step-command">
                <code>{{ step.command }}</code>
                <button 
                  @click="copyToClipboard(step.command)" 
                  class="btn-copy"
                  title="Copy to clipboard"
                >
                  Copy
                </button>
              </div>
            </li>
          </ol>
        </div>

        <div v-if="currentFixGuide.download_link" class="fix-guide-download">
          <h4>Download Link:</h4>
          <a :href="currentFixGuide.download_link" target="_blank" rel="noopener noreferrer">
            {{ currentFixGuide.download_link }}
          </a>
        </div>

        <div v-if="currentFixGuide.verify_command" class="fix-guide-verify">
          <h4>Verify Installation:</h4>
          <code>{{ currentFixGuide.verify_command }}</code>
          <button 
            @click="copyToClipboard(currentFixGuide.verify_command)" 
            class="btn-copy"
            title="Copy to clipboard"
          >
            Copy
          </button>
        </div>
      </div>

      <template #footer>
        <div class="modal-footer-actions">
          <button 
            v-if="currentProvider && currentProvider.can_auto_fix" 
            @click="fixProvider(currentProvider.name)" 
            class="btn-primary"
            :disabled="fixingProvider === currentProvider.name"
          >
            {{ fixingProvider === currentProvider.name ? 'Fixing...' : 'Auto Fix' }}
          </button>
          <button @click="showFixGuideModal = false" class="btn-secondary">
            Close
          </button>
        </div>
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
import { Plus, Edit, Trash2, Activity, Save, RefreshCw, AlertTriangle } from 'lucide-vue-next'

const settingsStore = useSettingsStore()
const groupsStore = useGroupsStore()

const activeTab = ref('retention')
const retentionPolicies = ref([])
const providers = ref(null)
const chatbotPolicies = ref([])
const showRetentionModal = ref(false)
const editingRetentionPolicy = ref(null)
const llmSettings = ref(null)
const llmForm = ref({
  ollama_base_url: '',
  ollama_api_key: '',
  ollama_llm_model: '',
  ollama_embedding_model: ''
})
const savingLLM = ref(false)
const ocrSettings = ref(null)

const ocrForm = ref({
  provider: 'paddle',
  languages: ['en', 'vi']
})
const savingOCR = ref(false)

// Purge grace period settings
const purgeGracePeriodForm = ref({
  days: 1
})
const savingPurgeGracePeriod = ref(false)

// Fix guide modal
const showFixGuideModal = ref(false)
const currentFixGuide = ref(null)
const currentProvider = ref(null)
const fixingProvider = ref(null)
const fixGuideModalTitle = ref('Fix Guide')

const tabs = [
  { id: 'retention', label: 'Retention Policies' },
  { id: 'providers', label: 'OCR/AI Providers' },
  { id: 'llm', label: 'LLM Settings' },
  { id: 'chatbot', label: 'Chatbot Policies' }
]

const availableLanguages = [
  { code: 'en', name: 'English' },
  { code: 'vi', name: 'Vietnamese' },
  { code: 'ja', name: 'Japanese' },
  { code: 'ko', name: 'Korean' },
  { code: 'zh', name: 'Chinese' }
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
  await loadLLMSettings()
  await loadOCRSettings()
  await loadPurgeGracePeriod()
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

const loadLLMSettings = async () => {
  try {
    const res = await settingsAPI.llm.get()
    if (res.is_success) {
      llmSettings.value = res.data
      llmForm.value = {
        ollama_base_url: res.data.ollama_base_url || '',
        ollama_api_key: '', // Always empty, user needs to enter new value
        ollama_llm_model: res.data.ollama_llm_model || '',
        ollama_embedding_model: res.data.ollama_embedding_model || ''
      }
    }
  } catch (e) {
    console.error('Failed to load LLM settings', e)
    if (window.$toast) {
      window.$toast.show('Failed to load LLM settings', 'error')
    }
  }
}

const saveLLMSettings = async () => {
  savingLLM.value = true
  try {
    // Only send fields that have values
    const payload = {}
    if (llmForm.value.ollama_base_url) payload.ollama_base_url = llmForm.value.ollama_base_url
    if (llmForm.value.ollama_api_key) payload.ollama_api_key = llmForm.value.ollama_api_key
    if (llmForm.value.ollama_llm_model) payload.ollama_llm_model = llmForm.value.ollama_llm_model
    if (llmForm.value.ollama_embedding_model) payload.ollama_embedding_model = llmForm.value.ollama_embedding_model
    
    const res = await settingsAPI.llm.update(payload)
    if (res.is_success) {
      if (window.$toast) {
        window.$toast.show('LLM settings saved. Server restart required.', 'success')
      }
      await loadLLMSettings()
    }
  } catch (e) {
    console.error('Failed to save LLM settings', e)
    if (window.$toast) {
      window.$toast.show('Failed to save LLM settings', 'error')
    }
  } finally {
    savingLLM.value = false
  }
}

const loadOCRSettings = async () => {
  try {
    await settingsStore.fetchOCRSettings()
    ocrSettings.value = settingsStore.ocrSettings
    if (ocrSettings.value) {
      ocrForm.value = {
        provider: ocrSettings.value.provider || 'paddle',
        languages: ocrSettings.value.languages || ['en', 'vi']
      }
    } else {
      // Initialize with defaults if no settings in DB
      ocrForm.value = {
        provider: 'paddle',
        languages: ['en', 'vi']
      }
    }
  } catch (e) {
    console.error('Failed to load OCR settings', e)
    // Initialize with defaults on error
    ocrForm.value = {
      provider: 'paddle',
      languages: ['en', 'vi']
    }
    if (window.$toast) {
      window.$toast.show('Failed to load OCR settings', 'error')
    }
  }
}

const saveOCRSettings = async () => {
  savingOCR.value = true
  try {
    const payload = {
      provider: ocrForm.value.provider,
      languages: ocrForm.value.languages
    }
    
    await settingsStore.updateOCRSettings(payload)
    if (window.$toast) {
      window.$toast.show('OCR settings saved', 'success')
    }
    await loadOCRSettings()
  } catch (e) {
    console.error('Failed to save OCR settings', e)
    if (window.$toast) {
      window.$toast.show('Failed to save OCR settings', 'error')
    }
  } finally {
    savingOCR.value = false
  }
}

const showFixGuide = (provider) => {
  currentProvider.value = provider
  if (provider.fix_guide) {
    currentFixGuide.value = provider.fix_guide
    fixGuideModalTitle.value = `Fix Guide: ${provider.name}`
  } else {
    // Fallback: create a basic guide from description
    currentFixGuide.value = {
      title: `Fix ${provider.name}`,
      description: provider.description || 'No fix guide available',
      steps: []
    }
    fixGuideModalTitle.value = `Fix Guide: ${provider.name}`
  }
  showFixGuideModal.value = true
}

const fixProvider = async (providerName) => {
  fixingProvider.value = providerName
  try {
    await settingsStore.fixProvider(providerName)
    if (window.$toast) {
      window.$toast.show(`${providerName} fix completed successfully`, 'success')
    }
    // Refresh providers to see updated health
    await loadProviders()
    // Close modal if open
    if (showFixGuideModal.value && currentProvider.value?.name === providerName) {
      showFixGuideModal.value = false
    }
  } catch (e) {
    console.error(`Failed to fix ${providerName}`, e)
    const errorMsg = e.response?.data?.message || e.message || `Failed to fix ${providerName}`
    if (window.$toast) {
      window.$toast.show(errorMsg, 'error')
    }
  } finally {
    fixingProvider.value = null
  }
}

const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    if (window.$toast) {
      window.$toast.show('Copied to clipboard', 'success')
    }
  } catch (e) {
    console.error('Failed to copy to clipboard', e)
    if (window.$toast) {
      window.$toast.show('Failed to copy to clipboard', 'error')
    }
  }
}

const loadPurgeGracePeriod = async () => {
  try {
    const res = await settingsAPI.purgeGracePeriod.get()
    if (res.is_success && res.data) {
      purgeGracePeriodForm.value = {
        days: res.data.days || 1
      }
    }
  } catch (e) {
    console.error('Failed to load purge grace period', e)
    if (window.$toast) {
      window.$toast.show('Failed to load purge grace period settings', 'error')
    }
  }
}

const savePurgeGracePeriod = async () => {
  savingPurgeGracePeriod.value = true
  try {
    if (purgeGracePeriodForm.value.days < 0 || purgeGracePeriodForm.value.days > 365) {
      if (window.$toast) {
        window.$toast.show('Purge grace period must be between 0 and 365 days', 'error')
      }
      return
    }
    
    const res = await settingsAPI.purgeGracePeriod.update(purgeGracePeriodForm.value.days)
    if (res.is_success) {
      if (window.$toast) {
        window.$toast.show('Purge grace period saved successfully', 'success')
      }
      await loadPurgeGracePeriod()
    } else {
      if (window.$toast) {
        window.$toast.show(res.message || 'Failed to save purge grace period', 'error')
      }
    }
  } catch (e) {
    console.error('Failed to save purge grace period', e)
    if (window.$toast) {
      window.$toast.show('Failed to save purge grace period', 'error')
    }
  } finally {
    savingPurgeGracePeriod.value = false
  }
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

.llm-settings-form {
  max-width: 800px;
}

.config-warning {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  margin-bottom: 2rem;
  color: #856404;
}

.config-warning strong {
  display: block;
  margin-bottom: 0.25rem;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 600;
  color: #333;
  font-size: 0.95rem;
}

.form-group input {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.9rem;
  font-family: inherit;
}

.form-group input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
}

.form-group small {
  font-size: 0.85rem;
  color: #666;
  font-style: italic;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
  padding-top: 1.5rem;
  border-top: 1px solid #eee;
}

.form-actions button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.form-actions .btn-primary {
  background: var(--primary);
  color: white;
}

.form-actions .btn-primary:hover:not(:disabled) {
  background: var(--primary-dark);
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.form-actions .btn-secondary {
  background: #f5f5f5;
  color: #333;
}

.form-actions .btn-secondary:hover:not(:disabled) {
  background: #e5e5e5;
}

.provider-error {
  border-left: 4px solid #ff6b6b;
  background: #fff5f5;
}

.provider-error-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #fff3cd;
  border-radius: 4px;
  color: #856404;
  font-size: 0.85rem;
}

.provider-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.btn-small {
  padding: 0.4rem 0.8rem;
  font-size: 0.85rem;
  border-radius: 4px;
  border: 1px solid #ddd;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-small.btn-primary {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.btn-small.btn-primary:hover:not(:disabled) {
  background: var(--primary-dark);
}

.btn-small.btn-secondary {
  background: #f5f5f5;
  color: #333;
}

.btn-small.btn-secondary:hover:not(:disabled) {
  background: #e5e5e5;
}

.btn-small:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.fix-guide-content {
  max-height: 70vh;
  overflow-y: auto;
  padding: 1rem 0;
}

.fix-guide-description {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 6px;
}

.fix-guide-steps {
  margin-bottom: 1.5rem;
}

.fix-guide-steps h4 {
  margin-bottom: 1rem;
  color: #333;
}

.steps-list {
  list-style: none;
  padding: 0;
  counter-reset: step-counter;
}

.step-item {
  counter-increment: step-counter;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid var(--primary);
}

.step-header {
  margin-bottom: 0.5rem;
  color: #333;
}

.step-description {
  margin-bottom: 0.5rem;
  color: #666;
  font-size: 0.9rem;
}

.step-action {
  margin-bottom: 0.5rem;
  color: #555;
  font-size: 0.9rem;
}

.step-command {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: #2d2d2d;
  border-radius: 4px;
  color: #f8f8f2;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
}

.step-command code {
  flex: 1;
  color: #f8f8f2;
  background: transparent;
  padding: 0;
}

.btn-copy {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  background: #444;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-copy:hover {
  background: #555;
}

.fix-guide-download,
.fix-guide-verify {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #e7f3ff;
  border-radius: 6px;
}

.fix-guide-download h4,
.fix-guide-verify h4 {
  margin-bottom: 0.5rem;
  color: #333;
}

.fix-guide-download a {
  color: var(--primary);
  text-decoration: none;
  word-break: break-all;
}

.fix-guide-download a:hover {
  text-decoration: underline;
}

.fix-guide-verify {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.fix-guide-verify code {
  flex: 1;
  padding: 0.5rem;
  background: #2d2d2d;
  color: #f8f8f2;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
}

.modal-footer-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

.form-actions button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ocr-settings-section {
  margin-bottom: 3rem;
  padding: 1.5rem;
  background: var(--bg-light);
  border-radius: 8px;
  border: 1px solid #eee;
}

.ocr-settings-section h3 {
  margin: 0 0 1.5rem 0;
  color: var(--primary);
}

.language-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-top: 0.5rem;
}

.language-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.language-checkbox:hover {
  border-color: var(--primary);
  background: #f9f9f9;
}

.language-checkbox input[type="checkbox"] {
  width: auto;
  margin: 0;
  cursor: pointer;
}

.language-checkbox input[type="checkbox"]:checked + span {
  font-weight: 600;
  color: var(--primary);
}

.deletion-settings-section {
  margin-bottom: 3rem;
  padding: 1.5rem;
  background: var(--bg-light);
  border-radius: 8px;
  border: 1px solid #eee;
}

.deletion-settings-section h2 {
  margin: 0 0 1.5rem 0;
  color: var(--primary);
}
</style>
