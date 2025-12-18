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
              <select
                id="ollama_llm_model"
                v-model="llmForm.ollama_llm_model"
              >
                <option value="">-- Select LLM Model --</option>
                <option
                  v-for="model in availableLLMModels"
                  :key="model.name"
                  :value="model.name"
                >
                  {{ model.name }}{{ model.is_current_llm ? ' (Current)' : '' }}
                </option>
              </select>
              <small>Select an available model for chat. Only downloaded models are shown.</small>
            </div>
            
            <div class="form-group">
              <label for="ollama_embedding_model">Embedding Model *</label>
              <select
                id="ollama_embedding_model"
                v-model="llmForm.ollama_embedding_model"
              >
                <option value="">-- Select Embedding Model --</option>
                <option
                  v-for="model in availableEmbeddingModels"
                  :key="model.name"
                  :value="model.name"
                >
                  {{ model.name }}{{ model.is_current_embedding ? ' (Current)' : '' }}
                </option>
              </select>
              <small>Select an available model for embeddings. Only downloaded models are shown.</small>
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

        <!-- Ollama Models Management Section -->
        <div class="ollama-models-section">
          <div class="section-header">
            <h2>Ollama Models</h2>
            <button @click="loadOllamaModels" class="btn-secondary" :disabled="loadingModels">
              <RefreshCw :size="20" :class="{ 'spinning': loadingModels }" />
              Refresh
            </button>
          </div>

          <div v-if="!ollamaConnected" class="warning-box">
            <AlertTriangle :size="20" />
            <span>Cannot connect to Ollama. Please check your Ollama Base URL configuration.</span>
          </div>

          <div v-else-if="loadingModels" class="loading">Loading models...</div>
          
          <div v-else>
            <!-- Search Box -->
            <div class="models-search-container">
              <div class="search-input-wrapper">
                <Search :size="18" class="search-icon" />
                <input
                  v-model="modelSearchQuery"
                  type="text"
                  placeholder="Search models by name, description, or tags..."
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
                Found {{ llmModels.length + embeddingModels.length }} model(s)
              </div>
            </div>
            
            <!-- LLM Models Section -->
            <div class="models-subsection">
              <div class="subsection-header" @click="toggleSection('llm')">
                <h3>LLM Models</h3>
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
                        <span v-if="model.is_current_llm" class="current-badge">Current</span>
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
                      <span v-if="model.downloaded" class="status-text">Downloaded</span>
                      <span v-else-if="model.available" class="status-text">Available</span>
                      <span v-else class="status-text">Unknown</span>
                      <div class="action-buttons">
                        <button
                          v-if="!model.downloaded && model.available"
                          @click="pullModel(model.name)"
                          class="btn-small btn-primary"
                          :disabled="pullingModel === model.name"
                        >
                          <Download :size="14" />
                          {{ pullingModel === model.name ? 'Downloading...' : 'Download' }}
                        </button>
                        <div v-if="model.downloaded" class="test-dropdown">
                          <button
                            @click.stop="showTestDropdown(model.name)"
                            class="btn-small btn-secondary"
                            :disabled="testingModel === model.name"
                          >
                            <TestTube :size="14" />
                            Test
                          </button>
                          <div v-if="testDropdownOpen === model.name" class="dropdown-menu" @click.stop>
                            <button @click="testModel(model.name, 'llm', true)" class="dropdown-item">
                              Quick Test
                            </button>
                            <button @click="showCustomTest(model.name, 'llm')" class="dropdown-item">
                              Custom Test
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
                      placeholder="Enter test prompt..."
                      @keyup.enter="testModel(model.name, 'llm', false)"
                    />
                    <button @click="testModel(model.name, 'llm', false)" class="btn-small btn-primary">
                      Run Test
                    </button>
                    <button @click="cancelCustomTest" class="btn-small btn-secondary">
                      Cancel
                    </button>
                  </div>

                  <!-- Test Result -->
                  <div v-if="testResults[model.name]" class="test-result">
                    <div class="test-result-header" @click="toggleTestResult(model.name)">
                      <span>Test Result</span>
                      <span>{{ testResults[model.name].success ? '✓' : '✗' }}</span>
                    </div>
                    <div v-if="expandedTestResults[model.name]" class="test-result-content">
                      <div v-if="testResults[model.name].success">
                        <div v-if="testResults[model.name].result.response" class="test-response">
                          <strong>Response:</strong>
                          <pre>{{ testResults[model.name].result.response }}</pre>
                        </div>
                        <div v-if="testResults[model.name].result.token_usage" class="test-meta">
                          <span>Duration: {{ testResults[model.name].duration_ms }}ms</span>
                          <span>Tokens: {{ testResults[model.name].result.token_usage.total_tokens }}</span>
                        </div>
                      </div>
                      <div v-else class="test-error">
                        {{ testResults[model.name].error || 'Test failed' }}
                      </div>
                    </div>
                  </div>
                </div>
                <div v-if="llmModels.length === 0" class="empty-state">
                  No LLM models found
                </div>
              </div>
            </div>

            <!-- Embedding Models Section -->
            <div class="models-subsection">
              <div class="subsection-header" @click="toggleSection('embedding')">
                <h3>Embedding Models</h3>
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
                        <span v-if="model.is_current_embedding" class="current-badge">Current</span>
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
                      <span v-if="model.downloaded" class="status-text">Downloaded</span>
                      <span v-else-if="model.available" class="status-text">Available</span>
                      <span v-else class="status-text">Unknown</span>
                      <div class="action-buttons">
                        <button
                          v-if="!model.downloaded && model.available"
                          @click="pullModel(model.name)"
                          class="btn-small btn-primary"
                          :disabled="pullingModel === model.name"
                        >
                          <Download :size="14" />
                          {{ pullingModel === model.name ? 'Downloading...' : 'Download' }}
                        </button>
                        <div v-if="model.downloaded" class="test-dropdown">
                          <button
                            @click.stop="showTestDropdown(model.name)"
                            class="btn-small btn-secondary"
                            :disabled="testingModel === model.name"
                          >
                            <TestTube :size="14" />
                            Test
                          </button>
                          <div v-if="testDropdownOpen === model.name" class="dropdown-menu" @click.stop>
                            <button @click="testModel(model.name, 'embedding', true)" class="dropdown-item">
                              Quick Test
                            </button>
                            <button @click="showCustomTest(model.name, 'embedding')" class="dropdown-item">
                              Custom Test
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
                      placeholder="Enter test text..."
                      @keyup.enter="testModel(model.name, 'embedding', false)"
                    />
                    <button @click="testModel(model.name, 'embedding', false)" class="btn-small btn-primary">
                      Run Test
                    </button>
                    <button @click="cancelCustomTest" class="btn-small btn-secondary">
                      Cancel
                    </button>
                  </div>

                  <!-- Test Result -->
                  <div v-if="testResults[model.name]" class="test-result">
                    <div class="test-result-header" @click="toggleTestResult(model.name)">
                      <span>Test Result</span>
                      <span>{{ testResults[model.name].success ? '✓' : '✗' }}</span>
                    </div>
                    <div v-if="expandedTestResults[model.name]" class="test-result-content">
                      <div v-if="testResults[model.name].success">
                        <div v-if="testResults[model.name].result.embedding_dimension" class="test-response">
                          <strong>Dimension:</strong> {{ testResults[model.name].result.embedding_dimension }}
                        </div>
                        <div v-if="testResults[model.name].result.embedding_sample" class="test-response">
                          <strong>Sample (first 10 values):</strong>
                          <pre>{{ JSON.stringify(testResults[model.name].result.embedding_sample, null, 2) }}</pre>
                        </div>
                        <div class="test-meta">
                          <span>Duration: {{ testResults[model.name].duration_ms }}ms</span>
                        </div>
                      </div>
                      <div v-else class="test-error">
                        {{ testResults[model.name].error || 'Test failed' }}
                      </div>
                    </div>
                  </div>
                </div>
                <div v-if="embeddingModels.length === 0" class="empty-state">
                  No Embedding models found
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Chatbot Policies Tab -->
      <div v-if="activeTab === 'chatbot'" class="tab-content">
        <!-- Chatbot Prompts Section -->
        <div class="section-header">
          <h2>Chatbot Prompts</h2>
        </div>
        <div class="prompts-section">
          <div class="form-section">
            <div class="form-group">
              <label for="system_prompt">System Prompt</label>
              <textarea
                id="system_prompt"
                v-model="promptsForm.system_prompt"
                rows="4"
                placeholder="System prompt for chatbot assistant..."
                class="prompt-textarea"
              ></textarea>
              <small>This prompt defines the chatbot's role and behavior. Use {context} and {question} placeholders in context prompts.</small>
            </div>
            <div class="form-group">
              <label for="context_prompt">Context Prompt (with documents)</label>
              <textarea
                id="context_prompt"
                v-model="promptsForm.context_prompt"
                rows="6"
                placeholder="Prompt template when documents are provided..."
                class="prompt-textarea"
              ></textarea>
              <small>Template used when answering questions with document context. Use {context} for document content and {question} for user question.</small>
            </div>
            <div class="form-group">
              <label for="no_context_prompt">No Context Prompt (without documents)</label>
              <textarea
                id="no_context_prompt"
                v-model="promptsForm.no_context_prompt"
                rows="4"
                placeholder="Prompt template when no documents are provided..."
                class="prompt-textarea"
              ></textarea>
              <small>Template used when answering questions without document context. Use {question} placeholder.</small>
            </div>
            <div class="form-actions">
              <button @click="savePrompts" class="btn-primary" :disabled="savingPrompts">
                <Save :size="16" />
                {{ savingPrompts ? 'Saving...' : 'Save Prompts' }}
              </button>
              <button @click="resetPromptsToDefaults" class="btn-secondary" :disabled="savingPrompts">
                <RefreshCw :size="16" />
                Reset to Defaults
              </button>
            </div>
          </div>
        </div>

        <div class="section-header" style="margin-top: 3rem;">
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
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useSettingsStore } from '../../store/settings'
import { useGroupsStore } from '../../store/groups'
import { settingsAPI } from '../../services/api'
import { Modal, StatusBadge } from '../../components'
import { Plus, Edit, Trash2, Activity, Save, RefreshCw, AlertTriangle, Download, TestTube, ChevronDown, ChevronUp, Search, X } from 'lucide-vue-next'

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
  document.addEventListener('click', handleClickOutside)
  await loadRetentionPolicies()
  await loadProviders()
  await loadChatbotPolicies()
  await loadGroups()
  await loadLLMSettings()
  await loadOCRSettings()
  await loadPurgeGracePeriod()
  await loadPrompts()
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
      window.$toast.show('Failed to load prompts', 'error')
    }
  }
}

const resetPromptsToDefaults = async () => {
  if (!confirm('Reset prompts to defaults? This will reload the default prompts from the system.')) {
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
      window.$toast.show('Prompts reset to defaults', 'success')
    }
  } catch (e) {
    console.error('Failed to reset prompts', e)
    if (window.$toast) {
      window.$toast.show('Failed to reset prompts', 'error')
    }
  }
}

const savePrompts = async () => {
  savingPrompts.value = true
  try {
    const res = await settingsAPI.chatbot.updatePrompts(promptsForm.value)
    if (res.is_success) {
      if (window.$toast) {
        window.$toast.show('Prompts saved successfully', 'success')
      }
    }
  } catch (e) {
    console.error('Failed to save prompts', e)
    if (window.$toast) {
      window.$toast.show('Failed to save prompts', 'error')
    }
  } finally {
    savingPrompts.value = false
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
      // Load models list for dropdowns
      await loadOllamaModels()
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
        window.$toast.show('Failed to load Ollama models', 'error')
      }
    }
  } catch (e) {
    console.error('Failed to load Ollama models', e)
    ollamaConnected.value = false
    if (window.$toast) {
      window.$toast.show('Failed to load Ollama models', 'error')
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
        window.$toast.show(`Started pulling ${modelName}. This may take several minutes.`, 'success')
      }
      // Refresh models list after a delay
      setTimeout(async () => {
        await loadOllamaModels()
      }, 2000)
    } else {
      if (window.$toast) {
        window.$toast.show(res.message || `Failed to pull ${modelName}`, 'error')
      }
    }
  } catch (e) {
    console.error(`Failed to pull model ${modelName}`, e)
    const errorMsg = e.response?.data?.message || e.message || `Failed to pull ${modelName}`
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
        error: res.message || 'Test failed'
      }
      expandedTestResults.value[modelName] = true
    }
  } catch (e) {
    console.error(`Failed to test model ${modelName}`, e)
    const errorMsg = e.response?.data?.message || e.message || `Failed to test ${modelName}`
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

/* Ollama Models Section */
.ollama-models-section {
  margin-top: 3rem;
  padding: 1.5rem;
  background: var(--bg-light);
  border-radius: 8px;
  border: 1px solid #eee;
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
}

.subsection-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  padding: 0.75rem;
  margin: -0.75rem -0.75rem 1rem -0.75rem;
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

.prompts-section {
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
