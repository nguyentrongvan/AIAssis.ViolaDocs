<template>
  <Layout>
    <template #header>
      <h1>Settings</h1>
    </template>
    <div class="admin-page">
      <div class="settings-sections">
        <div class="section">
          <h3>Retention Policy</h3>
          <div class="setting-item">
            <label>Default Retention Period (days)</label>
            <input v-model.number="settings.retention_days" type="number" />
          </div>
          <div class="setting-item">
            <label>Purge Grace Period (days)</label>
            <input v-model.number="settings.purge_grace_days" type="number" />
          </div>
        </div>
        <div class="section">
          <h3>OCR Settings</h3>
          <div class="setting-item">
            <label>Default OCR Provider</label>
            <select v-model="settings.ocr_provider">
              <option value="paddle">PaddleOCR</option>
            </select>
          </div>
          <div class="setting-item">
            <label>Supported Languages</label>
            <div>
              <label><input type="checkbox" v-model="settings.languages" value="en" /> English</label>
              <label><input type="checkbox" v-model="settings.languages" value="vi" /> Vietnamese</label>
            </div>
          </div>
        </div>
        <div class="section">
          <h3>Chatbot Settings</h3>
          <div class="setting-item">
            <label>Default LLM Provider</label>
            <select v-model="settings.llm_provider">
              <option value="gemini">Gemini</option>
            </select>
          </div>
        </div>
        <div class="section-actions">
          <button @click="saveSettings" class="btn-primary">Save Settings</button>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Layout from '../../components/Layout.vue'
import api from '../../services/api'

const settings = ref({
  retention_days: 30,
  purge_grace_days: 30,
  ocr_provider: 'paddle',
  languages: ['en', 'vi'],
  llm_provider: 'gemini'
})

onMounted(async () => {
  await loadSettings()
})

const loadSettings = async () => {
  try {
    const res = await api.get('/settings')
    if (res.is_success && res.data) {
      settings.value = { ...settings.value, ...res.data }
    }
  } catch (e) {
    console.error('Failed to load settings', e)
  }
}

const saveSettings = async () => {
  try {
    const res = await api.post('/settings', settings.value)
    if (res.is_success) {
      alert('Settings saved')
    }
  } catch (e) {
    console.error('Failed to save settings', e)
  }
}
</script>

<style scoped>
.admin-page {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.settings-sections {
  max-width: 800px;
}
.section {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid #eee;
}
.section h3 {
  margin: 0 0 1.5rem 0;
  color: var(--primary);
}
.setting-item {
  margin-bottom: 1.5rem;
}
.setting-item label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}
.setting-item input,
.setting-item select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}
.setting-item label input[type="checkbox"] {
  width: auto;
  margin-right: 0.5rem;
}
.section-actions {
  margin-top: 2rem;
}
</style>

