<template>
  <div class="system-config-page">
    <div class="page-header">
      <h1>{{ $t('admin.systemConfig.title') }}</h1>
      <div class="header-actions">
        <button @click="refreshConfig" class="btn-secondary" :disabled="loading">
          <RefreshCw :size="16" :class="{ 'spinning': loading }" />
          {{ $t('common.refresh') }}
        </button>
        <button @click="saveAll" class="btn-primary" :disabled="loading || !hasChanges">
          <Save :size="16" />
          {{ $t('admin.systemConfig.saveAllChanges') }}
        </button>
      </div>
    </div>

    <div v-if="error" class="error-banner">
      <AlertCircle :size="20" />
      <span>{{ error }}</span>
    </div>

    <div v-if="success" class="success-banner">
      <CheckCircle :size="20" />
      <span>{{ success }}</span>
    </div>

    <div class="config-warning">
      <AlertTriangle :size="20" />
      <div>
        <strong>{{ $t('admin.systemConfig.warning') }}:</strong> {{ $t('admin.systemConfig.warningMessage') }}
      </div>
    </div>

    <div v-if="loading && !config" class="loading-state">
      <Loader2 :size="32" class="spinning" />
      <p>{{ $t('admin.systemConfig.loadingConfiguration') }}</p>
    </div>

    <div v-else class="config-content">
      <div class="config-sidebar">
        <div class="category-list">
          <button
            v-for="cat in categories"
            :key="cat.id"
            @click="selectedCategory = cat.id"
            :class="['category-btn', { active: selectedCategory === cat.id }]"
          >
            {{ cat.name }}
          </button>
        </div>
      </div>

      <div class="config-main">
        <div v-for="cat in categories" :key="cat.id" v-show="selectedCategory === cat.id">
          <h2>{{ cat.name }}</h2>
          <p class="category-description">{{ cat.description }}</p>

          <div class="config-items">
            <div
              v-for="(item, key) in getConfigByCategory(cat.id)"
              :key="key"
              class="config-item"
            >
              <div class="config-item-header">
                <label :for="`config-${key}`">{{ formatKey(key) }}</label>
                <span v-if="item.sensitive" class="sensitive-badge">{{ $t('admin.systemConfig.sensitive') }}</span>
              </div>
              <div class="config-item-input">
                <input
                  v-if="item.type === 'string' || item.type === 'integer'"
                  :id="`config-${key}`"
                  :type="item.type === 'integer' ? 'number' : 'text'"
                  v-model="editedConfig[key]"
                  :disabled="item.sensitive && item.value === '***'"
                  :placeholder="item.sensitive ? $t('admin.systemConfig.enterNewValueToUpdate') : ''"
                  class="config-input"
                  @input="markChanged(key)"
                />
                <select
                  v-else-if="item.type === 'boolean'"
                  :id="`config-${key}`"
                  v-model="editedConfig[key]"
                  class="config-input"
                  @change="markChanged(key)"
                >
                  <option :value="true">{{ $t('admin.systemConfig.true') }}</option>
                  <option :value="false">{{ $t('admin.systemConfig.false') }}</option>
                </select>
                <div v-else class="config-value-display">{{ item.value }}</div>
              </div>
              <div v-if="item.sensitive && item.value === '***'" class="config-hint">
                {{ $t('admin.systemConfig.currentValueHiddenHint') }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { systemConfigAPI } from '../../services/api'
import {
  RefreshCw, Save, AlertCircle, CheckCircle, AlertTriangle, Loader2
} from 'lucide-vue-next'

const { t } = useI18n()

const config = ref(null)
const editedConfig = ref({})
const changedKeys = ref(new Set())
const loading = ref(false)
const error = ref(null)
const success = ref(null)
const selectedCategory = ref('database')
const categories = ref([])

const hasChanges = computed(() => changedKeys.value.size > 0)

const getConfigByCategory = (categoryId) => {
  if (!config.value) return {}
  const filtered = {}
  for (const [key, value] of Object.entries(config.value.config)) {
    if (value.category === categoryId) {
      filtered[key] = value
    }
  }
  return filtered
}

const formatKey = (key) => {
  return key.split('_').map(word => 
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ')
}

const markChanged = (key) => {
  changedKeys.value.add(key)
  success.value = null
}

const loadConfig = async () => {
  loading.value = true
  error.value = null
  try {
    const [configRes, categoriesRes] = await Promise.all([
      systemConfigAPI.get(),
      systemConfigAPI.getCategories()
    ])
    
    if (configRes.is_success) {
      config.value = configRes.data
      // Initialize edited config with current values
      editedConfig.value = {}
      for (const [key, value] of Object.entries(config.value.config)) {
        editedConfig.value[key] = value.value
      }
    }
    
    if (categoriesRes.is_success) {
      categories.value = categoriesRes.data.categories
      if (categories.value.length > 0) {
        selectedCategory.value = categories.value[0].id
      }
    }
  } catch (e) {
    console.error('Failed to load config', e)
    error.value = e.response?.data?.message || t('admin.systemConfig.failedToLoadConfiguration')
  } finally {
    loading.value = false
  }
}

const refreshConfig = async () => {
  changedKeys.value.clear()
  editedConfig.value = {}
  await loadConfig()
}

const saveAll = async () => {
  if (changedKeys.value.size === 0) return
  
  loading.value = true
  error.value = null
  success.value = null
  
  try {
    // Build config object with only changed values
    const configsToUpdate = {}
    for (const key of changedKeys.value) {
      const value = editedConfig.value[key]
      // Convert boolean to string for .env file
      if (typeof value === 'boolean') {
        configsToUpdate[key.toUpperCase()] = value.toString().toLowerCase()
      } else {
        configsToUpdate[key.toUpperCase()] = value
      }
    }
    
    const res = await systemConfigAPI.updateBulk(configsToUpdate)
    if (res.is_success) {
      success.value = t('admin.systemConfig.successfullyUpdated', { count: res.data.updated_keys.length })
      changedKeys.value.clear()
      await loadConfig() // Reload to get updated values
    } else {
      error.value = res.message || t('admin.systemConfig.failedToUpdateConfiguration')
    }
  } catch (e) {
    console.error('Failed to save config', e)
    error.value = e.response?.data?.message || t('admin.systemConfig.failedToSaveConfiguration')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.system-config-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 2rem;
  font-weight: 700;
  margin: 0;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.02em;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

.error-banner,
.success-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.error-banner {
  background: #fee;
  color: #c33;
  border: 1px solid #fcc;
}

.success-banner {
  background: #efe;
  color: #3c3;
  border: 1px solid #cfc;
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

.loading-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #666;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.config-content {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 2rem;
}

.config-sidebar {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  height: fit-content;
  position: sticky;
  top: 2rem;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.category-btn {
  padding: 0.75rem 1rem;
  text-align: left;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  color: #666;
  font-weight: 500;
}

.category-btn:hover {
  background: #f5f5f5;
}

.category-btn.active {
  background: var(--primary-light);
  color: var(--primary);
  font-weight: 600;
}

.config-main {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.config-main h2 {
  margin: 0 0 0.5rem 0;
  color: var(--primary);
}

.category-description {
  color: #666;
  margin-bottom: 2rem;
  font-size: 0.9rem;
}

.config-items {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.config-item {
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #eee;
}

.config-item:last-child {
  border-bottom: none;
}

.config-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.config-item-header label {
  font-weight: 600;
  color: #333;
  font-size: 0.95rem;
}

.sensitive-badge {
  background: #fee;
  color: #c33;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.config-item-input {
  margin-bottom: 0.5rem;
}

.config-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.9rem;
}

.config-input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.config-value-display {
  padding: 0.75rem;
  background: #f5f5f5;
  border-radius: 6px;
  color: #666;
  font-family: monospace;
}

.config-hint {
  font-size: 0.85rem;
  color: #666;
  font-style: italic;
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

