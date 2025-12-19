<template>
  <div class="admin-page">
    <h1 class="page-header">{{ $t('admin.settings.title') }}</h1>

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
          <h2>{{ $t('admin.settings.documentDeletionSettings') }}</h2>
          <div class="form-section">
            <div class="form-group">
              <label for="purge_grace_period">{{ $t('admin.settings.purgeGracePeriod') }} *</label>
              <input
                id="purge_grace_period"
                v-model.number="purgeGracePeriodForm.days"
                type="number"
                min="0"
                max="365"
                :placeholder="$t('admin.settings.purgeGracePeriodPlaceholder')"
              />
              <small>{{ $t('admin.settings.purgeGracePeriodHint') }}</small>
            </div>
            <div class="form-actions">
              <button @click="savePurgeGracePeriod" class="btn-primary" :disabled="savingPurgeGracePeriod">
                <Save :size="16" />
                {{ savingPurgeGracePeriod ? $t('admin.settings.saving') : $t('admin.settings.saveSettings') }}
              </button>
              <button @click="loadPurgeGracePeriod" class="btn-secondary" :disabled="savingPurgeGracePeriod">
                <RefreshCw :size="16" />
                {{ $t('common.refresh') }}
              </button>
            </div>
          </div>
        </div>

        <div class="section-header">
          <h2>{{ $t('admin.settings.retentionPolicies') }}</h2>
          <button @click="showRetentionModal = true" class="btn-primary">
            <Plus :size="20" />
            {{ $t('admin.settings.createPolicy') }}
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
                  {{ $t('common.edit') }}
                </button>
                <button @click="deleteRetentionPolicy(policy)" class="btn-small btn-danger">
                  <Trash2 :size="16" />
                  {{ $t('common.delete') }}
                </button>
              </div>
            </div>
            <div class="policy-details">
              <div class="detail-item">
                <span class="label">{{ $t('admin.settings.duration') }}:</span>
                <span>{{ policy.duration_days }} {{ $t('upload.days') }}</span>
              </div>
              <div class="detail-item">
                <span class="label">{{ $t('admin.settings.disposition') }}:</span>
                <span>{{ policy.disposition }}</span>
              </div>
              <div class="detail-item">
                <span class="label">{{ $t('admin.settings.legalHold') }}:</span>
                <span>{{ policy.legal_hold ? $t('common.yes') : $t('common.no') }}</span>
              </div>
            </div>
          </div>
          <div v-if="retentionPolicies.length === 0" class="empty-state">
            {{ $t('admin.settings.noRetentionPolicies') }}
          </div>
        </div>
      </div>

      <!-- OCR/AI Providers Tab -->
      <div v-if="activeTab === 'providers'" class="tab-content">
        <div class="section-header">
          <h2>{{ $t('admin.settings.ocrProviders') }}</h2>
          <button @click="checkProviderHealth" class="btn-secondary">
            <Activity :size="20" />
            {{ $t('admin.settings.checkHealth') }}
          </button>
        </div>
        
        <!-- OCR Settings Section -->
        <div class="ocr-settings-section">
          <h3>{{ $t('admin.settings.ocrSettings') }}</h3>
          <div class="form-section">
            <div class="form-group">
              <label for="ocr_provider">{{ $t('admin.settings.ocrProvider') }} *</label>
              <select id="ocr_provider" v-model="ocrForm.provider" disabled>
                <option value="tesseract">{{ $t('admin.settings.ocrProviderTesseract') }}</option>
              </select>
              <small>{{ $t('admin.settings.selectOCRProvider') }} (Only Tesseract is supported)</small>
            </div>
            
            <div class="form-group">
              <label>{{ $t('admin.settings.languages') }} *</label>
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
              <small>{{ $t('admin.settings.selectLanguages') }}</small>
            </div>
            
            <div class="form-actions">
              <button @click="saveOCRSettings" class="btn-primary" :disabled="savingOCR">
                <Save :size="16" />
                {{ savingOCR ? $t('admin.settings.saving') : $t('admin.settings.saveOCRSettings') }}
              </button>
              <button @click="loadOCRSettings" class="btn-secondary" :disabled="savingOCR">
                <RefreshCw :size="16" />
                {{ $t('common.refresh') }}
              </button>
            </div>
          </div>
        </div>
        
        <div v-if="providers" class="providers-config">
          <div class="provider-section">
            <h3>{{ $t('admin.settings.ocrProvidersSection') }}</h3>
            <div class="provider-list">
              <div
                v-for="provider in (providers.ocr || []).filter(p => p.name === 'tesseract')"
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
                    <input type="checkbox" v-model="provider.enabled" disabled />
                    {{ $t('admin.settings.enabled') }} (Always enabled)
                  </label>
                  <div v-if="provider.quota" class="quota-info">
                    {{ $t('admin.settings.quota') }}: {{ provider.quota.used }} / {{ provider.quota.limit }}
                  </div>
                  <div v-if="provider.health === 'error' || provider.health === 'system_not_found'" class="provider-actions">
                    <button 
                      @click="showFixGuide(provider)" 
                      class="btn-small btn-secondary"
                    >
                      {{ $t('admin.settings.viewGuide') }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="provider-section">
            <h3>{{ $t('admin.settings.embeddingProvidersSection') }}</h3>
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
                    {{ $t('admin.settings.enabled') }}
                  </label>
                </div>
              </div>
            </div>
          </div>
          <div class="provider-section">
            <h3>{{ $t('admin.settings.llmProvidersSection') }}</h3>
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
                    {{ $t('admin.settings.enabled') }}
                  </label>
                  <div v-if="provider.models" class="models-list">
                    <label>{{ $t('admin.settings.available') }} {{ $t('admin.settings.llmModelsSection') }}:</label>
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
            <button @click="saveProviders" class="btn-primary">{{ $t('admin.settings.saveProviders') }}</button>
          </div>
        </div>
        <div v-else class="loading">{{ $t('admin.settings.loadingProviders') }}</div>
      </div>

      <!-- LLM Settings Tab -->
      <div v-if="activeTab === 'llm'" class="tab-content">
        <div class="section-header">
          <h2>{{ $t('admin.settings.llmSettingsTitle') }}</h2>
        </div>
        <div class="llm-settings-form">
          <div class="config-warning">
            <AlertTriangle :size="20" />
            <div>
              <strong>{{ $t('admin.settings.note') }}:</strong> {{ $t('admin.settings.changesRequireRestart') }}
            </div>
          </div>
          
          <div v-if="llmSettings" class="form-section">
            <div class="form-group">
              <label for="ollama_base_url">{{ $t('admin.settings.ollamaBaseUrl') }} *</label>
              <input
                id="ollama_base_url"
                v-model="llmForm.ollama_base_url"
                type="text"
                :placeholder="$t('admin.settings.ollamaBaseUrlPlaceholder')"
              />
              <small>{{ $t('admin.settings.ollamaBaseUrlHint') }}</small>
            </div>
            
            <div class="form-group">
              <label for="ollama_api_key">{{ $t('admin.settings.ollamaApiKey') }}</label>
              <input
                id="ollama_api_key"
                v-model="llmForm.ollama_api_key"
                type="password"
                :placeholder="$t('admin.settings.ollamaApiKeyPlaceholder')"
              />
              <small>{{ $t('admin.settings.currentValueHidden') }}</small>
            </div>
            
            <div class="form-group">
              <label for="ollama_llm_model">{{ $t('admin.settings.ollamaLlmModel') }} *</label>
              <select
                id="ollama_llm_model"
                v-model="llmForm.ollama_llm_model"
              >
                <option value="">{{ $t('admin.settings.selectLlmModel') }}</option>
                <option
                  v-for="model in availableLLMModels"
                  :key="model.name"
                  :value="model.name"
                >
                  {{ model.name }}{{ model.is_current_llm ? ` (${$t('admin.settings.current')})` : '' }}
                </option>
              </select>
              <small>{{ $t('admin.settings.selectLlmModelHint') }}</small>
            </div>
            
            <div class="form-group">
              <label for="ollama_embedding_model">{{ $t('admin.settings.ollamaEmbeddingModel') }} *</label>
              <select
                id="ollama_embedding_model"
                v-model="llmForm.ollama_embedding_model"
              >
                <option value="">{{ $t('admin.settings.selectEmbeddingModel') }}</option>
                <option
                  v-for="model in availableEmbeddingModels"
                  :key="model.name"
                  :value="model.name"
                >
                  {{ model.name }}{{ model.is_current_embedding ? ` (${$t('admin.settings.current')})` : '' }}
                </option>
              </select>
              <small>{{ $t('admin.settings.selectEmbeddingModelHint') }}</small>
            </div>
            
            <div class="form-actions">
              <button @click="saveLLMSettings" class="btn-primary" :disabled="savingLLM">
                <Save :size="16" />
                {{ savingLLM ? $t('admin.settings.saving') : $t('admin.settings.saveLlmSettings') }}
              </button>
              <button @click="loadLLMSettings" class="btn-secondary" :disabled="savingLLM">
                <RefreshCw :size="16" />
                {{ $t('admin.settings.reset') }}
              </button>
            </div>
          </div>
          
          <div v-else class="loading">{{ $t('admin.settings.loadingLlmSettings') }}</div>
        </div>

        <!-- Ollama Models Management Section -->
        <div class="ollama-models-section">
          <div class="section-header">
            <h2>{{ $t('admin.settings.ollamaModels') }}</h2>
            <button @click="loadOllamaModels" class="btn-secondary" :disabled="loadingModels">
              <RefreshCw :size="20" :class="{ 'spinning': loadingModels }" />
              {{ $t('common.refresh') }}
            </button>
          </div>

          <div v-if="!ollamaConnected" class="warning-box">
            <AlertTriangle :size="20" />
            <span>{{ $t('admin.settings.cannotConnectOllama') }}</span>
          </div>

          <div v-else-if="loadingModels" class="loading">{{ $t('admin.settings.loadingModels') }}</div>
          
          <div v-else>
            <!-- Search Box -->
            <div class="models-search-container">
              <div class="search-input-wrapper">
                <Search :size="18" class="search-icon" />
                <input
                  v-model="modelSearchQuery"
                  type="text"
                  :placeholder="$t('admin.settings.searchModelsPlaceholder')"
                  class="models-search-input"
                />
                <button
                  v-if="modelSearchQuery"
                  @click="clearSearch"
                  class="search-clear-btn"
                  type="button"
                >
                  <X :size="16" />
                </button>
              </div>
              <div v-if="modelSearchQuery" class="search-results-info">
                {{ $t('admin.settings.foundModels', { count: llmModels.length + embeddingModels.length }) }}
              </div>
            </div>
            
            <!-- LLM Models Section -->
            <div class="models-subsection">
              <div class="subsection-header" @click="toggleSection('llm')">
                <h3>{{ $t('admin.settings.llmModelsSection') }}</h3>
                <button class="expand-toggle" type="button">
                  <ChevronDown v-if="expandedSections.llm" :size="20" />
                  <ChevronUp v-else :size="20" />
                </button>
              </div>
              <div v-show="expandedSections.llm" class="models-list">
                <div
                  v-for="model in llmModels"
                  :key="model.name"
                  class="model-item"
                  :class="{ 'model-current': model.is_current_llm }"
                >
                  <div class="model-header">
                    <div class="model-info">
                      <h4>
                        {{ model.name }}
                        <span v-if="model.is_current_llm" class="current-badge">{{ $t('admin.settings.current') }}</span>
                      </h4>
                      <div class="model-meta">
                        <span v-if="model.size > 0">{{ formatSize(model.size) }}</span>
                        <span v-if="model.modified_at">{{ formatDate(model.modified_at) }}</span>
                        <span v-if="model.description" class="model-description">{{ model.description }}</span>
                        <span v-if="model.tags && model.tags.length > 0" class="model-tags">
                          <span v-for="tag in model.tags" :key="tag" class="tag">{{ tag }}</span>
                        </span>
                      </div>
                    </div>
                    <div class="model-actions">
                      <StatusBadge 
                        :status="model.downloaded ? 'available' : (model.available ? 'pending' : 'not_available')" 
                      />
                      <span v-if="model.downloaded" class="status-text">{{ $t('admin.settings.downloaded') }}</span>
                      <span v-else-if="model.available" class="status-text">{{ $t('admin.settings.available') }}</span>
                      <span v-else class="status-text">{{ $t('common.unknown') }}</span>
                      <div class="action-buttons">
                        <button
                          v-if="!model.downloaded && model.available"
                          @click="pullModel(model.name)"
                          class="btn-small btn-primary"
                          :disabled="pullingModel === model.name"
                        >
                          <Download :size="14" />
                          {{ pullingModel === model.name ? $t('admin.settings.downloading') : $t('admin.settings.download') }}
                        </button>
                        <div v-if="model.downloaded" class="test-dropdown">
                          <button
                            @click.stop="showTestDropdown(model.name)"
                            class="btn-small btn-secondary"
                            :disabled="testingModel === model.name"
                          >
                            <TestTube :size="14" />
                            {{ $t('admin.settings.test') }}
                          </button>
                          <div v-if="testDropdownOpen === model.name" class="dropdown-menu" @click.stop>
                            <button @click="testModel(model.name, 'llm', true)" class="dropdown-item">
                              {{ $t('admin.settings.quickTest') }}
                            </button>
                            <button @click="showCustomTest(model.name, 'llm')" class="dropdown-item">
                              {{ $t('admin.settings.customTest') }}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Custom Test Input -->
                  <div v-if="customTestModel === model.name && customTestType === 'llm'" class="custom-test-input">
                    <input
                      v-model="customTestInput"
                      type="text"
                      :placeholder="$t('admin.settings.enterTestPrompt')"
                      @keyup.enter="testModel(model.name, 'llm', false)"
                    />
                    <button @click="testModel(model.name, 'llm', false)" class="btn-small btn-primary">
                      {{ $t('admin.settings.runTest') }}
                    </button>
                    <button @click="cancelCustomTest" class="btn-small btn-secondary">
                      {{ $t('common.cancel') }}
                    </button>
                  </div>

                  <!-- Test Result -->
                  <div v-if="testResults[model.name]" class="test-result">
                    <div class="test-result-header" @click="toggleTestResult(model.name)">
                      <span>{{ $t('admin.settings.testResult') }}</span>
                      <span>{{ testResults[model.name].success ? '✓' : '✗' }}</span>
                    </div>
                    <div v-if="expandedTestResults[model.name]" class="test-result-content">
                      <div v-if="testResults[model.name].success">
                        <div v-if="testResults[model.name].result.response" class="test-response">
                          <strong>{{ $t('admin.settings.response') }}:</strong>
                          <pre>{{ testResults[model.name].result.response }}</pre>
                        </div>
                        <div v-if="testResults[model.name].result.token_usage" class="test-meta">
                          <span>{{ $t('admin.settings.duration') }}: {{ testResults[model.name].duration_ms }}ms</span>
                          <span>{{ $t('admin.settings.tokens') }}: {{ testResults[model.name].result.token_usage.total_tokens }}</span>
                        </div>
                      </div>
                      <div v-else class="test-error">
                        {{ testResults[model.name].error || $t('admin.settings.testFailed') }}
                      </div>
                    </div>
                  </div>
                </div>
                <div v-if="llmModels.length === 0" class="empty-state">
                  {{ $t('admin.settings.noLlmModels') }}
                </div>
              </div>
            </div>

            <!-- Embedding Models Section -->
            <div class="models-subsection">
              <div class="subsection-header" @click="toggleSection('embedding')">
                <h3>{{ $t('admin.settings.embeddingModelsSection') }}</h3>
                <button class="expand-toggle" type="button">
                  <ChevronDown v-if="expandedSections.embedding" :size="20" />
                  <ChevronUp v-else :size="20" />
                </button>
              </div>
              <div v-show="expandedSections.embedding" class="models-list">
                <div
                  v-for="model in embeddingModels"
                  :key="model.name"
                  class="model-item"
                  :class="{ 'model-current': model.is_current_embedding }"
                >
                  <div class="model-header">
                    <div class="model-info">
                      <h4>
                        {{ model.name }}
                        <span v-if="model.is_current_embedding" class="current-badge">{{ $t('admin.settings.current') }}</span>
                      </h4>
                      <div class="model-meta">
                        <span v-if="model.size > 0">{{ formatSize(model.size) }}</span>
                        <span v-if="model.modified_at">{{ formatDate(model.modified_at) }}</span>
                        <span v-if="model.description" class="model-description">{{ model.description }}</span>
                        <span v-if="model.tags && model.tags.length > 0" class="model-tags">
                          <span v-for="tag in model.tags" :key="tag" class="tag">{{ tag }}</span>
                        </span>
                      </div>
                    </div>
                    <div class="model-actions">
                      <StatusBadge 
                        :status="model.downloaded ? 'available' : (model.available ? 'pending' : 'not_available')" 
                      />
                      <span v-if="model.downloaded" class="status-text">{{ $t('admin.settings.downloaded') }}</span>
                      <span v-else-if="model.available" class="status-text">{{ $t('admin.settings.available') }}</span>
                      <span v-else class="status-text">{{ $t('common.unknown') }}</span>
                      <div class="action-buttons">
                        <button
                          v-if="!model.downloaded && model.available"
                          @click="pullModel(model.name)"
                          class="btn-small btn-primary"
                          :disabled="pullingModel === model.name"
                        >
                          <Download :size="14" />
                          {{ pullingModel === model.name ? $t('admin.settings.downloading') : $t('admin.settings.download') }}
                        </button>
                        <div v-if="model.downloaded" class="test-dropdown">
                          <button
                            @click.stop="showTestDropdown(model.name)"
                            class="btn-small btn-secondary"
                            :disabled="testingModel === model.name"
                          >
                            <TestTube :size="14" />
                            {{ $t('admin.settings.test') }}
                          </button>
                          <div v-if="testDropdownOpen === model.name" class="dropdown-menu" @click.stop>
                            <button @click="testModel(model.name, 'embedding', true)" class="dropdown-item">
                              {{ $t('admin.settings.quickTest') }}
                            </button>
                            <button @click="showCustomTest(model.name, 'embedding')" class="dropdown-item">
                              {{ $t('admin.settings.customTest') }}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Custom Test Input -->
                  <div v-if="customTestModel === model.name && customTestType === 'embedding'" class="custom-test-input">
                    <input
                      v-model="customTestInput"
                      type="text"
                      :placeholder="$t('admin.settings.enterTestText')"
                      @keyup.enter="testModel(model.name, 'embedding', false)"
                    />
                    <button @click="testModel(model.name, 'embedding', false)" class="btn-small btn-primary">
                      {{ $t('admin.settings.runTest') }}
                    </button>
                    <button @click="cancelCustomTest" class="btn-small btn-secondary">
                      {{ $t('common.cancel') }}
                    </button>
                  </div>

                  <!-- Test Result -->
                  <div v-if="testResults[model.name]" class="test-result">
                    <div class="test-result-header" @click="toggleTestResult(model.name)">
                      <span>{{ $t('admin.settings.testResult') }}</span>
                      <span>{{ testResults[model.name].success ? '✓' : '✗' }}</span>
                    </div>
                    <div v-if="expandedTestResults[model.name]" class="test-result-content">
                      <div v-if="testResults[model.name].success">
                        <div v-if="testResults[model.name].result.embedding_dimension" class="test-response">
                          <strong>{{ $t('admin.settings.dimension') }}:</strong> {{ testResults[model.name].result.embedding_dimension }}
                        </div>
                        <div v-if="testResults[model.name].result.embedding_sample" class="test-response">
                          <strong>{{ $t('admin.settings.sample') }}:</strong>
                          <pre>{{ JSON.stringify(testResults[model.name].result.embedding_sample, null, 2) }}</pre>
                        </div>
                        <div class="test-meta">
                          <span>{{ $t('admin.settings.duration') }}: {{ testResults[model.name].duration_ms }}ms</span>
                        </div>
                      </div>
                      <div v-else class="test-error">
                        {{ testResults[model.name].error || $t('admin.settings.testFailed') }}
                      </div>
                    </div>
                  </div>
                </div>
                <div v-if="embeddingModels.length === 0" class="empty-state">
                  {{ $t('admin.settings.noEmbeddingModels') }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Auto Tag Settings Tab -->
      <div v-if="activeTab === 'tags'" class="tab-content">
        <div class="section-header">
          <h2>{{ $t('admin.settings.autoTagSettingsTitle') }}</h2>
        </div>
        <div class="tag-settings-section">
          <div class="form-section">
            <div class="form-group">
              <label for="tag_max_tags">{{ $t('admin.settings.maxTags') }} *</label>
              <input
                id="tag_max_tags"
                v-model.number="tagForm.max_tags"
                type="number"
                min="1"
                max="20"
                :placeholder="$t('admin.settings.maxTagsPlaceholder')"
              />
              <small>{{ $t('admin.settings.maxTagsHint') }}</small>
            </div>
            <div class="form-group">
              <label for="tag_max_length">{{ $t('admin.settings.maxTagLength') }} *</label>
              <input
                id="tag_max_length"
                v-model.number="tagForm.max_length"
                type="number"
                min="5"
                max="200"
                :placeholder="$t('admin.settings.maxTagLengthPlaceholder')"
              />
              <small>{{ $t('admin.settings.maxTagLengthHint') }}</small>
            </div>
            <div class="form-group">
              <label for="tag_prefix">{{ $t('admin.settings.tagPrefix') }} *</label>
              <input
                id="tag_prefix"
                v-model="tagForm.prefix"
                type="text"
                :placeholder="$t('admin.settings.tagPrefixPlaceholder')"
                maxlength="50"
              />
              <small>{{ $t('admin.settings.tagPrefixHint') }}</small>
            </div>
            <div class="form-group">
              <label for="tag_ocr_text_limit">{{ $t('admin.settings.ocrTextLimit') }} *</label>
              <input
                id="tag_ocr_text_limit"
                v-model.number="tagForm.ocr_text_limit"
                type="number"
                min="100"
                max="50000"
                :placeholder="$t('admin.settings.ocrTextLimitPlaceholder')"
              />
              <small>{{ $t('admin.settings.ocrTextLimitHint') }}</small>
            </div>
            <div class="form-group">
              <label for="tag_prompt">{{ $t('admin.settings.tagPrompt') }} *</label>
              <textarea
                id="tag_prompt"
                v-model="tagForm.prompt"
                rows="8"
                :placeholder="$t('admin.settings.tagPromptPlaceholder')"
                class="prompt-textarea"
                maxlength="5000"
              ></textarea>
              <small>{{ $t('admin.settings.tagPromptHint') }}</small>
            </div>
            <div class="form-actions">
              <button @click="saveTagSettings" class="btn-primary" :disabled="savingTags">
                <Save :size="16" />
                {{ savingTags ? $t('admin.settings.saving') : $t('admin.settings.saveTagSettings') }}
              </button>
              <button @click="loadTagSettings" class="btn-secondary" :disabled="savingTags">
                <RefreshCw :size="16" />
                {{ $t('admin.settings.reset') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Chatbot Policies Tab -->
      <div v-if="activeTab === 'chatbot'" class="tab-content">
        <!-- Chatbot Prompts Section -->
        <div class="section-header">
          <h2>{{ $t('admin.settings.chatbotPrompts') }}</h2>
        </div>
        <div class="prompts-section">
          <div class="form-section">
            <div class="form-group">
              <label for="system_prompt">{{ $t('admin.settings.systemPrompt') }}</label>
              <textarea
                id="system_prompt"
                v-model="promptsForm.system_prompt"
                rows="4"
                :placeholder="$t('admin.settings.systemPromptPlaceholder')"
                class="prompt-textarea"
              ></textarea>
              <small>{{ $t('admin.settings.systemPromptHint') }}</small>
            </div>
            <div class="form-group">
              <label for="context_prompt">{{ $t('admin.settings.contextPrompt') }}</label>
              <textarea
                id="context_prompt"
                v-model="promptsForm.context_prompt"
                rows="6"
                :placeholder="$t('admin.settings.contextPromptPlaceholder')"
                class="prompt-textarea"
              ></textarea>
              <small>{{ $t('admin.settings.contextPromptHint') }}</small>
            </div>
            <div class="form-group">
              <label for="no_context_prompt">{{ $t('admin.settings.noContextPrompt') }}</label>
              <textarea
                id="no_context_prompt"
                v-model="promptsForm.no_context_prompt"
                rows="4"
                :placeholder="$t('admin.settings.noContextPromptPlaceholder')"
                class="prompt-textarea"
              ></textarea>
              <small>{{ $t('admin.settings.noContextPromptHint') }}</small>
            </div>
            <div class="form-actions">
              <button @click="savePrompts" class="btn-primary" :disabled="savingPrompts">
                <Save :size="16" />
                {{ savingPrompts ? $t('admin.settings.saving') : $t('admin.settings.savePrompts') }}
              </button>
              <button @click="resetPromptsToDefaults" class="btn-secondary" :disabled="savingPrompts">
                <RefreshCw :size="16" />
                {{ $t('admin.settings.resetToDefaults') }}
              </button>
            </div>
          </div>
        </div>

        <!-- RAG Settings Section -->
        <div class="section-header" style="margin-top: 3rem;">
          <h2>{{ $t('admin.settings.ragSettings') }}</h2>
        </div>
        <div class="rag-settings-section">
          <div class="form-section">
            <div class="form-group">
              <label for="rag_chunk_size">{{ $t('admin.settings.chunkSize') }} *</label>
              <input
                id="rag_chunk_size"
                v-model.number="ragForm.chunk_size"
                type="number"
                min="100"
                max="4096"
                :placeholder="$t('admin.settings.chunkSizePlaceholder')"
              />
              <small>{{ $t('admin.settings.chunkSizeHint') }}</small>
            </div>
            <div class="form-group">
              <label for="rag_chunk_overlap">{{ $t('admin.settings.chunkOverlap') }} *</label>
              <input
                id="rag_chunk_overlap"
                v-model.number="ragForm.chunk_overlap"
                type="number"
                min="0"
                :max="ragForm.chunk_size / 2"
                :placeholder="$t('admin.settings.chunkOverlapPlaceholder')"
              />
              <small>{{ $t('admin.settings.chunkOverlapHint') }}</small>
            </div>
            <div class="form-group">
              <label for="rag_top_k">{{ $t('admin.settings.topK') }} *</label>
              <input
                id="rag_top_k"
                v-model.number="ragForm.top_k"
                type="number"
                min="1"
                max="100"
                :placeholder="$t('admin.settings.topKPlaceholder')"
              />
              <small>{{ $t('admin.settings.topKHint') }}</small>
            </div>
            <div class="form-actions">
              <button @click="saveRAGSettings" class="btn-primary" :disabled="savingRAG">
                <Save :size="16" />
                {{ savingRAG ? $t('admin.settings.saving') : $t('admin.settings.saveRagSettings') }}
              </button>
              <button @click="loadRAGSettings" class="btn-secondary" :disabled="savingRAG">
                <RefreshCw :size="16" />
                {{ $t('admin.settings.reset') }}
              </button>
            </div>
          </div>
        </div>

        <div class="section-header" style="margin-top: 3rem;">
          <h2>{{ $t('admin.settings.chatbotPolicies') }}</h2>
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
                {{ $t('common.edit') }}
              </button>
            </div>
            <div class="policy-details">
              <div class="detail-item">
                <span class="label">{{ $t('admin.settings.allowedSources') }}:</span>
                <span>{{ policy.allowed_sources?.join(', ') || $t('admin.settings.all') }}</span>
              </div>
              <div class="detail-item">
                <span class="label">{{ $t('admin.settings.allowPreview') }}:</span>
                <span>{{ policy.allow_preview ? $t('common.yes') : $t('common.no') }}</span>
              </div>
              <div class="detail-item">
                <span class="label">{{ $t('admin.settings.maxTokens') }}:</span>
                <span>{{ policy.max_tokens || $t('admin.settings.unlimited') }}</span>
              </div>
            </div>
          </div>
          <div v-if="chatbotPolicies.length === 0" class="empty-state">
            {{ $t('admin.settings.noChatbotPolicies') }}
          </div>
        </div>
      </div>
    </div>

    <!-- Retention Policy Modal -->
    <Modal
      v-model:show="showRetentionModal"
      :title="editingRetentionPolicy ? $t('admin.settings.editPolicy') : $t('admin.settings.createPolicy')"
    >
      <div class="form-group">
        <label>{{ $t('admin.settings.policyName') }} *</label>
        <input v-model="retentionForm.name" required />
      </div>
      <div class="form-group">
        <label>{{ $t('admin.settings.durationDays') }} *</label>
        <input v-model.number="retentionForm.duration_days" type="number" required />
      </div>
      <div class="form-group">
        <label>{{ $t('admin.settings.disposition') }} *</label>
        <select v-model="retentionForm.disposition" required>
          <option value="delete">{{ $t('admin.settings.delete') }}</option>
          <option value="archive">{{ $t('admin.settings.archive') }}</option>
          <option value="retain">{{ $t('admin.settings.archive') }}</option>
        </select>
      </div>
      <div class="form-group">
        <label>
          <input type="checkbox" v-model="retentionForm.legal_hold" />
          {{ $t('admin.settings.legalHold') }}
        </label>
      </div>
      <template #footer>
        <button
          type="button"
          @click="showRetentionModal = false"
          class="btn-secondary"
        >
          {{ $t('common.cancel') }}
        </button>
        <button type="button" @click="saveRetentionPolicy" class="btn-primary">{{ $t('common.save') }}</button>
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
          <h4>{{ $t('admin.settings.stepsToFix') }}</h4>
          <ol class="steps-list">
            <li v-for="step in currentFixGuide.steps" :key="step.step" class="step-item">
              <div class="step-header">
                <strong>{{ step.step }}. {{ step.title }}</strong>
              </div>
              <div class="step-description">{{ step.description }}</div>
              <div v-if="step.action" class="step-action">
                <strong>{{ $t('common.actions') }}:</strong> {{ step.action }}
              </div>
              <div v-if="step.command" class="step-command">
                <code>{{ step.command }}</code>
                <button 
                  @click="copyToClipboard(step.command)" 
                  class="btn-copy"
                  :title="$t('common.copy')"
                >
                  {{ $t('common.copy') }}
                </button>
              </div>
            </li>
          </ol>
        </div>

        <div v-if="currentFixGuide.download_link" class="fix-guide-download">
          <h4>{{ $t('admin.settings.downloadLink') }}:</h4>
          <a :href="currentFixGuide.download_link" target="_blank" rel="noopener noreferrer">
            {{ currentFixGuide.download_link }}
          </a>
        </div>

        <div v-if="currentFixGuide.verify_command" class="fix-guide-verify">
          <h4>{{ $t('admin.settings.verifyInstallation') }}:</h4>
          <code>{{ currentFixGuide.verify_command }}</code>
          <button 
            @click="copyToClipboard(currentFixGuide.verify_command)" 
            class="btn-copy"
            :title="$t('common.copy')"
          >
            {{ $t('common.copy') }}
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
            {{ fixingProvider === currentProvider.name ? $t('admin.settings.fixing') : $t('admin.settings.autoFix') }}
          </button>
          <button @click="showFixGuideModal = false" class="btn-secondary">
            {{ $t('common.close') }}
          </button>
        </div>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSettingsStore } from '../../store/settings'
import { useGroupsStore } from '../../store/groups'
import { settingsAPI } from '../../services/api'
import { Modal, StatusBadge } from '../../components'
import { Plus, Edit, Trash2, Activity, Save, RefreshCw, AlertTriangle, Download, TestTube, ChevronDown, ChevronUp, Search, X } from 'lucide-vue-next'

const { t } = useI18n()

const settingsStore = useSettingsStore()
const groupsStore = useGroupsStore()

const activeTab = ref('retention')

// Watch for tab changes to load models
watch(activeTab, async (newTab) => {
  if (newTab === 'llm') {
    await loadOllamaModels()
  }
})

// Computed properties for filtering models
const llmModels = computed(() => {
  return ollamaModels.value.filter(model => {
    // Filter for LLM models (not embedding models)
    // Use type field if available, otherwise fallback to name-based filtering
    let isLLM = false
    if (model.type !== undefined) {
      isLLM = model.type === 'llm'
    } else {
      // Fallback: Filter by name (for backward compatibility)
      const name = model.name.toLowerCase()
      isLLM = !name.includes('embed') && !name.includes('nomic-embed')
    }
    
    if (!isLLM) return false
    
    // Apply search filter
    if (modelSearchQuery.value) {
      const query = modelSearchQuery.value.toLowerCase()
      const name = model.name.toLowerCase()
      const description = (model.description || '').toLowerCase()
      const tags = (model.tags || []).join(' ').toLowerCase()
      return name.includes(query) || description.includes(query) || tags.includes(query)
    }
    
    return true
  })
})

const embeddingModels = computed(() => {
  return ollamaModels.value.filter(model => {
    // Filter for embedding models
    // Use type field if available, otherwise fallback to name-based filtering
    let isEmbedding = false
    if (model.type !== undefined) {
      isEmbedding = model.type === 'embedding'
    } else {
      // Fallback: Filter by name (for backward compatibility)
      const name = model.name.toLowerCase()
      isEmbedding = name.includes('embed') || name.includes('nomic-embed')
    }
    
    if (!isEmbedding) return false
    
    // Apply search filter
    if (modelSearchQuery.value) {
      const query = modelSearchQuery.value.toLowerCase()
      const name = model.name.toLowerCase()
      const description = (model.description || '').toLowerCase()
      const tags = (model.tags || []).join(' ').toLowerCase()
      return name.includes(query) || description.includes(query) || tags.includes(query)
    }
    
    return true
  })
})

// Computed properties for dropdowns - only show downloaded/available models
const availableLLMModels = computed(() => {
  return llmModels.value.filter(model => model.downloaded === true)
})

const availableEmbeddingModels = computed(() => {
  return embeddingModels.value.filter(model => model.downloaded === true)
})

// Close dropdown when clicking outside
const handleClickOutside = (event) => {
  if (!event.target.closest('.test-dropdown')) {
    testDropdownOpen.value = null
  }
}

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
const promptsForm = ref({
  system_prompt: '',
  context_prompt: '',
  no_context_prompt: ''
})
const savingPrompts = ref(false)

// RAG Settings
const ragForm = ref({
  chunk_size: 1024,
  chunk_overlap: 100,
  top_k: 20
})
const savingRAG = ref(false)

// Ollama Models Management
const ollamaModels = ref([])
const loadingModels = ref(false)
const ollamaConnected = ref(true)
const pullingModel = ref(null)
const testingModel = ref(null)
const testDropdownOpen = ref(null)
const customTestModel = ref(null)
const customTestType = ref(null)
const customTestInput = ref('')
const testResults = ref({})
const expandedTestResults = ref({})
const expandedSections = ref({
  llm: true,
  embedding: true
})

const modelSearchQuery = ref('')

const toggleSection = (section) => {
  expandedSections.value[section] = !expandedSections.value[section]
}

const clearSearch = () => {
  modelSearchQuery.value = ''
}
const ocrSettings = ref(null)

const ocrForm = ref({
  provider: 'tesseract',
  languages: ['en', 'vi']
})
const savingOCR = ref(false)

// Purge grace period settings
const purgeGracePeriodForm = ref({
  days: 1
})
const savingPurgeGracePeriod = ref(false)

// Auto Tag Settings
const tagForm = ref({
  max_tags: 3,
  max_length: 50,
  prefix: 'auto_tag:',
  ocr_text_limit: 5000,
  prompt: ''
})
const savingTags = ref(false)

// Fix guide modal
const showFixGuideModal = ref(false)
const currentFixGuide = ref(null)
const currentProvider = ref(null)
const fixingProvider = ref(null)
const fixGuideModalTitle = ref('')

const tabs = computed(() => {
  const { t } = useI18n()
  return [
    { id: 'retention', label: t('admin.settings.retentionPolicies') },
    { id: 'providers', label: t('admin.settings.ocrProviders') },
    { id: 'llm', label: t('admin.settings.llmSettings') },
    { id: 'chatbot', label: t('admin.settings.chatbotPolicies') },
    { id: 'tags', label: t('admin.settings.autoTagSettings') }
  ]
})

const availableLanguages = computed(() => [
  { code: 'en', name: t('admin.settings.languageEnglish') },
  { code: 'vi', name: t('admin.settings.languageVietnamese') },
  { code: 'ja', name: t('admin.settings.languageJapanese') },
  { code: 'ko', name: t('admin.settings.languageKorean') },
  { code: 'zh', name: t('admin.settings.languageChinese') }
])

const retentionForm = ref({
  name: '',
  duration_days: 30,
  disposition: 'delete',
  legal_hold: false
})

onMounted(async () => {
  document.addEventListener('click', handleClickOutside)
  await loadRetentionPolicies()
  await loadProviders()
  await loadChatbotPolicies()
  await loadGroups()
  await loadLLMSettings()
  await loadOCRSettings()
  await loadPurgeGracePeriod()
  await loadPrompts()
  await loadRAGSettings()
  await loadTagSettings()
  // Load Ollama models when LLM tab is active
  if (activeTab.value === 'llm') {
    await loadOllamaModels()
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
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
        editingRetentionPolicy.value ? t('admin.settings.policyUpdated') : t('admin.settings.policyCreated'),
        'success'
      )
    }
  } catch (e) {
    console.error('Failed to save retention policy', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToSaveRetentionPolicy'), 'error')
    }
  }
}

const deleteRetentionPolicy = async (policy) => {
  if (confirm(t('admin.settings.deletePolicyConfirm', { name: policy.name }))) {
    try {
      await settingsStore.deleteRetentionPolicy(policy.id)
      await loadRetentionPolicies()
      if (window.$toast) {
        window.$toast.show(t('admin.settings.policyDeleted'), 'success')
      }
    } catch (e) {
      console.error('Failed to delete retention policy', e)
      if (window.$toast) {
        window.$toast.show(t('admin.settings.failedToDeleteRetentionPolicy'), 'error')
      }
    }
  }
}

const checkProviderHealth = async () => {
  try {
    // This would trigger health checks on backend
    await loadProviders()
    if (window.$toast) {
      window.$toast.show(t('admin.settings.healthCheckCompleted'), 'success')
    }
  } catch (e) {
    console.error('Failed to check provider health', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToCheckProviderHealth'), 'error')
    }
  }
}

const saveProviders = async () => {
  try {
    await settingsStore.updateProviders(providers.value)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.providersSaved'), 'success')
    }
  } catch (e) {
    console.error('Failed to save providers', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToSaveProviders'), 'error')
    }
  }
}

const loadPrompts = async () => {
  try {
    const res = await settingsAPI.chatbot.getPrompts()
    if (res.is_success) {
      promptsForm.value = {
        system_prompt: res.data.system_prompt || '',
        context_prompt: res.data.context_prompt || '',
        no_context_prompt: res.data.no_context_prompt || ''
      }
    }
  } catch (e) {
    console.error('Failed to load prompts', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToLoadPrompts'), 'error')
    }
  }
}

const resetPromptsToDefaults = async () => {
  if (!confirm(t('admin.settings.resetPromptsConfirm'))) {
    return
  }
  
  try {
    // Delete custom prompts from settings to use defaults
    await settingsAPI.chatbot.updatePrompts({
      system_prompt: null,
      context_prompt: null,
      no_context_prompt: null
    })
    
    // Reload prompts (will get defaults)
    await loadPrompts()
    
    if (window.$toast) {
      window.$toast.show(t('admin.settings.promptsResetToDefaults'), 'success')
    }
  } catch (e) {
    console.error('Failed to reset prompts', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToResetPrompts'), 'error')
    }
  }
}

const savePrompts = async () => {
  savingPrompts.value = true
  try {
    const res = await settingsAPI.chatbot.updatePrompts(promptsForm.value)
    if (res.is_success) {
      if (window.$toast) {
        window.$toast.show(t('admin.settings.promptsSaved'), 'success')
      }
    }
  } catch (e) {
    console.error('Failed to save prompts', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToSavePrompts'), 'error')
    }
  } finally {
    savingPrompts.value = false
  }
}

const loadRAGSettings = async () => {
  try {
    const res = await settingsAPI.chatbot.rag.get()
    if (res.is_success) {
      ragForm.value = {
        chunk_size: res.data.chunk_size || 1024,
        chunk_overlap: res.data.chunk_overlap || 100,
        top_k: res.data.top_k || 20
      }
    }
  } catch (e) {
    console.error('Failed to load RAG settings', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToLoadRagSettings'), 'error')
    }
  }
}

const saveRAGSettings = async () => {
  // Validation
  if (ragForm.value.chunk_size < 100 || ragForm.value.chunk_size > 4096) {
    if (window.$toast) {
      window.$toast.show(t('admin.settings.chunkSizeMustBeBetween'), 'error')
    }
    return
  }
  
  if (ragForm.value.chunk_overlap < 0) {
    if (window.$toast) {
      window.$toast.show(t('admin.settings.chunkOverlapMustBeNonNegative'), 'error')
    }
    return
  }
  
  if (ragForm.value.chunk_overlap >= ragForm.value.chunk_size) {
    if (window.$toast) {
      window.$toast.show(t('admin.settings.chunkOverlapMustBeLessThanChunkSize'), 'error')
    }
    return
  }
  
  if (ragForm.value.top_k < 1 || ragForm.value.top_k > 100) {
    if (window.$toast) {
      window.$toast.show(t('admin.settings.topKMustBeBetween'), 'error')
    }
    return
  }
  
  savingRAG.value = true
  try {
    const res = await settingsAPI.chatbot.rag.update(ragForm.value)
    if (res.is_success) {
      if (window.$toast) {
        window.$toast.show(t('admin.settings.ragSettingsSaved'), 'success')
      }
    }
  } catch (e) {
    console.error('Failed to save RAG settings', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToSaveRagSettings'), 'error')
    }
  } finally {
    savingRAG.value = false
  }
}

const editChatbotPolicy = (policy) => {
  if (window.$toast) {
    window.$toast.show(t('admin.settings.chatbotPolicyEditingNotImplemented'), 'info')
  }
}

const getGroupName = (groupId) => {
  const group = groupsStore.groups.find(g => g.id === groupId)
  return group ? group.name : t('admin.settings.groupFallback', { id: groupId })
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
      // Load models list for dropdowns
      await loadOllamaModels()
    }
  } catch (e) {
    console.error('Failed to load LLM settings', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToLoadLlmSettings'), 'error')
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
        window.$toast.show(t('admin.settings.llmSettingsSaved'), 'success')
      }
      await loadLLMSettings()
    }
  } catch (e) {
    console.error('Failed to save LLM settings', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToSaveLlmSettings'), 'error')
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
        provider: ocrSettings.value.provider || 'tesseract',
        languages: ocrSettings.value.languages || ['en', 'vi']
      }
    } else {
      // Initialize with defaults if no settings in DB
      ocrForm.value = {
        provider: 'tesseract',
        languages: ['en', 'vi']
      }
    }
  } catch (e) {
    console.error('Failed to load OCR settings', e)
    // Initialize with defaults on error
    ocrForm.value = {
      provider: 'tesseract',
      languages: ['en', 'vi']
    }
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToLoadOcrSettings'), 'error')
    }
  }
}

const saveOCRSettings = async () => {
  savingOCR.value = true
  try {
    // Force provider to tesseract - only supported provider
    const payload = {
      provider: 'tesseract',
      languages: ocrForm.value.languages
    }
    
    await settingsStore.updateOCRSettings(payload)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.ocrSettingsSaved'), 'success')
    }
    await loadOCRSettings()
  } catch (e) {
    console.error('Failed to save OCR settings', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToSaveOcrSettings'), 'error')
    }
  } finally {
    savingOCR.value = false
  }
}

const showFixGuide = (provider) => {
  currentProvider.value = provider
  if (provider.fix_guide) {
    currentFixGuide.value = provider.fix_guide
    fixGuideModalTitle.value = t('admin.settings.fixGuideTitle', { name: provider.name })
  } else {
    // Fallback: create a basic guide from description
    currentFixGuide.value = {
      title: t('admin.settings.fixGuideTitle', { name: provider.name }),
      description: provider.description || t('admin.settings.noFixGuideAvailable'),
      steps: []
    }
    fixGuideModalTitle.value = t('admin.settings.fixGuideTitle', { name: provider.name })
  }
  showFixGuideModal.value = true
}

const fixProvider = async (providerName) => {
  fixingProvider.value = providerName
  try {
    await settingsStore.fixProvider(providerName)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.fixCompleted', { name: providerName }), 'success')
    }
    // Refresh providers to see updated health
    await loadProviders()
    // Close modal if open
    if (showFixGuideModal.value && currentProvider.value?.name === providerName) {
      showFixGuideModal.value = false
    }
  } catch (e) {
    console.error(`Failed to fix ${providerName}`, e)
    const errorMsg = e.response?.data?.message || e.message || t('admin.settings.failedToPullModel', { name: providerName })
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
      window.$toast.show(t('admin.settings.copiedToClipboard'), 'success')
    }
  } catch (e) {
    console.error('Failed to copy to clipboard', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToCopyToClipboard'), 'error')
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
      window.$toast.show(t('admin.settings.failedToLoadPurgeGracePeriod'), 'error')
    }
  }
}

const savePurgeGracePeriod = async () => {
  savingPurgeGracePeriod.value = true
  try {
    if (purgeGracePeriodForm.value.days < 0 || purgeGracePeriodForm.value.days > 365) {
      if (window.$toast) {
        window.$toast.show(t('admin.settings.purgeGracePeriodMustBeBetween'), 'error')
      }
      return
    }
    
    const res = await settingsAPI.purgeGracePeriod.update(purgeGracePeriodForm.value.days)
    if (res.is_success) {
      if (window.$toast) {
        window.$toast.show(t('admin.settings.purgeGracePeriodSaved'), 'success')
      }
      await loadPurgeGracePeriod()
    } else {
      if (window.$toast) {
        window.$toast.show(res.message || t('admin.settings.failedToSavePurgeGracePeriod'), 'error')
      }
    }
  } catch (e) {
    console.error('Failed to save purge grace period', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToSavePurgeGracePeriod'), 'error')
    }
  } finally {
    savingPurgeGracePeriod.value = false
  }
}

// Ollama Models Management Functions
const loadOllamaModels = async () => {
  loadingModels.value = true
  try {
    const res = await settingsAPI.ollama.models.list()
    if (res.is_success) {
      ollamaModels.value = res.data.models || []
      ollamaConnected.value = res.data.ollama_connected !== false
    } else {
      ollamaConnected.value = false
      if (window.$toast) {
        window.$toast.show(t('admin.settings.failedToLoadOllamaModels'), 'error')
      }
    }
  } catch (e) {
    console.error('Failed to load Ollama models', e)
    ollamaConnected.value = false
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToLoadOllamaModels'), 'error')
    }
  } finally {
    loadingModels.value = false
  }
}

const pullModel = async (modelName) => {
  pullingModel.value = modelName
  try {
    const res = await settingsAPI.ollama.models.pull(modelName)
    if (res.is_success) {
      if (window.$toast) {
        window.$toast.show(t('admin.settings.startedPulling', { name: modelName }), 'success')
      }
      // Refresh models list after a delay
      setTimeout(async () => {
        await loadOllamaModels()
      }, 2000)
    } else {
      if (window.$toast) {
        window.$toast.show(res.message || t('admin.settings.failedToPullModel', { name: modelName }), 'error')
      }
    }
  } catch (e) {
    console.error(`Failed to pull model ${modelName}`, e)
    const errorMsg = e.response?.data?.message || e.message || t('admin.settings.failedToPullModel', { name: modelName })
    if (window.$toast) {
      window.$toast.show(errorMsg, 'error')
    }
  } finally {
    pullingModel.value = null
  }
}

const showTestDropdown = (modelName) => {
  testDropdownOpen.value = testDropdownOpen.value === modelName ? null : modelName
}

const showCustomTest = (modelName, modelType) => {
  customTestModel.value = modelName
  customTestType.value = modelType
  customTestInput.value = ''
  testDropdownOpen.value = null
}

const cancelCustomTest = () => {
  customTestModel.value = null
  customTestType.value = null
  customTestInput.value = ''
}

const testModel = async (modelName, modelType, isQuickTest) => {
  testingModel.value = modelName
  cancelCustomTest()
  
  try {
    const testInput = isQuickTest ? null : customTestInput.value
    const res = await settingsAPI.ollama.models.test(modelName, modelType, testInput)
    
    if (res.is_success) {
      testResults.value[modelName] = {
        success: true,
        result: res.data.result,
        duration_ms: res.data.duration_ms,
        test_input: res.data.test_input
      }
      expandedTestResults.value[modelName] = true
    } else {
      testResults.value[modelName] = {
        success: false,
        error: res.message || t('admin.settings.testFailed')
      }
      expandedTestResults.value[modelName] = true
    }
  } catch (e) {
    console.error(`Failed to test model ${modelName}`, e)
    const errorMsg = e.response?.data?.message || e.message || t('admin.settings.failedToTestModel', { name: modelName })
    testResults.value[modelName] = {
      success: false,
      error: errorMsg
    }
    expandedTestResults.value[modelName] = true
    if (window.$toast) {
      window.$toast.show(errorMsg, 'error')
    }
  } finally {
    testingModel.value = null
  }
}

const toggleTestResult = (modelName) => {
  expandedTestResults.value[modelName] = !expandedTestResults.value[modelName]
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

const loadTagSettings = async () => {
  try {
    const res = await settingsAPI.tags.get()
    if (res.is_success) {
      tagForm.value = {
        max_tags: res.data.max_tags || 3,
        max_length: res.data.max_length || 50,
        prefix: res.data.prefix || 'auto_tag:',
        ocr_text_limit: res.data.ocr_text_limit || 5000,
        prompt: res.data.prompt || ''
      }
    }
  } catch (e) {
    console.error('Failed to load tag settings', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToLoadTagSettings'), 'error')
    }
  }
}

const saveTagSettings = async () => {
  // Validation
  if (tagForm.value.max_tags < 1 || tagForm.value.max_tags > 20) {
    if (window.$toast) {
      window.$toast.show(t('admin.settings.maxTagsMustBeBetween'), 'error')
    }
    return
  }
  
  if (tagForm.value.max_length < 5 || tagForm.value.max_length > 200) {
    if (window.$toast) {
      window.$toast.show(t('admin.settings.maxTagLengthMustBeBetween'), 'error')
    }
    return
  }
  
  if (tagForm.value.prefix && tagForm.value.prefix.length > 50) {
    if (window.$toast) {
      window.$toast.show(t('admin.settings.tagPrefixMustBeMaximum'), 'error')
    }
    return
  }
  
  if (tagForm.value.ocr_text_limit < 100 || tagForm.value.ocr_text_limit > 50000) {
    if (window.$toast) {
      window.$toast.show(t('admin.settings.ocrTextLimitMustBeBetween'), 'error')
    }
    return
  }
  
  if (tagForm.value.prompt && tagForm.value.prompt.length > 5000) {
    if (window.$toast) {
      window.$toast.show(t('admin.settings.promptMustBeMaximum'), 'error')
    }
    return
  }
  
  savingTags.value = true
  try {
    const res = await settingsAPI.tags.update(tagForm.value)
    if (res.is_success) {
      if (window.$toast) {
        window.$toast.show(t('admin.settings.tagSettingsSaved'), 'success')
      }
      await loadTagSettings()
    }
  } catch (e) {
    console.error('Failed to save tag settings', e)
    if (window.$toast) {
      window.$toast.show(t('admin.settings.failedToSaveTagSettings'), 'error')
    }
  } finally {
    savingTags.value = false
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
  border-radius: var(--radius-md);
  font-size: 1rem;
  background: var(--bg-white);
  transition: all var(--transition-base);
  cursor: pointer;
}

.form-group select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23333' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  padding-right: 2.5rem;
}

.form-group select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-light);
}

.form-group select option {
  padding: 0.5rem;
}

/* Checkbox styles moved to theme.css */

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

/* Ollama Models Section */
.ollama-models-section {
  margin-top: 3rem;
  padding: 0;
  background: var(--bg-light);
  border-radius: 8px;
  border: 1px solid #eee;
}

.ollama-models-section > .section-header {
  padding: 1.5rem 1.5rem 1rem 1.5rem;
  margin: 0;
}

.ollama-models-section > div:not(.section-header) {
  padding: 0 1.5rem 1.5rem 1.5rem;
}

.ollama-models-section .models-subsection {
  padding: 0 1.5rem;
  margin-left: -1.5rem;
  margin-right: -1.5rem;
}

.ollama-models-section .subsection-header {
  padding-left: 1.5rem;
  padding-right: 1.5rem;
}

.ollama-models-section .models-list {
  padding-left: 1.5rem;
  padding-right: 1.5rem;
}

.models-search-container {
  margin-bottom: 2rem;
}

.search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  background: white;
  border: 1px solid #ddd;
  border-radius: var(--radius-md);
  padding: 0.75rem 1rem;
  transition: all var(--transition-base);
}

.search-input-wrapper:focus-within {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-light);
}

.search-icon {
  color: #999;
  margin-right: 0.75rem;
  flex-shrink: 0;
}

.models-search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 1rem;
  color: var(--text-dark);
  background: transparent;
}

.models-search-input::placeholder {
  color: #999;
}

.search-clear-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #999;
  padding: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all var(--transition-base);
  margin-left: 0.5rem;
  flex-shrink: 0;
}

.search-clear-btn:hover {
  background-color: var(--bg-light);
  color: var(--primary);
}

.search-results-info {
  margin-top: 0.75rem;
  font-size: 0.875rem;
  color: var(--text-medium);
  font-style: italic;
}

.models-subsection {
  margin-bottom: 2rem;
  padding: 0;
}

.subsection-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  padding: 0.75rem 0;
  margin: 0 0 1rem 0;
  border-radius: var(--radius-md);
  transition: background-color var(--transition-base);
  user-select: none;
}

.subsection-header:hover {
  background-color: rgba(108, 92, 231, 0.05);
}

.subsection-header h3 {
  margin: 0;
  color: var(--primary);
  font-size: 1.25rem;
  font-weight: 600;
}

.expand-toggle {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--primary);
  padding: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all var(--transition-base);
}

.expand-toggle:hover {
  background-color: rgba(108, 92, 231, 0.1);
  transform: scale(1.1);
}

.models-subsection h3 {
  margin: 0 0 1rem 0;
  color: var(--primary);
  font-size: 1.2rem;
}

.models-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0;
  margin: 0;
}

.model-item {
  background: white;
  padding: 1rem;
  border-radius: 6px;
  border: 1px solid #ddd;
  transition: all 0.2s;
}

.model-item.model-current {
  border-left: 4px solid var(--primary);
  background: #f8f9ff;
}

.model-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.model-info h4 {
  margin: 0 0 0.5rem 0;
  color: #333;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.current-badge {
  background: var(--primary);
  color: white;
  padding: 0.2rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.model-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  font-size: 0.85rem;
  color: #666;
  align-items: center;
}

.model-description {
  font-style: italic;
  color: #888;
}

.model-tags {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.model-tags .tag {
  background: #e5e7eb;
  color: #374151;
  padding: 0.2rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
}

.model-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.status-text {
  font-size: 0.85rem;
  color: #666;
  font-weight: 500;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  position: relative;
}

.test-dropdown {
  position: relative;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 0.25rem;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 10;
  min-width: 150px;
}

.dropdown-item {
  display: block;
  width: 100%;
  padding: 0.5rem 1rem;
  text-align: left;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.dropdown-item:hover {
  background: #f5f5f5;
}

.custom-test-input {
  margin-top: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 4px;
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.custom-test-input input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.test-result {
  margin-top: 1rem;
  border-top: 1px solid #eee;
  padding-top: 1rem;
}

.test-result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 4px;
  font-weight: 500;
}

.test-result-header:hover {
  background: #e9ecef;
}

.test-result-content {
  margin-top: 0.5rem;
  padding: 1rem;
  background: white;
  border-radius: 4px;
  border: 1px solid #eee;
}

.test-response {
  margin-bottom: 1rem;
}

.test-response pre {
  background: #f8f9fa;
  padding: 0.75rem;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.85rem;
  margin-top: 0.5rem;
}

.test-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  color: #666;
  margin-top: 0.5rem;
}

.test-error {
  color: #dc3545;
  padding: 0.5rem;
  background: #fff5f5;
  border-radius: 4px;
}

.warning-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 6px;
  color: #856404;
  margin-bottom: 1rem;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.prompts-section,
.tag-settings-section {
  background: var(--bg-light);
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid #eee;
  margin-bottom: 2rem;
}

.prompt-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #ddd;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.5;
  resize: vertical;
  min-height: 100px;
}

.prompt-textarea:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.form-group small {
  display: block;
  margin-top: 0.5rem;
  color: #666;
  font-size: 0.85rem;
  line-height: 1.4;
}
</style>
